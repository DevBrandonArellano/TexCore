"""
Pruebas de endpoints de inventory/views.py no cubiertos por la suite previa:
StockBodegaViewSet, TransferenciaStockAPIView, AlertasStockAPIView, KardexBodegaAPIView.

Técnicas ISTQB aplicadas:
- Tabla de decisión / caja blanca: ramas RBAC de get_queryset (admin vs bodeguero)
  y ramas de validación de la transferencia (stock insuficiente, sin stock).
- Particiones de equivalencia (EP): stock suficiente / insuficiente / inexistente.
- Análisis de valores límite (BVA): stock = cantidad solicitada (transferencia exacta).
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status

from gestion.tests.factories import (
    SedeFactory, BodegaFactory, ProductoFactory, CustomUserFactory,
    StockBodegaFactory,
)


class StockBodegaViewSetTestCase(TestCase):
    """Caja blanca de get_queryset: admin ve todo, bodeguero solo asignadas."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega1 = BodegaFactory(sede=self.sede)
        self.bodega2 = BodegaFactory(sede=self.sede)
        self.s1 = StockBodegaFactory(bodega=self.bodega1, producto=ProductoFactory(sede=self.sede))
        self.s2 = StockBodegaFactory(bodega=self.bodega2, producto=ProductoFactory(sede=self.sede))
        self.url = '/api/inventory/stock/'

    def test_stock_dado_admin_cuando_lista_entonces_ve_todo(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)

    def test_stock_dado_bodeguero_cuando_lista_entonces_solo_asignadas(self):
        bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        bodeguero.bodegas_asignadas.add(self.bodega1)
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)

    def test_stock_dado_filtro_sede_cuando_lista_entonces_filtra(self):
        otra_sede = SedeFactory()
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url, {'sede_id': otra_sede.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)


class TransferenciaStockAPIViewTestCase(TestCase):
    """Caja blanca de la transferencia atómica entre bodegas."""

    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.origen = BodegaFactory(sede=self.sede)
        self.destino = BodegaFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.user)
        self.url = '/api/inventory/transferencias/'

    def _stock_origen(self, cantidad):
        return StockBodegaFactory(bodega=self.origen, producto=self.producto, cantidad=Decimal(cantidad))

    def test_transferencia_dado_stock_suficiente_cuando_post_entonces_200(self):
        self._stock_origen('100.00')
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '30.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {resp.data}")

    def test_transferencia_dado_origen_igual_destino_cuando_post_entonces_400(self):
        # Caja negra: validate() rechaza origen == destino
        self._stock_origen('100.00')
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '10.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.origen.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transferencia_dado_stock_insuficiente_cuando_post_entonces_400(self):
        # EP: cantidad solicitada > disponible
        self._stock_origen('10.00')
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '50.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transferencia_dado_sin_stock_en_origen_cuando_post_entonces_404(self):
        # Caja blanca: rama StockBodega.DoesNotExist -> 404
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '5.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_transferencia_dado_sin_autenticar_cuando_post_entonces_401(self):
        # Sin permission_classes explícitos, DRF cae a AllowAny (bug de seguridad) —
        # este endpoint debe exigir autenticación como cualquier otro de escritura.
        self.client.force_authenticate(user=None)
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '10.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_transferencia_dado_vendedor_cuando_post_entonces_403(self):
        vendedor = CustomUserFactory(sede=self.sede, groups=['vendedor'])
        self.client.force_authenticate(user=vendedor)
        resp = self.client.post(self.url, {
            'producto_id': self.producto.id, 'cantidad': '10.00',
            'bodega_origen_id': self.origen.id, 'bodega_destino_id': self.destino.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class AlertasStockAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega = BodegaFactory(sede=self.sede)
        # Producto con stock_minimo=10 (default factory) y stock por debajo
        self.producto = ProductoFactory(sede=self.sede, stock_minimo=Decimal('10.000'))
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, cantidad=Decimal('5.000'))
        self.url = '/api/inventory/alertas-stock/'

    def test_alertas_dado_stock_bajo_minimo_cuando_get_entonces_lo_lista(self):
        admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=admin)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['faltante'], Decimal('5.000'))

    def test_alertas_dado_bodeguero_sin_asignacion_cuando_get_entonces_vacio(self):
        # Caja blanca: bodeguero sin bodegas asignadas no ve alertas ajenas
        bodeguero = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        self.client.force_authenticate(user=bodeguero)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 0)


class KardexBodegaAPIViewTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega = BodegaFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        self.client.force_authenticate(user=self.user)

    def test_kardex_dado_sin_producto_id_cuando_get_entonces_400(self):
        # Caja blanca: producto_id obligatorio
        resp = self.client.get(f'/api/inventory/bodegas/{self.bodega.id}/kardex/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_kardex_dado_sin_autenticar_cuando_get_entonces_401(self):
        # Sin permission_classes explícitos, DRF cae a AllowAny (bug de seguridad).
        self.client.force_authenticate(user=None)
        producto = ProductoFactory(sede=self.sede)
        resp = self.client.get(f'/api/inventory/bodegas/{self.bodega.id}/kardex/', {'producto_id': producto.id})
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
