"""
Hoja de dosificación imprimible de una fórmula (rol Tintorero).

POST /api/formula-colors/{id}/imprimir-dosificacion/ con {peso, litros}: se imprime
la versión OFICIAL (la que usa planta), con la cantidad a pesar de cada insumo por
fase. Sin versión oficial se imprime la receta viva marcada como borrador.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): con / sin versión oficial; g/L / %; servicio arriba / caído.
- Análisis de valores límite (BVA): peso en cero.
"""

from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import DetalleFormula
from gestion.services.versionado_formula import VersionadoFormulaService
from gestion.tests.factories import (
    CustomUserFactory,
    DetalleFormulaFactory,
    FaseRecetaFactory,
    FormulaColorFactory,
    ProductoFactory,
    SedeFactory,
)

GENERAR_PDF = "gestion.views.formula_views.PrintingService.generate_formula_dosificacion_pdf"


class ImprimirDosificacionFormulaTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = SedeFactory(nombre="Planta Tintorería")
        self.tintorero = CustomUserFactory(sede=self.sede, groups=["tintorero"])
        self.client.force_authenticate(user=self.tintorero)

        self.formula = FormulaColorFactory(
            sede=self.sede,
            estado="en_pruebas",
            codigo="AZ-001",
            nombre_color="Azul Marino",
        )
        self.fase = FaseRecetaFactory(
            formula=self.formula, nombre="tintura", orden=1, ciclo=3, temperatura=70, tiempo=20
        )
        self.auxiliar = ProductoFactory(tipo="quimico", sede=self.sede, codigo="Q-001", descripcion="Igualante")
        self.colorante = ProductoFactory(tipo="quimico", sede=self.sede, codigo="C-AZ", descripcion="Colorante Azul")
        self.detalle_gr_l = DetalleFormulaFactory(
            fase=self.fase,
            producto=self.auxiliar,
            tipo_calculo="gr_l",
            concentracion_gr_l=Decimal("0.700"),
            orden_adicion=1,
        )
        DetalleFormulaFactory(
            fase=self.fase,
            producto=self.colorante,
            tipo_calculo="pct",
            concentracion_gr_l=None,
            porcentaje=Decimal("1.500"),
            orden_adicion=2,
        )
        self.url = f"/api/formula-colors/{self.formula.id}/imprimir-dosificacion/"

    def _oficializar(self):
        version = VersionadoFormulaService.crear_version(self.formula, "Ensayo aprobado en laboratorio", self.tintorero)
        VersionadoFormulaService.marcar_oficial(self.formula, version.numero, self.tintorero)
        return version

    def _imprimir(self, body=None):
        with patch(GENERAR_PDF, return_value=b"%PDF-hoja") as generar:
            resp = self.client.post(self.url, body or {"peso": "100", "litros": "800"}, format="json")
        return resp, generar

    def test_imprimir_dado_version_oficial_cuando_cambia_la_receta_viva_entonces_imprime_la_oficial(self):
        version = self._oficializar()
        DetalleFormula.objects.filter(pk=self.detalle_gr_l.pk).update(concentracion_gr_l=Decimal("5.000"))

        resp, generar = self._imprimir()

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        datos = generar.call_args.args[0]
        self.assertTrue(datos["es_oficial"])
        self.assertEqual(datos["version_numero"], version.numero)
        auxiliar = datos["fases"][0]["insumos"][0]
        self.assertEqual(auxiliar["dosis"], "0.7000 g/L")  # la oficial, no los 5 g/L de la viva
        self.assertEqual(auxiliar["cantidad_gr"], 560.0)  # 0,7 g/L × 800 L

    def test_imprimir_dado_receta_cuando_calcula_entonces_envia_fases_e_insumos_por_fase(self):
        self._oficializar()

        _, generar = self._imprimir()

        datos = generar.call_args.args[0]
        self.assertEqual(datos["formula_codigo"], "AZ-001")
        self.assertEqual(datos["formula_nombre"], "Azul Marino")
        self.assertEqual(datos["sede_nombre"], "Planta Tintorería")
        self.assertEqual((datos["peso_kg"], datos["litros_bano"], datos["relacion_bano"]), (100.0, 800.0, 8.0))
        fase = datos["fases"][0]
        self.assertEqual((fase["orden"], fase["ciclo"], fase["temperatura"], fase["tiempo"]), (1, 3, 70, 20))
        self.assertTrue(fase["proceso_nombre"])
        self.assertEqual([i["producto_codigo"] for i in fase["insumos"]], ["Q-001", "C-AZ"])
        colorante = fase["insumos"][1]
        self.assertEqual(colorante["dosis"], "1.5000 %")
        self.assertEqual(colorante["cantidad_gr"], 1500.0)  # 1,5 % de 100 kg
        self.assertEqual(colorante["cantidad_kg"], 1.5)

    def test_imprimir_dado_formula_sin_version_oficial_cuando_imprime_entonces_usa_la_viva_como_borrador(self):
        resp, generar = self._imprimir()

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        datos = generar.call_args.args[0]
        self.assertFalse(datos["es_oficial"])
        self.assertIsNone(datos["version_numero"])
        self.assertEqual(datos["fases"][0]["insumos"][0]["dosis"], "0.7000 g/L")

    def test_imprimir_dado_varias_fases_cuando_calcula_entonces_cada_insumo_queda_en_su_fase(self):
        jabonado = FaseRecetaFactory(formula=self.formula, nombre="lavado", orden=2, temperatura=90, tiempo=10)
        jabon = ProductoFactory(tipo="quimico", sede=self.sede, codigo="J-001", descripcion="Jabón")
        DetalleFormulaFactory(
            fase=jabonado, producto=jabon, tipo_calculo="gr_l", concentracion_gr_l=Decimal("1.000"), orden_adicion=1
        )
        self._oficializar()

        _, generar = self._imprimir()

        fases = generar.call_args.args[0]["fases"]
        self.assertEqual([f["orden"] for f in fases], [1, 2])
        self.assertEqual([i["producto_codigo"] for i in fases[1]["insumos"]], ["J-001"])
        self.assertEqual(fases[1]["insumos"][0]["cantidad_gr"], 800.0)

    def test_imprimir_dado_peso_cero_cuando_post_entonces_400_sin_llamar_al_servicio(self):
        resp, generar = self._imprimir({"peso": "0", "litros": "800"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        generar.assert_not_called()

    def test_imprimir_dado_sin_litros_cuando_post_entonces_400(self):
        resp, generar = self._imprimir({"peso": "100"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        generar.assert_not_called()

    def test_imprimir_dado_servicio_de_impresion_caido_cuando_post_entonces_503(self):
        with patch(GENERAR_PDF, return_value=None):
            resp = self.client.post(self.url, {"peso": "100", "litros": "800"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def test_imprimir_dado_formula_de_otra_sede_cuando_post_entonces_404(self):
        ajena = FormulaColorFactory(sede=SedeFactory(), estado="en_pruebas")
        with patch(GENERAR_PDF, return_value=b"%PDF") as generar:
            resp = self.client.post(
                f"/api/formula-colors/{ajena.id}/imprimir-dosificacion/",
                {"peso": "100", "litros": "800"},
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        generar.assert_not_called()

    def test_imprimir_dado_pdf_generado_cuando_responde_entonces_nombra_el_archivo_con_el_codigo(self):
        resp, _ = self._imprimir()
        self.assertEqual(resp.content, b"%PDF-hoja")
        self.assertIn("dosificacion_AZ-001.pdf", resp["Content-Disposition"])

    # TIME_ZONE es UTC: el «Generado» de la hoja va en hora de la planta (UTC-5).
    def test_imprimir_dado_hora_utc_cuando_arma_el_pdf_entonces_generado_en_hora_de_la_planta(self):
        from datetime import UTC, datetime

        with patch("gestion.views.formula_views.timezone.now", return_value=datetime(2026, 10, 27, 18, 23, tzinfo=UTC)):
            _, generar = self._imprimir()
        self.assertEqual(generar.call_args[0][0]["generado_en"], "27/10/2026 13:23")


class TextoDosisTestCase(TestCase):
    """La dosis impresa sale de la receta: g/L, %, o «—» si el insumo no trae su valor."""

    @staticmethod
    def _calculo(tipo, concentracion=None, porcentaje=None):
        from gestion.services.services_formula import ResultadoInsumo

        return ResultadoInsumo(
            producto_id=1,
            producto_descripcion="X",
            tipo_calculo=tipo,
            cantidad_kg=Decimal("0"),
            cantidad_gr=Decimal("0"),
            concentracion_gr_l=concentracion,
            porcentaje=porcentaje,
        )

    def test_texto_dosis_dado_cada_tipo_de_calculo_cuando_formatea_entonces_usa_su_unidad(self):
        from gestion.views.formula_views import _texto_dosis

        self.assertEqual(_texto_dosis(self._calculo("gr_l", concentracion=Decimal("2.5"))), "2.5000 g/L")
        self.assertEqual(_texto_dosis(self._calculo("pct", porcentaje=Decimal("1.25"))), "1.2500 %")
        self.assertEqual(_texto_dosis(self._calculo("gr_l")), "—")
        self.assertEqual(_texto_dosis(self._calculo("otro")), "—")
