"""
Un mismo color puede tener una fórmula por tipo de material (algodón, poliéster…)
dentro de la misma sede. La unicidad pasa de (nombre_color, sede) a
(nombre_color, tipo_sustrato, sede).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): mismo color con sustrato distinto, con el mismo
  sustrato, y en otra sede.
"""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from gestion.models import FormulaColor
from gestion.tests.factories import FormulaColorFactory, SedeFactory


class FormulaColorNombrePorSustratoTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()

    def test_formula_color_dado_mismo_color_con_otro_sustrato_cuando_se_guarda_entonces_se_acepta(self):
        FormulaColorFactory(sede=self.sede, codigo="AZ-ALG", nombre_color="Azul Marino", tipo_sustrato="algodon")

        FormulaColor.objects.create(
            sede=self.sede, codigo="AZ-POL", nombre_color="Azul Marino", tipo_sustrato="poliester"
        )

        self.assertEqual(FormulaColor.objects.filter(sede=self.sede, nombre_color="Azul Marino").count(), 2)

    def test_formula_color_dado_mismo_color_y_mismo_sustrato_cuando_se_guarda_entonces_se_rechaza(self):
        FormulaColorFactory(sede=self.sede, codigo="AZ-1", nombre_color="Azul Marino", tipo_sustrato="algodon")

        # Business validation en full_clean() (CLAUDE.md §3): el duplicado se rechaza antes de la BD.
        with self.assertRaises(ValidationError):
            FormulaColor.objects.create(
                sede=self.sede, codigo="AZ-2", nombre_color="Azul Marino", tipo_sustrato="algodon"
            )

    def test_formula_color_dado_mismo_color_y_sustrato_cuando_se_guarda_entonces_la_bd_tambien_lo_rechaza(self):
        # Segunda barrera: aunque se salte full_clean(), la restricción de la BD impide el duplicado.
        FormulaColorFactory(sede=self.sede, codigo="AZ-1", nombre_color="Azul Marino", tipo_sustrato="algodon")

        with self.assertRaises(IntegrityError), transaction.atomic():
            FormulaColor.objects.bulk_create(
                [FormulaColor(sede=self.sede, codigo="AZ-2", nombre_color="Azul Marino", tipo_sustrato="algodon")]
            )

    def test_formula_color_dado_mismo_color_y_sustrato_en_otra_sede_cuando_se_guarda_entonces_se_acepta(self):
        otra_sede = SedeFactory()
        FormulaColorFactory(sede=self.sede, codigo="AZ-1", nombre_color="Azul Marino", tipo_sustrato="algodon")

        FormulaColor.objects.create(
            sede=otra_sede, codigo="AZ-1", nombre_color="Azul Marino", tipo_sustrato="algodon"
        )

        self.assertEqual(FormulaColor.objects.filter(nombre_color="Azul Marino").count(), 2)
