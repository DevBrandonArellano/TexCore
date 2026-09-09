"""
Pruebas de gestion/views/_common.py — helpers compartidos entre módulos de vistas.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): valor ausente/vacío, entero válido,
  no numérico, entero no positivo.
- Análisis de valores límite (BVA): el borde 0 (inválido) frente a 1 (válido).
"""
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from gestion.views._common import parse_int_param


class ParseIntParamTestCase(SimpleTestCase):
    def test_parse_int_param_dado_valor_none_cuando_parsea_entonces_retorna_none(self):
        self.assertIsNone(parse_int_param(None, 'area'))

    def test_parse_int_param_dado_valor_vacio_cuando_parsea_entonces_retorna_none(self):
        self.assertIsNone(parse_int_param('', 'area'))

    def test_parse_int_param_dado_valor_numerico_valido_cuando_parsea_entonces_retorna_int(self):
        self.assertEqual(parse_int_param('7', 'area'), 7)

    def test_parse_int_param_dado_valor_no_numerico_cuando_parsea_entonces_lanza_validation_error(self):
        with self.assertRaises(ValidationError) as ctx:
            parse_int_param('abc', 'area')
        self.assertIn('area', ctx.exception.detail)

    def test_parse_int_param_dado_valor_cero_cuando_parsea_entonces_lanza_validation_error(self):
        # BVA: borde inválido — 0 no es un identificador positivo.
        with self.assertRaises(ValidationError):
            parse_int_param('0', 'area')

    def test_parse_int_param_dado_valor_negativo_cuando_parsea_entonces_lanza_validation_error(self):
        with self.assertRaises(ValidationError):
            parse_int_param('-5', 'area')

    def test_parse_int_param_dado_valor_uno_cuando_parsea_entonces_retorna_uno(self):
        # BVA: borde válido inmediatamente superior al inválido.
        self.assertEqual(parse_int_param('1', 'area'), 1)
