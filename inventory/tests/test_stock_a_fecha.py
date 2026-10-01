"""
Stock a fecha de corte (`GET /api/inventory/retro-kardex/`).

El saldo de cada bodega a una fecha pasada se calcula en SQL (entradas menos
salidas por bodega) y solo para bodegas que el usuario ve: la contraparte de
una transferencia hacia una bodega ajena no aparece. Una fecha sin hora corta
al final de ese día local; una fecha con hora, en ese instante.

Técnicas ISTQB: partición de equivalencia por bodega (visible / no visible),
valores límite de la fecha de corte (mismo día, instante exacto) y prueba de
rendimiento (número de consultas constante).
"""
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from gestion.tests.factories import BodegaFactory, CustomUserFactory, ProductoFactory, SedeFactory
from inventory.models import MovimientoInventario

URL = '/api/inventory/retro-kardex/'


def _mov(fecha, **campos):
    mov = MovimientoInventario.objects.create(**campos)
    MovimientoInventario.objects.filter(pk=mov.pk).update(fecha=fecha)
    return mov


def _local(y, m, d, h=12, mi=0):
    return timezone.make_aware(datetime(y, m, d, h, mi))


class StockAFechaTestCase(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.producto = ProductoFactory(sede=self.sede)
        self.bodega_a = BodegaFactory(sede=self.sede, nombre='Principal')
        self.bodega_b = BodegaFactory(sede=self.sede)
        _mov(_local(2026, 9, 1), tipo_movimiento='AJUSTE', producto=self.producto,
             bodega_destino=self.bodega_a, cantidad=Decimal('100.000'))
        _mov(_local(2026, 9, 10), tipo_movimiento='TRANSFERENCIA', producto=self.producto,
             bodega_origen=self.bodega_a, bodega_destino=self.bodega_b, cantidad=Decimal('30.000'))
        _mov(_local(2026, 9, 20, 10), tipo_movimiento='VENTA', producto=self.producto,
             bodega_origen=self.bodega_a, cantidad=Decimal('20.000'))

    def _consultar(self, user, **params):
        self.client.force_authenticate(user=user)
        return self.client.get(URL, {'producto_id': self.producto.id, **params})

    def _por_bodega(self, resp):
        return {fila['bodega_id']: Decimal(str(fila['stock_calculado'])) for fila in resp.data}

    def test_stock_a_fecha_dado_bodeguero_con_una_bodega_cuando_hay_transferencia_entonces_no_ve_la_otra(self):
        bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        bodeguero.bodegas_asignadas.add(self.bodega_a)
        resp = self._consultar(bodeguero, fecha_corte='2026-09-15')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self._por_bodega(resp), {self.bodega_a.id: Decimal('70.000')})

    def test_stock_a_fecha_dado_admin_cuando_consulta_entonces_ve_ambas_bodegas(self):
        resp = self._consultar(CustomUserFactory(groups=['admin_sistemas']), fecha_corte='2026-09-15')
        self.assertEqual(self._por_bodega(resp),
                         {self.bodega_a.id: Decimal('70.000'), self.bodega_b.id: Decimal('30.000')})

    def test_stock_a_fecha_dado_fecha_sin_hora_cuando_hay_movimiento_ese_dia_entonces_lo_incluye(self):
        resp = self._consultar(CustomUserFactory(groups=['admin_sistemas']),
                               fecha_corte='2026-09-20', bodega_id=self.bodega_a.id)
        self.assertEqual(self._por_bodega(resp), {self.bodega_a.id: Decimal('50.000')})

    def test_stock_a_fecha_dado_fecha_con_hora_anterior_al_movimiento_cuando_consulta_entonces_lo_excluye(self):
        corte = _local(2026, 9, 20, 9, 59).isoformat()
        resp = self._consultar(CustomUserFactory(groups=['admin_sistemas']),
                               fecha_corte=corte, bodega_id=self.bodega_a.id)
        self.assertEqual(self._por_bodega(resp), {self.bodega_a.id: Decimal('70.000')})

    def test_stock_a_fecha_dado_bodegas_con_el_mismo_nombre_en_dos_sedes_cuando_consulta_entonces_dos_filas(self):
        homonima = BodegaFactory(sede=SedeFactory(), nombre='Principal')
        _mov(_local(2026, 9, 2), tipo_movimiento='AJUSTE', producto=self.producto,
             bodega_destino=homonima, cantidad=Decimal('5.000'))
        resp = self._consultar(CustomUserFactory(groups=['admin_sistemas']), fecha_corte='2026-09-15')
        filas = {fila['bodega_id']: fila for fila in resp.data}
        self.assertEqual(Decimal(str(filas[homonima.id]['stock_calculado'])), Decimal('5.000'))
        self.assertEqual(Decimal(str(filas[self.bodega_a.id]['stock_calculado'])), Decimal('70.000'))
        self.assertNotEqual(filas[homonima.id]['sede'], filas[self.bodega_a.id]['sede'])

    def test_stock_a_fecha_dado_fecha_invalida_cuando_consulta_entonces_400(self):
        resp = self._consultar(CustomUserFactory(groups=['admin_sistemas']), fecha_corte='2026-13-40')
        self.assertEqual(resp.status_code, 400)

    def test_stock_a_fecha_dado_producto_de_otra_sede_cuando_bodeguero_consulta_entonces_404(self):
        ajeno = ProductoFactory(sede=SedeFactory())
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede, groups=['bodeguero']))
        resp = self.client.get(URL, {'producto_id': ajeno.id, 'fecha_corte': '2026-09-15'})
        self.assertEqual(resp.status_code, 404)

    def test_stock_a_fecha_dado_muchos_movimientos_cuando_consulta_entonces_consultas_constantes(self):
        admin = CustomUserFactory(groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        params = {'producto_id': self.producto.id, 'fecha_corte': '2026-09-30'}
        with CaptureQueriesContext(connection) as pocos:
            self.client.get(URL, params)
        for i in range(40):
            _mov(_local(2026, 9, 21) + timedelta(minutes=i), tipo_movimiento='AJUSTE',
                 producto=self.producto, bodega_destino=self.bodega_b, cantidad=Decimal('1.000'))
        with CaptureQueriesContext(connection) as muchos:
            resp = self.client.get(URL, params)
        self.assertEqual(len(muchos), len(pocos))
        self.assertEqual(self._por_bodega(resp)[self.bodega_b.id], Decimal('70.000'))
