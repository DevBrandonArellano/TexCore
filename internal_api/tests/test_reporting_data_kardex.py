"""
reporting_data.get_kardex — datos del export Excel del kárdex (TEX-22 CA-2).

Comparte KardexService con la pantalla: el saldo del Excel es el mismo que el
del kárdex en pantalla (antes exportaba saldo_resultante, una foto del stock por
lote al momento del movimiento, y sin bodega destino no se distinguía una
entrada de una salida).

Técnicas ISTQB:
- Particiones de equivalencia (EP): con producto (hay saldo) / sin producto
  (toda la bodega, sin saldo); entrada / salida.
- Caja blanca (CB-D): el saldo incluye lo anterior a fecha_desde sin agregar filas.
"""
from datetime import date, datetime, time
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from internal_api.services import reporting_data as rd
from inventory.models import MovimientoInventario
from gestion.tests.factories import SedeFactory, BodegaFactory, ProductoFactory


class GetKardexExportTestCase(TestCase):
    def setUp(self):
        sede = SedeFactory()
        self.bodega = BodegaFactory(sede=sede)
        self.otra_bodega = BodegaFactory(sede=sede)
        self.producto = ProductoFactory(sede=sede)
        self.otro_producto = ProductoFactory(sede=sede)
        self._mov(date(2026, 1, 1), '100.000', destino=self.bodega)
        self._mov(date(2026, 2, 1), '30.000', origen=self.bodega, otra=True, tipo='TRANSFERENCIA')
        self._mov(date(2026, 2, 2), '8.000', destino=self.bodega, producto=self.otro_producto)

    def _mov(self, dia, cantidad, destino=None, origen=None, producto=None, tipo='COMPRA', otra=False):
        mov = MovimientoInventario.objects.create(
            tipo_movimiento=tipo, producto=producto or self.producto, cantidad=Decimal(cantidad),
            bodega_destino=self.otra_bodega if otra else destino, bodega_origen=origen,
        )
        MovimientoInventario.objects.filter(pk=mov.pk).update(
            fecha=timezone.make_aware(datetime.combine(dia, time(12, 0))))
        return mov

    def test_get_kardex_dado_producto_y_fecha_desde_cuando_exporta_entonces_saldo_incluye_lo_anterior(self):
        filas = rd.get_kardex(self.bodega.id, producto_id=self.producto.id, fecha_desde='2026-02-01')

        self.assertEqual(len(filas), 1)  # sin fila virtual: el saldo ya trae lo anterior
        self.assertEqual(filas[0]['saldo'], Decimal('70.000'))

    def test_get_kardex_dado_transferencia_saliente_cuando_exporta_entonces_columnas_de_direccion(self):
        filas = rd.get_kardex(self.bodega.id, producto_id=self.producto.id)

        salida = filas[1]
        self.assertEqual(salida['tipo_movimiento'], 'TRANSFERENCIA')
        self.assertEqual(salida['entrada'], Decimal('0'))
        self.assertEqual(salida['salida'], Decimal('30.000'))
        self.assertEqual(salida['bodega_origen_nombre'], self.bodega.nombre)
        self.assertEqual(salida['bodega_destino_nombre'], self.otra_bodega.nombre)
        self.assertEqual(salida['saldo'], Decimal('70.000'))

    def test_get_kardex_dado_sin_producto_cuando_exporta_entonces_toda_la_bodega_sin_columna_saldo(self):
        filas = rd.get_kardex(self.bodega.id)

        self.assertEqual(len(filas), 3)
        self.assertNotIn('saldo', filas[0])
        self.assertIn('producto_descripcion', filas[0])

    def test_get_kardex_dado_fecha_hasta_cuando_exporta_entonces_incluye_todo_ese_dia(self):
        filas = rd.get_kardex(self.bodega.id, fecha_desde='2026-02-02', fecha_hasta='2026-02-02')
        self.assertEqual(len(filas), 1)

    def test_get_kardex_dado_tipo_salida_cuando_exporta_entonces_solo_salidas_con_saldo_real(self):
        # CA-2: el Excel trae las mismas filas que la pantalla filtrada por tipo.
        filas = rd.get_kardex(self.bodega.id, producto_id=self.producto.id, tipo='salida')

        self.assertEqual([f['tipo_movimiento'] for f in filas], ['TRANSFERENCIA'])
        self.assertEqual(filas[0]['saldo'], Decimal('70.000'))
