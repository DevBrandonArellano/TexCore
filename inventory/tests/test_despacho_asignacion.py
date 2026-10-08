"""Caracterización de los pasos de ProcessDespachoAPIView._procesar extraídos por C901:
asignación de cada lote a un pedido y filas que salen del lote escaneado."""
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


class LoteYFilasTests(TestCase):
    """Filas que salen al escanear un lote: la de su producto y las de productos pedidos."""

    def setUp(self):
        self.orden = OrdenProduccionFactory()
        self.lote = LoteProduccionFactory(orden_produccion=self.orden)
        self.principal = StockBodegaFactory(lote=self.lote, producto=self.orden.producto_salida)

    def test_lote_dado_codigo_inexistente_cuando_valida_entonces_lote_no_valido(self):
        with self.assertRaisesMessage(serializers.ValidationError, 'Lote NO-EXISTE no válido.'):
            Vista._lote_y_filas('NO-EXISTE', {}, set())

    def test_lote_dado_lote_sin_fila_de_stock_cuando_valida_entonces_sin_stock_disponible(self):
        with self.assertRaisesMessage(serializers.ValidationError, 'ya no tiene stock disponible'):
            Vista._lote_y_filas(self.lote.codigo_lote, {}, set())

    def test_lote_dado_lote_con_stock_cuando_valida_entonces_retira_sus_filas_y_devuelve_la_principal(self):
        mapa = {self.lote.id: [self.principal]}
        lote, filas = Vista._lote_y_filas(self.lote.codigo_lote, mapa, set())
        self.assertEqual((lote, filas), (self.lote, [self.principal]))
        self.assertEqual(mapa, {})

    def test_lote_dado_productos_extra_cuando_valida_entonces_principal_primero_y_solo_los_pedidos(self):
        pedido = StockBodegaFactory(lote=self.lote)
        no_pedido = StockBodegaFactory(lote=self.lote)
        mapa = {self.lote.id: [pedido, no_pedido, self.principal]}
        _, filas = Vista._lote_y_filas(self.lote.codigo_lote, mapa, {pedido.producto_id})
        self.assertEqual(filas, [self.principal, pedido])

    def test_lote_dado_lote_sin_orden_y_producto_no_pedido_cuando_valida_entonces_sin_stock_de_lo_pedido(self):
        lote = LoteProduccionFactory(orden_produccion=None)
        stock = StockBodegaFactory(lote=lote)
        with self.assertRaisesMessage(serializers.ValidationError, 'no tiene stock de los productos de los pedidos'):
            Vista._lote_y_filas(lote.codigo_lote, {lote.id: [stock]}, set())

    def test_lote_dado_lote_sin_orden_con_producto_pedido_cuando_valida_entonces_lo_despacha(self):
        lote = LoteProduccionFactory(orden_produccion=None)
        stock = StockBodegaFactory(lote=lote)
        _, filas = Vista._lote_y_filas(lote.codigo_lote, {lote.id: [stock]}, {stock.producto_id})
        self.assertEqual(filas, [stock])
