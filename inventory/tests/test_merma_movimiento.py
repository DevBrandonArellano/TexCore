"""
Pruebas de control de Merma en MovimientoInventarioViewSet.create() —
`tipo_movimiento='MERMA'` existe como choice (inventory/models.py) pero antes
de este cambio no estaba en ninguna rama de create() (ni entrada ni salida):
el registro se creaba en el Kardex pero NUNCA descontaba StockBodega (un
movimiento "huérfano" desde el punto de vista contable).

Técnicas ISTQB:
- EP: MERMA es una SALIDA de inventario (el material se pierde), mismo
  tratamiento que VENTA/CONSUMO.
- BVA: cantidad == stock disponible (límite exacto) vs. cantidad > stock.
- Caja blanca: rama `StockBodega.DoesNotExist` -> 400 (sin stock previo).
"""
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from inventory.models import StockBodega
from gestion.tests.factories import (
    SedeFactory, BodegaFactory, ProductoFactory, CustomUserFactory, StockBodegaFactory,
)


class MovimientoMermaCreateTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory()
        self.bodega = BodegaFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['bodeguero'])
        self.client.force_authenticate(user=self.user)
        self.url = reverse('movimiento-list')

    def test_create_dado_merma_con_stock_suficiente_cuando_post_entonces_descuenta(self):
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, lote=None, cantidad=Decimal('100.00'))
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'MERMA', 'producto': self.producto.id,
            'cantidad': '30.00', 'bodega_origen': self.bodega.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, f"Error: {resp.data}")
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('70.00'))
        self.assertEqual(Decimal(resp.data['saldo_resultante']), Decimal('70.00'))

    def test_create_dado_merma_cantidad_igual_a_stock_cuando_post_entonces_descuenta_a_cero(self):
        # BVA: límite exacto — cantidad == stock disponible
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, lote=None, cantidad=Decimal('20.00'))
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'MERMA', 'producto': self.producto.id,
            'cantidad': '20.00', 'bodega_origen': self.bodega.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, f"Error: {resp.data}")
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('0.00'))

    def test_create_dado_merma_stock_insuficiente_cuando_post_entonces_400(self):
        StockBodegaFactory(bodega=self.bodega, producto=self.producto, lote=None, cantidad=Decimal('10.00'))
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'MERMA', 'producto': self.producto.id,
            'cantidad': '50.00', 'bodega_origen': self.bodega.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        # No debe haber modificado el stock existente
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('10.00'))

    def test_create_dado_merma_sin_stock_previo_cuando_post_entonces_400(self):
        # Caja blanca: StockBodega.DoesNotExist -> 400 (mismo patrón que VENTA/CONSUMO)
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'MERMA', 'producto': self.producto.id,
            'cantidad': '5.00', 'bodega_origen': self.bodega.id,
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_dado_merma_sin_bodega_origen_cuando_post_entonces_400(self):
        resp = self.client.post(self.url, {
            'tipo_movimiento': 'MERMA', 'producto': self.producto.id, 'cantidad': '5.00',
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
