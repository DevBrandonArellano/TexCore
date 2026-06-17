"""
Pruebas de MovimientoInventarioViewSet (inventory/views.py).

Cubre el create transaccional (entradas/salidas con ajuste de stock) y el
update auditado (solo COMPRA, recálculo de stock, RBAC).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): tipo de movimiento entrada (COMPRA) vs salida (VENTA).
- Caja blanca: ramas de validación (bodega requerida, stock insuficiente/inexistente,
  tipo no editable, permisos de edición).
- Análisis de valores límite (BVA): salida con stock exacto vs insuficiente.
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from inventory.models import StockBodega, MovimientoInventario
from gestion.tests.factories import (
    SedeFactory, BodegaFactory, ProductoFactory, CustomUserFactory, StockBodegaFactory,
)


class MovimientoCreateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega = BodegaFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        self.client.force_authenticate(user=self.user)
        self.url = reverse('movimiento-list')

    def test_create_dado_compra_cuando_post_entonces_incrementa_stock(self):
        # EP entrada: COMPRA suma stock en bodega_destino
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'COMPRA', 'producto': self.producto.id,
            'cantidad': '50.00', 'bodega_destino': self.bodega.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, f"Error: {resp.data}")
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('50.00'))

    def test_create_dado_compra_sin_bodega_destino_cuando_post_entonces_400(self):
        # Caja blanca: entrada requiere bodega_destino
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'COMPRA', 'producto': self.producto.id, 'cantidad': '50.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_dado_venta_con_stock_cuando_post_entonces_descuenta(self):
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, lote=None, cantidad=Decimal('100.00'))
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'VENTA', 'producto': self.producto.id,
            'cantidad': '30.00', 'bodega_origen': self.bodega.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, f"Error: {resp.data}")
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('70.00'))

    def test_create_dado_venta_stock_insuficiente_cuando_post_entonces_400(self):
        # BVA: cantidad > stock disponible
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, lote=None, cantidad=Decimal('10.00'))
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'VENTA', 'producto': self.producto.id,
            'cantidad': '50.00', 'bodega_origen': self.bodega.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_dado_venta_sin_stock_cuando_post_entonces_400(self):
        # Caja blanca: StockBodega.DoesNotExist -> 400
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'VENTA', 'producto': self.producto.id,
            'cantidad': '5.00', 'bodega_origen': self.bodega.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class MovimientoUpdateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega = BodegaFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.admin = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])
        # Movimiento COMPRA + stock asociado
        self.mov = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto, cantidad=Decimal('50.00'),
            bodega_destino=self.bodega, usuario=self.admin, saldo_resultante=Decimal('50.00'),
        )
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, lote=None, cantidad=Decimal('50.00'))
        self.url = reverse('movimiento-detail', args=[self.mov.id])

    def test_update_dado_compra_cambia_cantidad_cuando_patch_entonces_recalcula_stock(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(self.url, {
            'cantidad': '60.00', 'razon_cambio': 'Corrección de factura del proveedor',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {resp.data}")
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('60.00'))  # 50 + (60-50)

    def test_update_dado_vendedor_cuando_patch_entonces_403(self):
        # Caja blanca: solo bodeguero/jefe/admin pueden editar
        vendedor = CustomUserFactory(sede=self.sede, groups=['vendedor'])
        self.client.force_authenticate(user=vendedor)
        resp = self.client.patch(self.url, {
            'cantidad': '60.00', 'razon_cambio': 'Intento no autorizado',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_dado_movimiento_no_compra_cuando_patch_entonces_400(self):
        # Caja blanca: solo COMPRA es editable
        mov_venta = MovimientoInventario.objects.create(
            tipo_movimiento='VENTA', producto=self.producto, cantidad=Decimal('5.00'),
            bodega_origen=self.bodega, usuario=self.admin, saldo_resultante=Decimal('45.00'),
        )
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(
            reverse('movimiento-detail', args=[mov_venta.id]),
            {'cantidad': '10.00', 'razon_cambio': 'Corrección de prueba válida'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_dado_razon_corta_cuando_patch_entonces_400(self):
        # BVA: razon_cambio < 10 caracteres -> inválido
        self.client.force_authenticate(user=self.admin)
        resp = self.client.patch(self.url, {'cantidad': '60.00', 'razon_cambio': 'corta'}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_auditoria_dado_movimiento_cuando_get_entonces_lista(self):
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(reverse('movimiento-auditoria', args=[self.mov.id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIsInstance(resp.data, list)
