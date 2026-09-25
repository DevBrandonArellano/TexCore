"""
Estado de la OP al registrar un lote (RegistroLoteService.registrar_lote), camino principal por el
que planta lanza una orden (spec 2026-09-24, reglas 4-5).

Técnicas ISTQB:
- Transición de estados (STT): pendiente -> en_proceso / finalizada al registrar lotes.
- Partición de equivalencia (EP): OP con peso requerido / sin él (producción continua);
  fórmula con versión oficial / sin ella.
"""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from gestion.models import LoteProduccion, OrdenProduccion
from gestion.services.registro_lote import RegistroLoteService
from gestion.tests.factories import (
    CustomUserFactory, FormulaColorFactory, OrdenProduccionFactory, StockBodegaFactory,
)
from inventory.models import StockBodega

LOTE = {
    'peso_merma': '0.00', 'tipo_merma': 'maquina', 'turno': 'Dia',
    'hora_inicio': '2026-09-01T08:00:00Z', 'hora_final': '2026-09-01T10:00:00Z',
}


class RegistroLoteEstadoOrdenTestCase(TestCase):

    def setUp(self):
        self.orden = OrdenProduccionFactory(peso_neto_requerido=Decimal('100.00'))
        self.user = CustomUserFactory(sede=self.orden.sede)
        self.stock_mp = StockBodegaFactory(
            bodega=self.orden.bodega_entrada, producto=self.orden.producto_entrada,
            cantidad=Decimal('1000.00'), lote=None,
        )

    def _registrar(self, peso, completar=False):
        RegistroLoteService.registrar_lote(
            self.orden, dict(LOTE, peso_neto_producido=peso), self.user, completar_orden=completar)
        self.orden.refresh_from_db()

    def test_registro_dado_lote_parcial_cuando_registra_entonces_orden_en_proceso(self):
        self._registrar('40.00')
        self.assertEqual(self.orden.estado, 'en_proceso')

    def test_registro_dado_lote_que_completa_el_peso_cuando_registra_entonces_orden_finalizada(self):
        self._registrar('100.00')
        self.assertEqual(self.orden.estado, 'finalizada')

    def test_registro_dado_orden_sin_peso_requerido_cuando_registra_entonces_queda_en_proceso(self):
        # Producción continua: sin meta de peso (antes: TypeError al comparar con None)
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(peso_neto_requerido=None)
        self.orden.refresh_from_db()
        self._registrar('40.00')
        self.assertEqual(self.orden.estado, 'en_proceso')

    def test_registro_dado_orden_sin_peso_requerido_y_completar_cuando_registra_entonces_finaliza(self):
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(peso_neto_requerido=None)
        self.orden.refresh_from_db()
        self._registrar('40.00', completar=True)
        self.assertEqual(self.orden.estado, 'finalizada')

    def test_registro_dado_formula_con_version_oficial_cuando_registra_entonces_congela_la_version(self):
        formula = FormulaColorFactory(sede=self.orden.sede, estado='aprobada')
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(formula_color=formula)
        self.orden.refresh_from_db()
        self._registrar('40.00')
        self.assertEqual(self.orden.version_formula, formula.versiones.get(es_oficial=True))

    def test_registro_dado_formula_sin_version_oficial_cuando_registra_entonces_error_y_revierte_todo(self):
        formula = FormulaColorFactory(sede=self.orden.sede, estado='en_pruebas')
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(formula_color=formula)
        self.orden.refresh_from_db()
        with self.assertRaises(ValidationError):
            self._registrar('40.00')
        self.orden.refresh_from_db()
        self.stock_mp.refresh_from_db()
        self.assertEqual(self.orden.estado, 'pendiente')
        self.assertFalse(LoteProduccion.objects.filter(orden_produccion=self.orden).exists())
        self.assertEqual(self.stock_mp.cantidad, Decimal('1000.00'))
        self.assertFalse(StockBodega.objects.filter(lote__orden_produccion=self.orden).exists())
