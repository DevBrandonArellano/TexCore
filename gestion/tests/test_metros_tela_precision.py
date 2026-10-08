"""
TEX-18 CA-4: los metros de tela se guardan con 4 decimales, sin pérdida por redondeo.

Hasta el 7-oct-2026, `LoteProduccion.cantidad_metros` era DECIMAL(10, 2) mientras el
modelo MES (`DetalleOperacionProduccion.cantidad_metros`) y CLAUDE.md usan DECIMAL(12, 4):
la operación MES redondeaba a 4 decimales y el lote que generaba guardaba solo 2. Los
kilogramos siguen con 3 decimales (estándar del kárdex), decisión del usuario.

Técnica ISTQB: valores límite (4 decimales se aceptan, 5 se rechazan; máximo de 8 enteros).
"""
from decimal import Decimal

from django.test import TestCase

from gestion.models import LoteProduccion
from gestion.serializers.production_serializers import (
    LoteProduccionSerializer,
    RegistrarLoteProduccionSerializer,
)
from gestion.tests.factories import LoteProduccionFactory

BASE_REGISTRO = {
    'peso_neto_producido': '10.00',
    'hora_inicio': '2026-10-07T08:00:00Z',
    'hora_final': '2026-10-07T09:00:00Z',
}


class MetrosTelaPrecisionTestCase(TestCase):
    def test_lote_dado_metros_con_4_decimales_cuando_guarda_entonces_los_conserva_exactos(self):
        lote = LoteProduccionFactory(cantidad_metros=Decimal('1234.5678'))
        lote.refresh_from_db()
        self.assertEqual(lote.cantidad_metros, Decimal('1234.5678'))

    def test_campo_metros_dado_modelo_cuando_se_inspecciona_entonces_es_decimal_12_4(self):
        campo = LoteProduccion._meta.get_field('cantidad_metros')
        self.assertEqual((campo.max_digits, campo.decimal_places), (12, 4))

    def test_registrar_lote_dado_metros_con_4_decimales_cuando_valida_entonces_acepta(self):
        s = RegistrarLoteProduccionSerializer(data={**BASE_REGISTRO, 'cantidad_metros': '600.1234'})
        self.assertTrue(s.is_valid(), s.errors)
        self.assertEqual(s.validated_data['cantidad_metros'], Decimal('600.1234'))

    def test_registrar_lote_dado_metros_con_5_decimales_cuando_valida_entonces_rechaza(self):
        s = RegistrarLoteProduccionSerializer(data={**BASE_REGISTRO, 'cantidad_metros': '600.12345'})
        self.assertFalse(s.is_valid())
        self.assertIn('cantidad_metros', s.errors)

    def test_registrar_lote_dado_metros_en_el_maximo_de_enteros_cuando_valida_entonces_acepta(self):
        s = RegistrarLoteProduccionSerializer(data={**BASE_REGISTRO, 'cantidad_metros': '99999999.9999'})
        self.assertTrue(s.is_valid(), s.errors)

    def test_lote_serializer_dado_metros_con_4_decimales_cuando_serializa_entonces_no_redondea(self):
        lote = LoteProduccionFactory(cantidad_metros=Decimal('0.0001'))
        self.assertEqual(LoteProduccionSerializer(lote).data['cantidad_metros'], '0.0001')
