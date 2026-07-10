"""
Pruebas de inventory/utils.py — safe_get_or_create_stock: get_or_create
robusto ante race conditions (IntegrityError) sobre StockBodega.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): fila no existe (se crea) / existe (se
  obtiene) / race condition (creada por otra transacción entre el SELECT y
  el INSERT).
"""
from unittest.mock import patch

from django.db import IntegrityError
from django.test import TestCase

from gestion.tests.factories import BodegaFactory, ProductoFactory
from inventory.models import StockBodega
from inventory.utils import safe_get_or_create_stock


class SafeGetOrCreateStockTestCase(TestCase):
    def setUp(self):
        self.bodega = BodegaFactory()
        self.producto = ProductoFactory()

    def test_dado_fila_no_existe_cuando_llama_entonces_la_crea(self):
        stock, created = safe_get_or_create_stock(StockBodega, bodega=self.bodega, producto=self.producto)
        self.assertTrue(created)
        self.assertEqual(stock.cantidad, 0)

    def test_dado_fila_ya_existe_cuando_llama_entonces_la_obtiene(self):
        existente = StockBodega.objects.create(bodega=self.bodega, producto=self.producto, cantidad='25.000')
        stock, created = safe_get_or_create_stock(StockBodega, bodega=self.bodega, producto=self.producto)
        self.assertFalse(created)
        self.assertEqual(stock.id, existente.id)

    def test_dado_defaults_explicitos_cuando_crea_entonces_los_usa(self):
        stock, created = safe_get_or_create_stock(
            StockBodega, bodega=self.bodega, producto=self.producto, defaults={'cantidad': '10.000'},
        )
        self.assertTrue(created)
        self.assertEqual(stock.cantidad, 10)

    def test_dado_race_condition_cuando_llama_entonces_reintenta_y_obtiene_la_fila(self):
        # Caja blanca: rama `except IntegrityError` -> la fila fue creada por
        # otra transacción concurrente entre el SELECT y el INSERT. Se acota
        # el patch a QuerySet.get_or_create (no a transaction.atomic, que es
        # un módulo compartido usado también por la validación de constraints
        # al crear `existente` en este mismo test).
        existente = StockBodega.objects.create(bodega=self.bodega, producto=self.producto, cantidad='5.000')

        with patch(
            'django.db.models.query.QuerySet.get_or_create',
            side_effect=IntegrityError('duplicate key — race condition simulada'),
        ):
            stock, created = safe_get_or_create_stock(StockBodega, bodega=self.bodega, producto=self.producto)

        self.assertFalse(created)
        self.assertEqual(stock.id, existente.id)
