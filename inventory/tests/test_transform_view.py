"""
Pruebas de inventory/transform_view.py — TransformacionAPIView.

Transforma stock de un producto Origen en un producto Destino: consume stock
en la bodega de origen y lo ingresa en la bodega de destino, registrando los
movimientos de inventario correspondientes (CONSUMO / PRODUCCION).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): campos obligatorios ausentes, sin
  justificación, sin stock de origen, lote_origen_id inválido.
- Análisis de valores límite (BVA): cantidad == 0, cantidad == stock disponible.
- Caja blanca: rama `nuevo_lote_codigo` (crea LoteProduccion) vs. mantiene el
  lote de origen; rama `lote_origen_id in ('0', 0, '')` tratada como "sin lote".
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from gestion.models import LoteProduccion
from gestion.tests.factories import BodegaFactory, CustomUserFactory, ProductoFactory, StockBodegaFactory
from inventory.models import MovimientoInventario, StockBodega


class TransformacionAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse('realizar-transformacion')
        self.user = CustomUserFactory()
        self.client.force_authenticate(user=self.user)

        self.bodega_origen = BodegaFactory()
        self.bodega_destino = BodegaFactory()
        self.producto_origen = ProductoFactory()
        self.producto_destino = ProductoFactory()
        self.stock_origen = StockBodegaFactory(
            bodega=self.bodega_origen, producto=self.producto_origen, cantidad=Decimal('100.000'),
        )

    def _payload(self, **overrides):
        base = {
            'bodega_origen_id': self.bodega_origen.id,
            'bodega_destino_id': self.bodega_destino.id,
            'producto_origen_id': self.producto_origen.id,
            'producto_destino_id': self.producto_destino.id,
            'cantidad': '20.000',
            '_justificacion_auditoria': 'Transformación de prueba QA',
        }
        base.update(overrides)
        return base

    def test_transformar_dado_usuario_no_autenticado_cuando_post_entonces_401(self):
        self.client.force_authenticate(user=None)
        resp = self.client.post(self.url, self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_transformar_dado_campo_obligatorio_faltante_cuando_post_entonces_400(self):
        payload = self._payload()
        del payload['cantidad']
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transformar_dado_sin_justificacion_cuando_post_entonces_400(self):
        payload = self._payload(_justificacion_auditoria='')
        resp = self.client.post(self.url, payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('justificaci', resp.data['error'].lower())

    def test_transformar_dado_cantidad_cero_cuando_post_entonces_400(self):
        # BVA: cantidad == 0 viola "la cantidad debe ser positiva"
        resp = self.client.post(self.url, self._payload(cantidad='0'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transformar_dado_cantidad_negativa_cuando_post_entonces_400(self):
        resp = self.client.post(self.url, self._payload(cantidad='-5'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transformar_dado_lote_origen_id_no_numerico_cuando_post_entonces_400(self):
        resp = self.client.post(self.url, self._payload(lote_origen_id='abc'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('lote_origen_id', resp.data['error'])

    def test_transformar_dado_sin_stock_registrado_en_origen_cuando_post_entonces_400(self):
        otro_producto = ProductoFactory()
        resp = self.client.post(
            self.url, self._payload(producto_origen_id=otro_producto.id), format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('No hay stock registrado', resp.data['error'])

    def test_transformar_dado_stock_insuficiente_cuando_post_entonces_400(self):
        resp = self.client.post(self.url, self._payload(cantidad='500.000'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Stock insuficiente', resp.data['error'])
        self.stock_origen.refresh_from_db()
        self.assertEqual(self.stock_origen.cantidad, Decimal('100.000'))  # No se tocó el stock

    def test_transformar_dado_datos_validos_cuando_post_entonces_201_y_mueve_stock(self):
        resp = self.client.post(self.url, self._payload(cantidad='20.000'), format='json')

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        self.stock_origen.refresh_from_db()
        self.assertEqual(self.stock_origen.cantidad, Decimal('80.000'))

        stock_destino = StockBodega.objects.get(
            bodega=self.bodega_destino, producto=self.producto_destino,
        )
        self.assertEqual(stock_destino.cantidad, Decimal('20.000'))

        self.assertEqual(
            MovimientoInventario.objects.filter(tipo_movimiento='CONSUMO', producto=self.producto_origen).count(), 1,
        )
        self.assertEqual(
            MovimientoInventario.objects.filter(
                tipo_movimiento='PRODUCCION', producto=self.producto_destino).count(), 1,
        )

    def test_transformar_dado_lote_origen_id_cero_cuando_post_entonces_trata_como_sin_lote(self):
        # Caja blanca: '0' se normaliza a None, no busca StockBodega por ese lote
        resp = self.client.post(self.url, self._payload(lote_origen_id='0'), format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_transformar_dado_nuevo_lote_codigo_cuando_post_entonces_crea_lote_de_destino(self):
        resp = self.client.post(
            self.url, self._payload(nuevo_lote_codigo='LOTE-TRANSF-001'), format='json',
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        nuevo_lote = LoteProduccion.objects.get(codigo_lote='LOTE-TRANSF-001')
        stock_destino = StockBodega.objects.get(
            bodega=self.bodega_destino, producto=self.producto_destino, lote=nuevo_lote,
        )
        self.assertEqual(stock_destino.cantidad, Decimal('20.000'))

    def test_transformar_dado_error_interno_cuando_post_entonces_500(self):
        # Caja blanca: rama `except Exception` -> 500 con detalle del error
        resp = self.client.post(
            self.url, self._payload(bodega_destino_id=999999), format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
