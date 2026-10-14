"""
Requisitos de materiales de una orden (TEX-28), con el mismo cálculo que el MRP.

- Producto de entrada: lo que falta producir (1:1).
- Químicos: la dosificación de la orden (g/L sobre los litros de baño, % sobre el peso).
  Si ya se descargaron al crearla, se informan como descontados.
- Stock disponible en la bodega de la orden (entrada o químicos) y faltante (CA-2).

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): g/L / %; descargado / no; con / sin peso.
- Análisis de valores límite (BVA): stock igual al requerido, una unidad por debajo.
"""

from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import DescargaQuimicoOP
from gestion.tests.factories import BodegaFactory, CustomUserFactory, LoteProduccionFactory
from inventory.models import StockBodega
from inventory.tests.test_mrp import _EscenarioMRP


class RequisitosMaterialesOrdenTestCase(_EscenarioMRP):
    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.force_authenticate(user=CustomUserFactory(sede=self.sede, groups=["jefe_planta"]))
        self.orden.bodega_quimicos = self.bodega_q
        self.orden.save(update_fields=["bodega_quimicos"])

    def _requisitos(self, orden=None):
        resp = self.client.get(reverse("ordenproduccion-requisitos-materiales", args=[(orden or self.orden).id]))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return resp.data, {r["producto_codigo"]: r for r in resp.data["requisitos"]}

    def test_requisitos_dado_formula_en_g_l_y_pct_cuando_consulta_entonces_dosifica_como_la_descarga(self):
        _, reqs = self._requisitos()
        self.assertEqual(reqs["Q-IGU"]["cantidad_requerida"], Decimal("1.600"))  # 2 g/L × 800 L
        self.assertEqual(reqs["C-AZ"]["cantidad_requerida"], Decimal("1.500"))  # 1,5 % de 100 kg
        self.assertEqual(reqs["MP-ALG"]["cantidad_requerida"], Decimal("100.000"))
        self.assertTrue(reqs["MP-ALG"]["es_base"])
        self.assertEqual(reqs["MP-ALG"]["unidad"], "kg")

    def test_requisitos_dado_lotes_producidos_cuando_consulta_entonces_la_base_es_lo_pendiente(self):
        LoteProduccionFactory(orden_produccion=self.orden, peso_neto_producido=Decimal("40.000"))
        data, reqs = self._requisitos()
        self.assertEqual(reqs["MP-ALG"]["cantidad_requerida"], Decimal("60.000"))
        self.assertEqual(data["peso_pendiente"], Decimal("60.00"))

    def test_requisitos_dado_stock_insuficiente_en_la_bodega_de_la_orden_cuando_consulta_entonces_marca_faltante(self):
        StockBodega.objects.create(bodega=self.bodega_mp, producto=self.materia_prima, cantidad=Decimal("99.999"))
        StockBodega.objects.create(
            bodega=BodegaFactory(sede=self.sede), producto=self.materia_prima, cantidad=Decimal("500")
        )  # otra bodega: no cuenta para la orden
        _, reqs = self._requisitos()
        self.assertEqual(reqs["MP-ALG"]["stock_disponible"], Decimal("99.999"))
        self.assertEqual(reqs["MP-ALG"]["faltante"], Decimal("0.001"))

    def test_requisitos_dado_stock_igual_al_requerido_cuando_consulta_entonces_sin_faltante(self):
        StockBodega.objects.create(bodega=self.bodega_q, producto=self.quimico, cantidad=Decimal("1.600"))
        _, reqs = self._requisitos()
        self.assertEqual(reqs["Q-IGU"]["faltante"], Decimal("0"))

    def test_requisitos_dado_stock_comprometido_cuando_consulta_entonces_no_lo_cuenta(self):
        StockBodega.objects.create(
            bodega=self.bodega_q, producto=self.quimico, cantidad=Decimal("5"), stock_comprometido=Decimal("4")
        )
        _, reqs = self._requisitos()
        self.assertEqual(reqs["Q-IGU"]["stock_disponible"], Decimal("1.000"))
        self.assertEqual(reqs["Q-IGU"]["faltante"], Decimal("0.600"))

    def test_requisitos_dado_quimicos_ya_descargados_cuando_consulta_entonces_los_informa_sin_faltante(self):
        DescargaQuimicoOP.objects.create(
            orden_produccion=self.orden,
            producto=self.quimico,
            bodega=self.bodega_q,
            tipo_calculo="gr_l",
            cantidad_calculada_kg=Decimal("1.6"),
            estado="aplicada",
        )
        _, reqs = self._requisitos()
        self.assertTrue(reqs["Q-IGU"]["ya_descontado"])
        self.assertEqual(reqs["Q-IGU"]["faltante"], Decimal("0"))
        self.assertFalse(reqs["MP-ALG"]["ya_descontado"])

    def test_requisitos_dado_orden_sin_peso_cuando_consulta_entonces_advierte_sin_requisitos(self):
        orden = self._orden(peso_neto_requerido=None, codigo="OP-CONT-09")
        data, reqs = self._requisitos(orden)
        self.assertEqual(reqs, {})
        self.assertTrue(any("OP-CONT-09" in a for a in data["advertencias"]))
