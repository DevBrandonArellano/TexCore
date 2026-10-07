"""
Multi-tenancy (OWASP A01) del historial de despachos.

Defecto encontrado en la prueba de carga con 4 empresas (2026-10-06): el despachador de
la empresa 1 revirtió un despacho de la empresa 3. HistorialDespachoViewSet no acotaba
por sede: cualquier rol con lectura de despachos listaba, consultaba, imprimía la guía y
revertía (o borraba) los despachos de todas las sedes. La sede de un despacho es la de
sus pedidos (ProcessDespachoAPIView solo acepta pedidos de la sede del usuario).

Técnica ISTQB: partición de equivalencia (propia sede / otra sede / rol que ve todas).
"""
from decimal import Decimal

from django.contrib.auth.models import Group
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import Cliente, CustomUser, PedidoVenta, Sede
from inventory.models import DetalleHistorialDespachoPedido, HistorialDespacho

URL = '/api/inventory/historial-despachos/'


def _despacho(sede, n):
    cliente = Cliente.objects.create(ruc_cedula=f'179000000{n}001', nombre_razon_social=f'Cliente {n}',
                                     direccion_envio='Quito', nivel_precio='normal', sede=sede)
    pedido = PedidoVenta.objects.create(cliente=cliente, guia_remision=f'GR-{n}', estado='despachado', sede=sede)
    historial = HistorialDespacho.objects.create(total_bultos=1, total_peso=Decimal('10.000'))
    DetalleHistorialDespachoPedido.objects.create(historial=historial, pedido=pedido,
                                                  cantidad_despachada=Decimal('10.000'))
    return historial


def _usuario(username, grupo, sede=None):
    usuario = CustomUser.objects.create_user(username=username, password='x', sede=sede)
    usuario.groups.add(Group.objects.get_or_create(name=grupo)[0])
    return usuario


class HistorialDespachoPorSedeTestCase(TestCase):
    def setUp(self):
        self.sede_a = Sede.objects.create(nombre='Empresa A', location='Quito')
        self.sede_b = Sede.objects.create(nombre='Empresa B', location='Cuenca')
        self.propio = _despacho(self.sede_a, 1)
        self.ajeno = _despacho(self.sede_b, 2)
        self.client = APIClient()
        self.client.force_authenticate(_usuario('despacho_a', 'despacho', self.sede_a))

    def test_historial_dado_despachador_cuando_lista_entonces_solo_ve_los_de_su_sede(self):
        resp = self.client.get(URL)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        filas = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertEqual([f['id'] for f in filas], [self.propio.id])

    def test_historial_dado_despacho_de_otra_sede_cuando_lo_consulta_entonces_404(self):
        self.assertEqual(self.client.get(f'{URL}{self.ajeno.id}/').status_code, status.HTTP_404_NOT_FOUND)

    def test_historial_dado_despacho_de_otra_sede_cuando_lo_revierte_entonces_404_sin_efectos(self):
        resp = self.client.post(f'{URL}{self.ajeno.id}/revertir/',
                                {'justificacion': 'Intento de revertir un despacho ajeno'}, format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(HistorialDespacho.objects.filter(pk=self.ajeno.pk).exists())

    def test_historial_dado_despacho_de_otra_sede_cuando_lo_borra_entonces_404_sin_efectos(self):
        resp = self.client.delete(f'{URL}{self.ajeno.id}/', {'justificacion': 'Intento de borrar un despacho ajeno'},
                                  format='json')

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(HistorialDespacho.objects.filter(pk=self.ajeno.pk).exists())

    def test_historial_dado_ejecutivo_cuando_lista_entonces_ve_todas_las_sedes(self):
        self.client.force_authenticate(_usuario('ejecutivo', 'ejecutivo'))

        resp = self.client.get(URL)

        filas = resp.data['results'] if isinstance(resp.data, dict) else resp.data
        self.assertEqual({f['id'] for f in filas}, {self.propio.id, self.ajeno.id})
