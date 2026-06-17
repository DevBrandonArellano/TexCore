"""
Pruebas de validación de inventory/serializers.py.

Cubre MovimientoInventarioUpdateSerializer (cantidad > 0, razón ≥ 10 chars)
y TransferenciaSerializer (origen ≠ destino).

Técnicas ISTQB aplicadas:
- Análisis de valores límite (BVA): cantidad = 0 (frontera), razón de 9 vs 10 chars.
- Caja negra: validate() de transferencia (origen == destino).
"""
from django.test import TestCase

from inventory.serializers import (
    MovimientoInventarioUpdateSerializer, TransferenciaSerializer,
)
from gestion.tests.factories import SedeFactory, BodegaFactory, ProductoFactory


class MovimientoUpdateSerializerTestCase(TestCase):
    def test_update_dado_cantidad_y_razon_validas_cuando_valida_entonces_ok(self):
        s = MovimientoInventarioUpdateSerializer(data={
            'cantidad': '5.000', 'razon_cambio': 'Ajuste por conteo físico',
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_update_dado_cantidad_cero_cuando_valida_entonces_invalido(self):
        # BVA: cantidad = 0 (frontera inferior) -> inválido
        s = MovimientoInventarioUpdateSerializer(data={
            'cantidad': '0.000', 'razon_cambio': 'Ajuste por conteo físico',
        })
        self.assertFalse(s.is_valid())
        self.assertIn('cantidad', s.errors)

    def test_update_dado_razon_de_9_chars_cuando_valida_entonces_invalido(self):
        # BVA: 9 caracteres (< 10) -> inválido
        s = MovimientoInventarioUpdateSerializer(data={
            'cantidad': '5.000', 'razon_cambio': '123456789',
        })
        self.assertFalse(s.is_valid())
        self.assertIn('razon_cambio', s.errors)

    def test_update_dado_razon_de_10_chars_cuando_valida_entonces_ok(self):
        # BVA: 10 caracteres (frontera) -> válido
        s = MovimientoInventarioUpdateSerializer(data={
            'cantidad': '5.000', 'razon_cambio': '1234567890',
        })
        self.assertTrue(s.is_valid(), s.errors)


class TransferenciaSerializerTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.producto = ProductoFactory(sede=self.sede)
        self.b1 = BodegaFactory(sede=self.sede)
        self.b2 = BodegaFactory(sede=self.sede)

    def test_transferencia_dado_bodegas_distintas_cuando_valida_entonces_ok(self):
        s = TransferenciaSerializer(data={
            'producto_id': self.producto.id, 'cantidad': '10.00',
            'bodega_origen_id': self.b1.id, 'bodega_destino_id': self.b2.id,
        })
        self.assertTrue(s.is_valid(), s.errors)

    def test_transferencia_dado_origen_igual_destino_cuando_valida_entonces_invalido(self):
        # Caja negra: validate() rechaza origen == destino
        s = TransferenciaSerializer(data={
            'producto_id': self.producto.id, 'cantidad': '10.00',
            'bodega_origen_id': self.b1.id, 'bodega_destino_id': self.b1.id,
        })
        self.assertFalse(s.is_valid())

    def test_transferencia_dado_cantidad_bajo_minimo_cuando_valida_entonces_invalido(self):
        # BVA: cantidad < 0.01 (min_value) -> inválido
        s = TransferenciaSerializer(data={
            'producto_id': self.producto.id, 'cantidad': '0.00',
            'bodega_origen_id': self.b1.id, 'bodega_destino_id': self.b2.id,
        })
        self.assertFalse(s.is_valid())
