"""
Pruebas de validación de gestion/serializers.py.

Cubre validadores a nivel de campo y de objeto: regex alfanumérico con acentos,
y validaciones numéricas de la dosificación.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): entrada válida (letras/acentos) vs inválida
  (emoji/símbolos).
- Análisis de valores límite (BVA): kg_tela / relacion_bano = 0 (frontera) vs > 0.
"""
from decimal import Decimal

from django.test import TestCase

from gestion.serializers import AreaSerializer, DosificacionSerializer
from gestion.tests.factories import SedeFactory


class AreaNombreValidatorTestCase(TestCase):
    """validate_nombre: ALPHANUMERIC_ACCENTS_REGEX."""

    def setUp(self):
        self.sede = SedeFactory()

    def test_nombre_dado_letras_y_acentos_cuando_valida_entonces_ok(self):
        # EP válida: letras, Ñ, acentos y espacios
        s = AreaSerializer(data={'nombre': 'Tintorería Ñañez', 'sede': self.sede.id})
        self.assertTrue(s.is_valid(), s.errors)

    def test_nombre_dado_alfanumerico_cuando_valida_entonces_ok(self):
        s = AreaSerializer(data={'nombre': 'Area 12', 'sede': self.sede.id})
        self.assertTrue(s.is_valid(), s.errors)

    def test_nombre_dado_emoji_cuando_valida_entonces_invalido(self):
        # EP inválida: caracteres fuera del set permitido
        s = AreaSerializer(data={'nombre': 'Area 🚀', 'sede': self.sede.id})
        self.assertFalse(s.is_valid())
        self.assertIn('nombre', s.errors)

    def test_nombre_dado_simbolos_cuando_valida_entonces_invalido(self):
        s = AreaSerializer(data={'nombre': 'Area@#$', 'sede': self.sede.id})
        self.assertFalse(s.is_valid())
        self.assertIn('nombre', s.errors)


class DosificacionSerializerTestCase(TestCase):
    """validate_kg_tela / validate_relacion_bano: deben ser > 0."""

    def test_dosificacion_dado_valores_positivos_cuando_valida_entonces_ok(self):
        s = DosificacionSerializer(data={'kg_tela': '100.000', 'relacion_bano': '10.00'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_dosificacion_dado_kg_tela_cero_cuando_valida_entonces_invalido(self):
        # BVA: kg_tela = 0 (frontera) -> inválido
        s = DosificacionSerializer(data={'kg_tela': '0.000', 'relacion_bano': '10.00'})
        self.assertFalse(s.is_valid())
        self.assertIn('kg_tela', s.errors)

    def test_dosificacion_dado_relacion_cero_cuando_valida_entonces_invalido(self):
        # BVA: relacion_bano = 0 (frontera) -> inválido
        s = DosificacionSerializer(data={'kg_tela': '100.000', 'relacion_bano': '0.00'})
        self.assertFalse(s.is_valid())
        self.assertIn('relacion_bano', s.errors)
