"""
Alcance de las escrituras de stock de inventario (OWASP A01, CWE-209).

Movimientos, transferencias y transformaciones solo operan sobre bodegas que
el usuario puede operar (`bodegas_visibles`): las suyas asignadas o, para el
Administrador de Sede, las de su sede. El destino de una transferencia o
transformación es de la sede del origen. Ninguna escritura crea ni reutiliza
lotes de producción ajenos, y la compra se registra solo por la recepción
F0-001 (`materia-prima/registrar-entrada/`). Técnicas ISTQB: partición de
equivalencia por bodega (asignada / no asignada / otra sede) y por rol.
"""
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from gestion.models import LoteProduccion
from gestion.tests.factories import (
    AreaFactory,
    BodegaFactory,
    CustomUserFactory,
    LoteProduccionFactory,
    OrdenProduccionFactory,
    ProductoFactory,
    SedeFactory,
    StockBodegaFactory,
)
from inventory.models import MovimientoInventario, StockBodega
from inventory.services.kardex_service import stock_a_fecha


def _stock(bodega, producto, lote=None):
    fila = StockBodega.objects.filter(bodega=bodega, producto=producto, lote=lote).first()
    return fila.cantidad if fila else Decimal('0')


class _BodegasMixin:
    """Sede A con una bodega asignada al bodeguero y otra no asignada; sede B ajena."""

    def setUp(self):
        self.client = APIClient()
        self.sede_a = SedeFactory()
        self.sede_b = SedeFactory()
        self.asignada = BodegaFactory(sede=self.sede_a)
        self.no_asignada = BodegaFactory(sede=self.sede_a)
        self.ajena = BodegaFactory(sede=self.sede_b)
        self.producto = ProductoFactory(sede=self.sede_a)
        self.producto_b = ProductoFactory(sede=self.sede_a)
        self.bodeguero = CustomUserFactory(sede=self.sede_a, groups=['bodeguero'])
        self.bodeguero.bodegas_asignadas.add(self.asignada)
        for bodega in (self.asignada, self.no_asignada, self.ajena):
            StockBodegaFactory(bodega=bodega, producto=self.producto, lote=None, cantidad=Decimal('100.00'))

    def _como(self, user):
        self.client.force_authenticate(user=user)
        return user


class MovimientoAlcanceTestCase(_BodegasMixin, TestCase):
    url = '/api/inventory/movimientos/'

    def test_movimiento_dado_bodega_no_asignada_cuando_ajuste_de_entrada_entonces_400_sin_stock(self):
        self._como(self.bodeguero)
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'AJUSTE', 'producto': self.producto.id, 'cantidad': '10.00',
            'bodega_destino': self.no_asignada.id,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(_stock(self.no_asignada, self.producto), Decimal('100.00'))

    def test_movimiento_dado_admin_sede_y_bodega_de_otra_sede_cuando_venta_entonces_400_sin_descontar(self):
        self._como(CustomUserFactory(sede=self.sede_a, groups=['admin_sede']))
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'VENTA', 'producto': self.producto.id, 'cantidad': '10.00',
            'bodega_origen': self.ajena.id,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(_stock(self.ajena, self.producto), Decimal('100.00'))

    def test_movimiento_dado_bodega_asignada_cuando_merma_entonces_201_y_descuenta(self):
        self._como(self.bodeguero)
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'MERMA', 'producto': self.producto.id, 'cantidad': '10.00',
            'bodega_origen': self.asignada.id,
        }, format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(_stock(self.asignada, self.producto), Decimal('90.00'))

    def test_movimiento_dado_compra_generica_cuando_post_entonces_400_sin_stock(self):
        # La compra se registra solo por la recepción F0-001 (lote de MP + costo).
        self._como(self.bodeguero)
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'COMPRA', 'producto': self.producto.id, 'cantidad': '10.00',
            'bodega_destino': self.asignada.id,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertIn('registrar-entrada', str(resp.data))
        self.assertEqual(_stock(self.asignada, self.producto), Decimal('100.00'))

    def test_movimiento_dado_lote_codigo_de_otro_lote_cuando_ajuste_entonces_no_crea_ni_engancha_lotes(self):
        area_b = AreaFactory(sede=self.sede_b)
        ajeno = LoteProduccionFactory(
            orden_produccion=OrdenProduccionFactory(sede=self.sede_b, area=area_b), codigo_lote='LOT-AJENO')
        self._como(self.bodeguero)
        antes = LoteProduccion.objects.count()
        self.client.post(self.url, {
            'tipo_movimiento': 'AJUSTE', 'producto': self.producto.id, 'cantidad': '5.00',
            'bodega_destino': self.asignada.id, 'lote_codigo': 'LOT-AJENO',
        }, format='json')
        self.assertEqual(LoteProduccion.objects.count(), antes)
        self.assertFalse(StockBodega.objects.filter(lote=ajeno, bodega=self.asignada).exists())

    def test_movimiento_dado_lote_de_otra_sede_cuando_ajuste_entonces_400(self):
        area_b = AreaFactory(sede=self.sede_b)
        ajeno = LoteProduccionFactory(orden_produccion=OrdenProduccionFactory(sede=self.sede_b, area=area_b))
        self._como(self.bodeguero)
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'AJUSTE', 'producto': self.producto.id, 'cantidad': '5.00',
            'bodega_destino': self.asignada.id, 'lote': ajeno.id,
        }, format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(StockBodega.objects.filter(lote=ajeno).exists())

    def test_movimiento_dado_error_interno_cuando_post_entonces_500_sin_detalle(self):
        self._como(self.bodeguero)
        with patch('inventory.views.movimiento_views.safe_get_or_create_stock',
                   side_effect=RuntimeError('detalle interno secreto')):
            resp = self.client.post(self.url, {
                'tipo_movimiento': 'AJUSTE', 'producto': self.producto.id, 'cantidad': '5.00',
                'bodega_destino': self.asignada.id,
            }, format='json')
        self.assertEqual(resp.status_code, 500)
        self.assertNotIn('detalle interno secreto', str(resp.data))


