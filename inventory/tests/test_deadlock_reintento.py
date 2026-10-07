"""
Reintento ante deadlock de SQL Server (error 1205 / SQLSTATE 40001) en despacho y
reversión. SQL Server aborta una de las transacciones y pide reejecutarla; sin
reintento, el usuario recibía un 500 bajo concurrencia (prueba de carga 29-sep).
Técnicas ISTQB: partición de equivalencia (deadlock / otro error de BD / éxito).
"""
from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase
from rest_framework.response import Response
from rest_framework.test import APIClient

from gestion.models import PedidoVenta
from gestion.tests.factories import BodegaFactory, ClienteFactory, CustomUserFactory, SedeFactory
from inventory.models import DetalleHistorialDespachoPedido, HistorialDespacho
from inventory.utils import INTENTOS_DEADLOCK, es_deadlock

DEADLOCK = OperationalError('Transaction was deadlocked ... chosen as the deadlock victim. (1205)')


class EsDeadlockTestCase(TestCase):

    def test_es_deadlock_dado_error_1205_cuando_evalua_entonces_true(self):
        self.assertTrue(es_deadlock(DEADLOCK))

    def test_es_deadlock_dado_otro_error_de_bd_cuando_evalua_entonces_false(self):
        self.assertFalse(es_deadlock(OperationalError('Login timeout expired')))


class ReintentoDeadlockTestCase(TestCase):

    def setUp(self):
        sede = SedeFactory()
        self.usuario = CustomUserFactory(sede=sede, groups=['despacho'])
        self.usuario.bodegas_asignadas.add(BodegaFactory(sede=sede))
        self.pedido = PedidoVenta.objects.create(cliente=ClienteFactory(sede=sede), guia_remision='GR-DL', sede=sede)
        self.client = APIClient()
        self.client.force_authenticate(user=self.usuario)

    def _despachar(self):
        return self.client.post('/api/inventory/process-despacho/',
                                {'pedidos': [self.pedido.id], 'lotes': ['L-1']}, format='json')

    @patch('inventory.views.despacho_views.ProcessDespachoAPIView._calcular_incompletos', return_value={})
    @patch('inventory.views.despacho_views.ProcessDespachoAPIView._procesar')
    def test_despacho_dado_deadlock_transitorio_cuando_post_entonces_reintenta_y_responde_200(self, procesar, _):
        procesar.side_effect = [DEADLOCK, Response({'ok': True})]
        resp = self._despachar()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(procesar.call_count, 2)

    @patch('inventory.views.despacho_views.ProcessDespachoAPIView._calcular_incompletos', return_value={})
    @patch('inventory.views.despacho_views.ProcessDespachoAPIView._procesar')
    def test_despacho_dado_deadlock_persistente_cuando_post_entonces_500_tras_agotar_intentos(self, procesar, _):
        procesar.side_effect = DEADLOCK
        resp = self._despachar()
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(procesar.call_count, INTENTOS_DEADLOCK)

    @patch('inventory.views.despacho_views.ProcessDespachoAPIView._calcular_incompletos', return_value={})
    @patch('inventory.views.despacho_views.ProcessDespachoAPIView._procesar')
    def test_despacho_dado_otro_error_de_bd_cuando_post_entonces_500_sin_reintentar(self, procesar, _):
        procesar.side_effect = OperationalError('Login timeout expired')
        resp = self._despachar()
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(procesar.call_count, 1)

    @patch('inventory.services.despacho_reversion.DespachoReversionService.revertir_despacho')
    def test_reversion_dado_deadlock_transitorio_cuando_revierte_entonces_reintenta_y_borra_historial(self, revertir):
        revertir.side_effect = [DEADLOCK, {'lotes_revertidos': []}]
        historial = HistorialDespacho.objects.create(usuario=self.usuario, total_bultos=0, total_peso=0)
        # El historial se acota a la sede de sus pedidos (OWASP A01).
        DetalleHistorialDespachoPedido.objects.create(historial=historial, pedido=self.pedido, cantidad_despachada=0)
        resp = self.client.post(f'/api/inventory/historial-despachos/{historial.id}/revertir/',
                                {'justificacion': 'Prueba de reintento'}, format='json')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(revertir.call_count, 2)
        self.assertFalse(HistorialDespacho.objects.filter(pk=historial.pk).exists())
