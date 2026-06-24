"""
Tests del modelo TransformacionProducto — registro granular máquina a máquina.

Técnicas ISTQB aplicadas:
- EP (Equivalence Partitioning): clases válidas/inválidas de pesos y secuencia.
- BVA (Boundary Value Analysis): merma=0 (peso_entrada==peso_salida), límite peso.
- Caja blanca: ramas de clean() y cálculo de merma en save().

Convención: test_<objeto>_dado_<contexto>_cuando_<accion>_entonces_<resultado>
"""
from decimal import Decimal
from datetime import datetime

from django.core.exceptions import ValidationError
from django.test import TestCase

from gestion.tests.factories import (
    OrdenProduccionFactory, MaquinaFactory, ProductoFactory, CustomUserFactory,
)


def _transf_kwargs(orden, **overrides):
    """Datos mínimos válidos para construir una TransformacionProducto."""
    defaults = {
        'orden_produccion': orden,
        'producto_entrada': orden.producto_entrada,
        'producto_salida': orden.producto_salida,
        'maquina': MaquinaFactory(area=orden.area),
        'peso_entrada': Decimal('100.000'),
        'peso_salida': Decimal('98.000'),
        'fecha_inicio': datetime(2026, 1, 1, 8, 0),
        'fecha_fin': datetime(2026, 1, 1, 12, 0),
    }
    defaults.update(overrides)
    return defaults


class TransformacionProductoMermaTest(TestCase):
    """Cálculo de merma y validaciones de peso."""

    def setUp(self):
        self.orden = OrdenProduccionFactory()

    # EP válida + comportamiento principal
    def test_transformacion_dado_pesos_validos_cuando_crear_entonces_calcula_merma(self):
        from gestion.models import TransformacionProducto
        t = TransformacionProducto.objects.create(**_transf_kwargs(self.orden))
        self.assertEqual(t.merma, Decimal('2.000'))

    # BVA: peso_entrada == peso_salida → merma exactamente 0 (válido)
    def test_transformacion_dado_peso_igual_cuando_crear_entonces_merma_cero(self):
        from gestion.models import TransformacionProducto
        t = TransformacionProducto.objects.create(
            **_transf_kwargs(self.orden, peso_entrada=Decimal('50.000'), peso_salida=Decimal('50.000'))
        )
        self.assertEqual(t.merma, Decimal('0.000'))

    # EP inválida / BVA: peso_salida > peso_entrada → merma negativa → ValidationError
    def test_transformacion_dado_peso_salida_mayor_cuando_clean_entonces_falla(self):
        from gestion.models import TransformacionProducto
        t = TransformacionProducto(
            **_transf_kwargs(self.orden, peso_entrada=Decimal('50.000'), peso_salida=Decimal('50.001'))
        )
        with self.assertRaises(ValidationError):
            t.full_clean()

    # Caja blanca: rama fecha_fin < fecha_inicio
    def test_transformacion_dado_fecha_fin_anterior_cuando_clean_entonces_falla(self):
        from gestion.models import TransformacionProducto
        t = TransformacionProducto(
            **_transf_kwargs(
                self.orden,
                fecha_inicio=datetime(2026, 1, 1, 12, 0),
                fecha_fin=datetime(2026, 1, 1, 8, 0),
            )
        )
        with self.assertRaises(ValidationError):
            t.full_clean()

    # BVA: fecha_inicio == fecha_fin → duración cero es válida (borde inferior)
    def test_transformacion_dado_fecha_inicio_igual_fin_cuando_clean_entonces_valido(self):
        from gestion.models import TransformacionProducto
        instante = datetime(2026, 1, 1, 8, 0)
        t = TransformacionProducto(
            **_transf_kwargs(self.orden, fecha_inicio=instante, fecha_fin=instante)
        )
        t.full_clean()  # no debe lanzar

    # BVA: precisión decimal de 3 dígitos en la merma
    def test_transformacion_dado_pesos_con_milesimos_cuando_crear_entonces_merma_preserva_precision(self):
        from gestion.models import TransformacionProducto
        t = TransformacionProducto.objects.create(
            **_transf_kwargs(self.orden, peso_entrada=Decimal('10.001'), peso_salida=Decimal('10.000'))
        )
        self.assertEqual(t.merma, Decimal('0.001'))

    # EP inválida / BVA: peso_entrada == 0 → no se puede transformar "nada"
    def test_transformacion_dado_peso_entrada_cero_cuando_clean_entonces_falla(self):
        from gestion.models import TransformacionProducto
        t = TransformacionProducto(
            **_transf_kwargs(self.orden, peso_entrada=Decimal('0.000'), peso_salida=Decimal('0.000'))
        )
        with self.assertRaises(ValidationError):
            t.full_clean()

    # EP: estado 'rechazada' se persiste
    def test_transformacion_dado_estado_rechazada_cuando_crear_entonces_se_persiste(self):
        from gestion.models import TransformacionProducto
        t = TransformacionProducto.objects.create(
            **_transf_kwargs(self.orden, estado='rechazada')
        )
        t.refresh_from_db()
        self.assertEqual(t.estado, 'rechazada')


class TransformacionProductoSecuenciaTest(TestCase):
    """Unicidad de numero_secuencia dentro de una OP."""

    def setUp(self):
        self.orden = OrdenProduccionFactory()

    def test_transformacion_dado_misma_secuencia_en_op_cuando_crear_entonces_viola_unicidad(self):
        # AuditableModelMixin.save() llama full_clean(), por lo que la colisión de
        # unique_together se reporta como ValidationError (validate_unique), no IntegrityError.
        from gestion.models import TransformacionProducto
        TransformacionProducto.objects.create(**_transf_kwargs(self.orden, numero_secuencia=1))
        with self.assertRaises(ValidationError):
            TransformacionProducto.objects.create(**_transf_kwargs(self.orden, numero_secuencia=1))