class TransferenciaAlcanceTestCase(_BodegasMixin, TestCase):
    url = '/api/inventory/transferencias/'

    def _payload(self, origen, destino):
        return {'producto_id': self.producto.id, 'bodega_origen_id': origen.id,
                'bodega_destino_id': destino.id, 'cantidad': '10.00'}

    def test_transferencia_dado_origen_no_asignado_cuando_post_entonces_400_sin_mover(self):
        self._como(self.bodeguero)
        resp = self.client.post(self.url, self._payload(self.no_asignada, self.asignada), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(_stock(self.no_asignada, self.producto), Decimal('100.00'))

    def test_transferencia_dado_destino_de_otra_sede_cuando_post_entonces_400_sin_mover(self):
        self._como(self.bodeguero)
        resp = self.client.post(self.url, self._payload(self.asignada, self.ajena), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(_stock(self.asignada, self.producto), Decimal('100.00'))

    def test_transferencia_dado_destino_de_su_sede_no_asignado_cuando_post_entonces_200(self):
        # El destino no necesita estar asignado: basta con que sea de la sede del origen.
        self._como(self.bodeguero)
        resp = self.client.post(self.url, self._payload(self.asignada, self.no_asignada), format='json')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(_stock(self.no_asignada, self.producto), Decimal('110.00'))

    def test_transferencia_dado_error_interno_cuando_post_entonces_500_sin_detalle(self):
        self._como(self.bodeguero)
        with patch('inventory.views.transferencia_views.MovimientoInventario.objects.create',
                   side_effect=RuntimeError('detalle interno secreto')):
            resp = self.client.post(self.url, self._payload(self.asignada, self.no_asignada), format='json')
        self.assertEqual(resp.status_code, 500)
        self.assertNotIn('detalle interno secreto', str(resp.data))


class TransformacionAlcanceTestCase(_BodegasMixin, TestCase):
    url = '/api/inventory/transformaciones/'

    def _payload(self, origen, destino, **extra):
        return {'bodega_origen_id': origen.id, 'bodega_destino_id': destino.id,
                'producto_origen_id': self.producto.id, 'producto_destino_id': self.producto_b.id,
                'cantidad': '10.00', '_justificacion_auditoria': 'Prueba de alcance', **extra}

    def test_transformacion_dado_vendedor_cuando_post_entonces_403_sin_mover(self):
        self._como(CustomUserFactory(sede=self.sede_a, groups=['vendedor']))
        resp = self.client.post(self.url, self._payload(self.asignada, self.asignada), format='json')
        self.assertEqual(resp.status_code, 403)
        self.assertEqual(_stock(self.asignada, self.producto), Decimal('100.00'))

    def test_transformacion_dado_origen_no_asignado_cuando_post_entonces_400_sin_mover(self):
        self._como(self.bodeguero)
        resp = self.client.post(self.url, self._payload(self.no_asignada, self.asignada), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(_stock(self.no_asignada, self.producto), Decimal('100.00'))

    def test_transformacion_dado_destino_de_otra_sede_cuando_post_entonces_400_sin_mover(self):
        self._como(self.bodeguero)
        resp = self.client.post(self.url, self._payload(self.asignada, self.ajena), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(_stock(self.asignada, self.producto), Decimal('100.00'))

    def test_transformacion_dado_nuevo_lote_con_codigo_de_otra_sede_cuando_post_entonces_400(self):
        area_b = AreaFactory(sede=self.sede_b)
        LoteProduccionFactory(
            orden_produccion=OrdenProduccionFactory(sede=self.sede_b, area=area_b), codigo_lote='LOT-B-1')
        self._como(self.bodeguero)
        resp = self.client.post(
            self.url, self._payload(self.asignada, self.asignada, nuevo_lote_codigo='LOT-B-1'), format='json')
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(_stock(self.asignada, self.producto), Decimal('100.00'))

    def test_transformacion_dado_bodegas_de_su_alcance_cuando_post_entonces_201(self):
        self._como(self.bodeguero)
        resp = self.client.post(self.url, self._payload(self.asignada, self.asignada), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(_stock(self.asignada, self.producto), Decimal('90.00'))
        self.assertTrue(MovimientoInventario.objects.filter(
            tipo_movimiento='PRODUCCION', producto=self.producto_b, bodega_destino=self.asignada).exists())

    def test_transformacion_dado_origen_y_destino_distintos_cuando_post_entonces_kardex_sin_entradas_fantasma(self):
        # El CONSUMO no lleva bodega de destino ni la PRODUCCION de origen: el
        # kárdex trata bodega_destino como entrada y bodega_origen como salida.
        self._como(self.bodeguero)
        self.bodeguero.bodegas_asignadas.add(self.no_asignada)
        resp = self.client.post(self.url, self._payload(self.asignada, self.no_asignada), format='json')
        self.assertEqual(resp.status_code, 201, resp.data)
        hoy = timezone.localdate().isoformat()
        origen = {f['bodega_id']: f['stock_calculado'] for f in stock_a_fecha(self.producto.id, hoy)}
        destino = {f['bodega_id']: f['stock_calculado'] for f in stock_a_fecha(self.producto_b.id, hoy)}
        self.assertEqual(origen, {self.asignada.id: Decimal('-10.00')})
        self.assertEqual(destino, {self.no_asignada.id: Decimal('10.00')})
