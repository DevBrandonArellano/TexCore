"""Caracterización de los pasos de ProcessDespachoAPIView._procesar extraídos por C901:
asignación de cada lote a un pedido y validación del lote escaneado."""
from decimal import Decimal
from types import SimpleNamespace as NS

from django.test import TestCase
from rest_framework import serializers

from gestion.tests.factories import LoteProduccionFactory, OrdenProduccionFactory, StockBodegaFactory
from inventory.views.despacho_views import ProcessDespachoAPIView as Vista

PRODUCTO = NS(id=50)
PEDIDOS = {1: NS(id=1), 2: NS(id=2)}


def _lote(reserva=None):
    return NS(pedido_venta_reserva_id=reserva, codigo_lote='L-1')


class AsignarPedidoTests(TestCase):
    def test_asignar_dado_lote_reservado_mto_cuando_pedido_seleccionado_entonces_asigna_y_descuenta(self):
        pendiente = {(2, 50): Decimal('30')}
        asignado = Vista._asignar_pedido(_lote(reserva=2), PRODUCTO, Decimal('10'), [1, 2], PEDIDOS, pendiente)
        self.assertIs(asignado, PEDIDOS[2])
        self.assertEqual(pendiente[(2, 50)], Decimal('20'))

    def test_asignar_dado_lote_reservado_mto_cuando_pedido_no_seleccionado_entonces_rechaza(self):
        with self.assertRaises(serializers.ValidationError):
            Vista._asignar_pedido(_lote(reserva=9), PRODUCTO, Decimal('10'), [1, 2], PEDIDOS, {})

    def test_asignar_dado_varios_pedidos_cuando_el_primero_ya_esta_cubierto_entonces_asigna_al_siguiente(self):
        pendiente = {(1, 50): Decimal('0'), (2, 50): Decimal('15')}
        asignado = Vista._asignar_pedido(_lote(), PRODUCTO, Decimal('20'), [1, 2], PEDIDOS, pendiente)
        self.assertIs(asignado, PEDIDOS[2])
        self.assertEqual(pendiente[(2, 50)], Decimal('-5'))

    def test_asignar_dado_excedente_escaneado_cuando_nadie_lo_necesita_entonces_va_al_primero_que_lo_pidio(self):
        pendiente = {(2, 50): Decimal('0')}
        asignado = Vista._asignar_pedido(_lote(), PRODUCTO, Decimal('20'), [1, 2], PEDIDOS, pendiente)
        self.assertIs(asignado, PEDIDOS[2])
        self.assertEqual(pendiente[(2, 50)], Decimal('0'))

    def test_asignar_dado_producto_que_ningun_pedido_pidio_cuando_asigna_entonces_queda_sin_pedido(self):
        self.assertIsNone(Vista._asignar_pedido(_lote(), PRODUCTO, Decimal('20'), [1, 2], PEDIDOS, {}))


class LoteConProductoTests(TestCase):
    def test_lote_dado_codigo_inexistente_cuando_valida_entonces_lote_no_valido(self):
        with self.assertRaisesMessage(serializers.ValidationError, 'Lote NO-EXISTE no válido.'):
            Vista._lote_con_producto('NO-EXISTE', {})

    def test_lote_dado_lote_sin_fila_de_stock_cuando_valida_entonces_sin_stock_disponible(self):
        lote = LoteProduccionFactory()
        with self.assertRaisesMessage(serializers.ValidationError, 'ya no tiene stock disponible'):
            Vista._lote_con_producto(lote.codigo_lote, {})

    def test_lote_dado_lote_sin_orden_cuando_valida_entonces_sin_producto_asociado(self):
        lote = LoteProduccionFactory(orden_produccion=None)
        stock = StockBodegaFactory(lote=lote)
        with self.assertRaisesMessage(serializers.ValidationError, 'no tiene un producto asociado'):
            Vista._lote_con_producto(lote.codigo_lote, {lote.id: stock})

    def test_lote_dado_lote_con_stock_cuando_valida_entonces_retira_su_fila_y_devuelve_producto(self):
        orden = OrdenProduccionFactory()
        lote = LoteProduccionFactory(orden_produccion=orden)
        stock = StockBodegaFactory(lote=lote)
        mapa = {lote.id: stock}
        _, fila, producto = Vista._lote_con_producto(lote.codigo_lote, mapa)
        self.assertEqual(fila, stock)
        self.assertEqual(producto, orden.producto_salida or orden.producto_entrada)
        self.assertEqual(mapa, {})
