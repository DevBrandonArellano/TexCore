"""
Pruebas de validaciones de entrada de DescargaQuimicosService.descargar_para_op
(gestion/services/descarga_quimicos.py).

Completa la cobertura de caja blanca de las guardas de configuración previas
al cálculo de dosificación.

Técnicas ISTQB aplicadas:
- Caja blanca (cobertura de decisiones): ramas `not bodega_quimicos` y
  `not formula_color`.
- Partición de equivalencia (EP): OP sin bodega de químicos / sin fórmula.
"""
from django.test import TestCase
from django.core.exceptions import ValidationError

from gestion.services.descarga_quimicos import DescargaQuimicosService
from gestion.tests.factories import (
    SedeFactory, BodegaFactory, CustomUserFactory,
    OrdenProduccionFactory,
)


class DescargaQuimicosValidacionesTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.user = CustomUserFactory(sede=self.sede)

    def test_descarga_dado_sin_bodega_quimicos_cuando_descarga_entonces_validation_error(self):
        # Caja blanca: rama `not orden.bodega_quimicos`
        orden = OrdenProduccionFactory(sede=self.sede, bodega_quimicos=None)
        with self.assertRaises(ValidationError) as ctx:
            DescargaQuimicosService.descargar_para_op(orden, self.user)
        self.assertIn('Bodega de químicos', str(ctx.exception))

    def test_descarga_dado_sin_formula_cuando_descarga_entonces_validation_error(self):
        # Caja blanca: rama `not orden.formula_color` (con bodega presente)
        orden = OrdenProduccionFactory(
            sede=self.sede,
            bodega_quimicos=BodegaFactory(sede=self.sede),
            formula_color=None,
        )
        with self.assertRaises(ValidationError) as ctx:
            DescargaQuimicosService.descargar_para_op(orden, self.user)
        self.assertIn('Fórmula de color', str(ctx.exception))
