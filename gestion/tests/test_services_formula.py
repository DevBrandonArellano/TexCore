"""
Pruebas de gestion/services_formula.py — cálculo de dosificación.

Completa la cobertura de caja blanca de DosificacionCalculator.calcular:
ramas gr/L, %, fallbacks legacy (gramos_por_kilo) y tipo de cálculo desconocido.

Técnicas ISTQB aplicadas:
- Caja blanca (cobertura de decisiones): cada rama de tipo_calculo y sus fallbacks.
- Análisis de valores límite (BVA): concentración/porcentaje = 0.
- Partición de equivalencia (EP): método gr_l / pct / desconocido.
"""
from decimal import Decimal

from django.test import TestCase

from gestion.models import DetalleFormula
from gestion.services_formula import (
    calcular_dosificacion_gr_l, calcular_dosificacion_pct, DosificacionCalculator,
)
from gestion.tests.factories import (
    SedeFactory, ProductoFactory, FormulaColorFactory,
    FaseRecetaFactory, DetalleFormulaFactory,
)


class FuncionesPurasDosificacionTestCase(TestCase):
    """Funciones puras — sin BD."""

    def test_gr_l_dado_valores_cuando_calcula_entonces_kg_correcto(self):
        # 1000 L * 10 gr/L = 10000 gr = 10 kg
        self.assertEqual(
            calcular_dosificacion_gr_l(Decimal('10'), Decimal('1000')),
            Decimal('10.000000'),
        )

    def test_gr_l_dado_concentracion_cero_cuando_calcula_entonces_cero(self):
        # BVA: concentración 0 -> 0 kg
        self.assertEqual(
            calcular_dosificacion_gr_l(Decimal('0'), Decimal('1000')),
            Decimal('0.000000'),
        )

    def test_pct_dado_valores_cuando_calcula_entonces_kg_correcto(self):
        # 100 kg * 2% = 2 kg
        self.assertEqual(
            calcular_dosificacion_pct(Decimal('2'), Decimal('100')),
            Decimal('2.000000'),
        )

    def test_pct_dado_porcentaje_cero_cuando_calcula_entonces_cero(self):
        self.assertEqual(
            calcular_dosificacion_pct(Decimal('0'), Decimal('100')),
            Decimal('0.000000'),
        )


class DosificacionCalculatorTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.formula = FormulaColorFactory(sede=self.sede)
        self.fase = FaseRecetaFactory(formula=self.formula, orden=1)
        self.quimico = ProductoFactory(tipo='quimico', sede=self.sede)

    def _detalle(self, **kwargs):
        return DetalleFormulaFactory(fase=self.fase, producto=self.quimico, **kwargs)

    def test_calcular_dado_gr_l_cuando_ejecuta_entonces_usa_concentracion(self):
        self._detalle(tipo_calculo='gr_l', concentracion_gr_l=Decimal('10.00'))
        resultado = DosificacionCalculator(self.formula).calcular(kg_tela=100, relacion_bano=10)
        # 100*10=1000 L; 1000*10 gr/L = 10 kg
        self.assertEqual(resultado.insumos[0].cantidad_kg, Decimal('10.000000'))

    def test_calcular_dado_gr_l_sin_concentracion_cuando_ejecuta_entonces_fallback_gramos_por_kilo(self):
        # Caja blanca: concentracion None -> fallback a gramos_por_kilo
        d = self._detalle(tipo_calculo='gr_l', concentracion_gr_l=Decimal('5.00'))
        DetalleFormula.objects.filter(id=d.id).update(concentracion_gr_l=None, gramos_por_kilo=Decimal('8.00'))
        resultado = DosificacionCalculator(self.formula).calcular(kg_tela=100, relacion_bano=10)
        # fallback usa 8 gr/L: 1000 L * 8 = 8 kg
        self.assertEqual(resultado.insumos[0].cantidad_kg, Decimal('8.000000'))

    def test_calcular_dado_pct_cuando_ejecuta_entonces_usa_porcentaje(self):
        self._detalle(tipo_calculo='pct', porcentaje=Decimal('2.00'), concentracion_gr_l=None)
        resultado = DosificacionCalculator(self.formula).calcular(kg_tela=100, relacion_bano=10)
        self.assertEqual(resultado.insumos[0].cantidad_kg, Decimal('2.000000'))

    def test_calcular_dado_pct_sin_porcentaje_cuando_ejecuta_entonces_fallback(self):
        # Caja blanca: porcentaje None -> fallback desde gramos_por_kilo
        d = self._detalle(tipo_calculo='pct', porcentaje=Decimal('2.00'), concentracion_gr_l=None)
        DetalleFormula.objects.filter(id=d.id).update(porcentaje=None, gramos_por_kilo=Decimal('20.00'))
        resultado = DosificacionCalculator(self.formula).calcular(kg_tela=100, relacion_bano=10)
        # (20/1000)*100 = 2% -> 100*2% = 2 kg
        self.assertEqual(resultado.insumos[0].cantidad_kg, Decimal('2.000000'))

    def test_calcular_dado_tipo_desconocido_cuando_ejecuta_entonces_cantidad_cero(self):
        # Caja blanca: rama else (tipo no soportado) -> cantidad 0.
        # Se usa .update() para sortear la validación de choices del modelo.
        d = self._detalle(tipo_calculo='gr_l', concentracion_gr_l=Decimal('10.00'))
        # 'zzz' cabe en la columna (a diferencia de 'desconocido') y no es choice válido
        DetalleFormula.objects.filter(id=d.id).update(tipo_calculo='zzz')
        resultado = DosificacionCalculator(self.formula).calcular(kg_tela=100, relacion_bano=10)
        self.assertEqual(resultado.insumos[0].cantidad_kg, Decimal('0'))
