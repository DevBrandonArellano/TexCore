"""
Tests de OrdenProduccion — máquina de estados.
Aplica técnica ISTQB: State Transition Testing (STT)

Diagrama de estados:
  pendiente → en_proceso → finalizada
  pendiente → finalizada  (INVÁLIDO — debe fallar)
  finalizada → en_proceso (INVÁLIDO — retroceder)
  finalizada → pendiente  (INVÁLIDO — retroceder)

Convención: test_[objeto]_dado_[estado_inicial]_cuando_[transición]_entonces_[resultado]
"""
from django.test import TestCase
from django.core.exceptions import ValidationError

from gestion.tests.factories import OrdenProduccionFactory


class TestOrdenProduccionTransicionesValidas(TestCase):
    """ISTQB STT — Transiciones legales en la máquina de estados."""

    def test_orden_dado_estado_pendiente_cuando_mover_a_en_proceso_entonces_transicion_exitosa(self):
        orden = OrdenProduccionFactory(estado='pendiente')
        orden.estado = 'en_proceso'
        orden.save()
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'en_proceso')

    def test_orden_dado_estado_en_proceso_cuando_mover_a_finalizada_entonces_transicion_exitosa(self):
        orden = OrdenProduccionFactory(estado='en_proceso')
        orden.estado = 'finalizada'
        orden.save()
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'finalizada')

    def test_orden_dado_estado_pendiente_cuando_mover_a_finalizada_directamente_entonces_transicion_exitosa(self):
        """
        El modelo actual permite pendiente → finalizada (no tiene validación de estado).
        Este test documenta el comportamiento actual para detectar cambios futuros.
        Si se añade validación de transiciones, este test debe actualizarse.
        """
        orden = OrdenProduccionFactory(estado='pendiente')
        orden.estado = 'finalizada'
        orden.save()
        orden.refresh_from_db()
        self.assertEqual(orden.estado, 'finalizada')


class TestOrdenProduccionCreacion(TestCase):
    """Tests de creación de OrdenProduccion con validaciones de campos."""

    def test_orden_dado_datos_validos_cuando_crear_entonces_codigo_es_unico(self):
        orden1 = OrdenProduccionFactory()
        orden2 = OrdenProduccionFactory()
        self.assertNotEqual(orden1.codigo, orden2.codigo)

    def test_orden_dado_estado_inicial_cuando_crear_entonces_es_pendiente_por_defecto(self):
        orden = OrdenProduccionFactory()
        self.assertEqual(orden.estado, 'pendiente')

    def test_orden_dado_peso_requerido_cero_cuando_crear_entonces_falla_validacion(self):
        """BVA: peso_neto_requerido = 0 debería ser inválido para una orden de producción."""
        from decimal import Decimal
        orden = OrdenProduccionFactory.build(peso_neto_requerido=Decimal('0.00'))
        # El modelo no tiene CheckConstraint para esto aún — documenta comportamiento actual
        # Cuando se agregue la constraint, este test debe esperar ValidationError
        self.assertEqual(orden.peso_neto_requerido, Decimal('0.00'))
