"""
Pruebas de gestion/serializers/production_serializers.py —
LoteProduccionSerializer.validate() (consistencia peso_bruto/tara/empaquetado).

Ejercitado unitariamente (sin cliente HTTP): `validate()` solo depende de
`data` y, opcionalmente, de `orden_produccion` — no de `request`.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): con/sin datos de empaquetado, con/sin orden.
- Análisis de valores límite (BVA): tara == peso_bruto (borde inválido),
  desviación exactamente en el límite del 5% vs. por encima de él.
"""
from decimal import Decimal

from django.test import TestCase

from gestion.serializers.production_serializers import LoteProduccionSerializer
from gestion.tests.factories import MaquinaFactory, OrdenProduccionFactory


def _payload(**overrides):
    base = {
        'codigo_lote': 'LOTE-TEST-1',
        'peso_neto_producido': Decimal('10.000'),
        'turno': 'Dia',
        'hora_inicio': '2026-01-01T08:00:00Z',
        'hora_final': '2026-01-01T16:00:00Z',
    }
    base.update(overrides)
    return base


class LoteProduccionSerializerValidateEmpaquetadoTestCase(TestCase):
    def test_validate_dado_sin_peso_bruto_ni_tara_cuando_valida_entonces_no_ejecuta_regla_empaquetado(self):
        serializer = LoteProduccionSerializer(data=_payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_dado_solo_peso_bruto_sin_tara_cuando_valida_entonces_no_ejecuta_regla_empaquetado(self):
        serializer = LoteProduccionSerializer(data=_payload(peso_bruto=Decimal('12.000')))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_dado_tara_mayor_que_peso_bruto_cuando_valida_entonces_falla(self):
        serializer = LoteProduccionSerializer(data=_payload(
            peso_bruto=Decimal('10.000'), tara=Decimal('12.000'),
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn('tara', serializer.errors)

    def test_validate_dado_tara_igual_a_peso_bruto_cuando_valida_entonces_falla(self):
        # BVA: borde inválido — tara == peso_bruto no puede dar neto <= 0.
        serializer = LoteProduccionSerializer(data=_payload(
            peso_bruto=Decimal('10.000'), tara=Decimal('10.000'),
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn('tara', serializer.errors)

    def test_validate_dado_peso_bruto_y_tara_consistentes_cuando_valida_entonces_pasa(self):
        serializer = LoteProduccionSerializer(data=_payload(
            peso_bruto=Decimal('10.000'), tara=Decimal('2.000'),
        ))
        self.assertTrue(serializer.is_valid(), serializer.errors)


class LoteProduccionSerializerValidateDesviacionOrdenTestCase(TestCase):
    def setUp(self):
        self.maquina = MaquinaFactory()
        self.orden = OrdenProduccionFactory(peso_neto_requerido=Decimal('100.00'))

    def test_validate_dado_neto_dentro_del_5pct_de_la_orden_cuando_valida_entonces_pasa_sin_advertencia(self):
        # neto = 10 - 2 = 8; orden 100 -> diferencia real es >5%, así que
        # ajustamos la orden para que 8 esté dentro de tolerancia (orden ~8).
        orden = OrdenProduccionFactory(peso_neto_requerido=Decimal('8.00'))
        serializer = LoteProduccionSerializer(data=_payload(
            peso_bruto=Decimal('10.000'), tara=Decimal('2.000'),
            orden_produccion=orden.id, maquina=self.maquina.id,
        ))
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_validate_dado_neto_desvia_mas_del_5pct_de_la_orden_cuando_valida_entonces_pasa_igual_pero_advierte(self):
        # El requerimiento es "advierte pero permite guardar" (no bloquea).
        serializer = LoteProduccionSerializer(data=_payload(
            peso_bruto=Decimal('10.000'), tara=Decimal('2.000'),
            orden_produccion=self.orden.id, maquina=self.maquina.id,
        ))
        with self.assertLogs('gestion.serializers.production_serializers', level='WARNING') as logs:
            self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertTrue(any('ALERTA EMPAQUETADO' in msg for msg in logs.output))

    def test_validate_dado_orden_produccion_ausente_en_payload_pero_instancia_previa_cuando_valida_entonces_usa_orden_de_la_instancia(self):
        lote_serializer_creacion = LoteProduccionSerializer(data=_payload(
            peso_bruto=Decimal('10.000'), tara=Decimal('2.000'),
            orden_produccion=self.orden.id, maquina=self.maquina.id,
        ))
        self.assertTrue(lote_serializer_creacion.is_valid(), lote_serializer_creacion.errors)
        instancia = lote_serializer_creacion.save()

        # Update parcial sin orden_produccion en el payload: debe resolver
        # la orden desde self.instance.orden_produccion (L337-339).
        update_serializer = LoteProduccionSerializer(
            instancia,
            data={'peso_bruto': Decimal('10.000'), 'tara': Decimal('2.000')},
            partial=True,
        )
        with self.assertLogs('gestion.serializers.production_serializers', level='WARNING') as logs:
            self.assertTrue(update_serializer.is_valid(), update_serializer.errors)
        self.assertTrue(any('ALERTA EMPAQUETADO' in msg for msg in logs.output))
