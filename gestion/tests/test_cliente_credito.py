"""
Tests de Cliente — límite de crédito.
Aplica técnicas ISTQB:
  - Partición de Equivalencia (EP)
  - Análisis de Valores Límite (BVA)
Convención de nombres: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]
"""
from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError

from gestion.tests.factories import ClienteFactory, SedeFactory


class TestClienteLimiteCredito_ParticionEquivalencia(TestCase):
    """
    ISTQB EP — Clases de equivalencia para limite_credito:
      Válida:   limite_credito >= 0
      Inválida: limite_credito < 0
    """

    def test_cliente_dado_limite_credito_cero_cuando_crear_entonces_es_valido(self):
        """BVA: valor mínimo exacto del límite."""
        cliente = ClienteFactory.build(limite_credito=Decimal('0.000'))
        # No debe lanzar excepción de validación de BD
        cliente.full_clean()

    def test_cliente_dado_limite_credito_positivo_cuando_crear_entonces_es_valido(self):
        """EP Clase Válida: cualquier valor positivo."""
        cliente = ClienteFactory(limite_credito=Decimal('500.000'))
        self.assertEqual(cliente.limite_credito, Decimal('500.000'))

    def test_cliente_dado_limite_credito_grande_cuando_crear_entonces_es_valido(self):
        """BVA: valor alto permitido por el campo (max_digits=12, decimal_places=3)."""
        cliente = ClienteFactory(limite_credito=Decimal('999999999.999'))
        self.assertGreater(cliente.limite_credito, Decimal('0'))

    def test_cliente_dado_limite_credito_negativo_cuando_guardar_entonces_falla_constraint_bd(self):
        """
        EP Clase Inválida + BVA: -0.001 viola el CheckConstraint de BD.
        La restricción está en gestion_cliente_limite_credito_positivo.
        """
        from django.db import IntegrityError
        with self.assertRaises((IntegrityError, ValidationError)):
            ClienteFactory(limite_credito=Decimal('-0.001'))


class TestClienteAuditoria_RequistoJustificacion(TestCase):
    """
    Tests del comportamiento de auditoría del Cliente.
    Verifica que se requiera justificación para cambiar campos críticos.
    """

    def test_cliente_dado_cambio_limite_credito_sin_justificacion_cuando_guardar_entonces_lanza_ValidationError(self):
        """Los campos auditables sin justificación deben rechazarse."""
        cliente = ClienteFactory(limite_credito=Decimal('100.000'))
        cliente.limite_credito = Decimal('200.000')
        # Sin _justificacion_auditoria debe fallar
        with self.assertRaises(ValidationError):
            cliente.save()

    def test_cliente_dado_cambio_limite_credito_con_justificacion_cuando_guardar_entonces_persiste(self):
        """Con justificación el cambio debe guardarse."""
        cliente = ClienteFactory(limite_credito=Decimal('100.000'))
        cliente.limite_credito = Decimal('200.000')
        cliente._justificacion_auditoria = "Aprobado por Gerencia — solicitud #123"
        cliente.save()
        cliente.refresh_from_db()
        self.assertEqual(cliente.limite_credito, Decimal('200.000'))

    def test_cliente_dado_sin_cambios_auditables_cuando_guardar_entonces_no_requiere_justificacion(self):
        """Si no cambia ningún campo auditable, no se necesita justificación."""
        cliente = ClienteFactory(limite_credito=Decimal('100.000'))
        # Cambiar un campo no auditable (como nombre_razon_social no está en campos_auditables por defecto)
        cliente.tiene_beneficio = not cliente.tiene_beneficio
        # No debe lanzar excepción
        cliente.save()
