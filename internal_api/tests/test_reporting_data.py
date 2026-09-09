"""
Pruebas de internal_api/services/reporting_data.py::get_stock_bajo().

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): stock por debajo/igual/por encima del mínimo.
- Análisis de valores límite (BVA): cantidad exactamente igual a stock_minimo (no es "bajo").
"""
from decimal import Decimal

from django.test import TestCase

from gestion.tests.factories import BodegaFactory, ProductoFactory, StockBodegaFactory
from internal_api.services.reporting_data import get_stock_bajo


class GetStockBajoTestCase(TestCase):
    def setUp(self):
        self.bodega = BodegaFactory()

    # EP: cantidad menor al stock_minimo del producto → aparece en el reporte
    def test_get_stock_bajo_dado_cantidad_menor_al_minimo_cuando_consulta_entonces_lo_incluye(self):
        producto = ProductoFactory(stock_minimo=Decimal('10.000'))
        StockBodegaFactory(bodega=self.bodega, producto=producto, cantidad=Decimal('5.000'))

        rows = get_stock_bajo(self.bodega.id)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['producto_codigo'], producto.codigo)
        self.assertEqual(rows[0]['cantidad'], Decimal('5.000'))
        self.assertEqual(rows[0]['stock_minimo'], Decimal('10.000'))

    # BVA: cantidad exactamente igual al mínimo → NO es "stock bajo"
    def test_get_stock_bajo_dado_cantidad_igual_al_minimo_cuando_consulta_entonces_no_lo_incluye(self):
        producto = ProductoFactory(stock_minimo=Decimal('10.000'))
        StockBodegaFactory(bodega=self.bodega, producto=producto, cantidad=Decimal('10.000'))

        rows = get_stock_bajo(self.bodega.id)

        self.assertEqual(rows, [])

    # EP: cantidad por encima del mínimo → no aparece
    def test_get_stock_bajo_dado_cantidad_sobre_el_minimo_cuando_consulta_entonces_no_lo_incluye(self):
        producto = ProductoFactory(stock_minimo=Decimal('10.000'))
        StockBodegaFactory(bodega=self.bodega, producto=producto, cantidad=Decimal('50.000'))

        rows = get_stock_bajo(self.bodega.id)

        self.assertEqual(rows, [])

    # EP: bodega distinta → no se mezcla en el resultado
    def test_get_stock_bajo_dado_stock_en_otra_bodega_cuando_consulta_entonces_no_lo_incluye(self):
        otra_bodega = BodegaFactory()
        producto = ProductoFactory(stock_minimo=Decimal('10.000'))
        StockBodegaFactory(bodega=otra_bodega, producto=producto, cantidad=Decimal('1.000'))

        rows = get_stock_bajo(self.bodega.id)

        self.assertEqual(rows, [])
