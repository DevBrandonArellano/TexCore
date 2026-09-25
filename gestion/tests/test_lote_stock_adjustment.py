"""
Pruebas de gestion/services/lote_stock_adjustment.LoteStockAdjustmentService: corrección del peso
de un lote (ajuste de salida, materia prima y químicos + estado de la OP) y reversión por rechazo.

Técnicas ISTQB:
- Partición de equivalencia (EP): peso sin cambio / aumenta / disminuye; con y sin fórmula.
- Análisis de valores límite (BVA): stock que quedaría exactamente en 0 frente a negativo.
- Transición de estados (STT): OP finalizada <-> en_proceso según lo producido; OP sin peso
  requerido (producción continua) no cambia de estado.
- Caja blanca, cobertura de decisiones (CB-D): stock de salida inexistente (se omite con log),
  stock del lote inexistente o en cero al rechazar.
"""
from decimal import Decimal

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from gestion.models import OrdenProduccion
from gestion.services.lote_stock_adjustment import LoteStockAdjustmentService
from gestion.tests.factories import (
    BodegaFactory, CustomUserFactory, DetalleFormulaFactory, FaseRecetaFactory, FormulaColorFactory,
    LoteProduccionFactory, OrdenProduccionFactory, ProductoFactory, SedeFactory,
)
from inventory.models import MovimientoInventario, StockBodega


class LoteStockAdjustmentTestCase(TestCase):

    def setUp(self):
        self.sede = SedeFactory()
        self.usuario = CustomUserFactory(sede=self.sede)
        self.bodega_mp = BodegaFactory(sede=self.sede)
        self.bodega_pt = BodegaFactory(sede=self.sede)
        self.hilo_crudo = ProductoFactory(sede=self.sede)
        self.hilo_tenido = ProductoFactory(sede=self.sede)
        self.orden = OrdenProduccionFactory(
            sede=self.sede, bodega_entrada=self.bodega_mp, bodega_salida=self.bodega_pt,
            producto_entrada=self.hilo_crudo, producto_salida=self.hilo_tenido,
            peso_neto_requerido=Decimal('100.00'))
        self.lote = LoteProduccionFactory(orden_produccion=self.orden, peso_neto_producido=Decimal('90.000'))
        self.stock_pt = self._stock(self.bodega_pt, self.hilo_tenido, '90', lote=self.lote)
        self.stock_mp = self._stock(self.bodega_mp, self.hilo_crudo, '50')

    def _stock(self, bodega, producto, cantidad, lote=None):
        stock = StockBodega(bodega=bodega, producto=producto, lote=lote, cantidad=Decimal(cantidad))
        stock.save()
        return stock

    def _estado(self, estado):
        # Sin fórmula no hay versión que congelar: basta un update directo del estado
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(estado=estado)
        self.orden.refresh_from_db()

    def _ajustar(self, viejo, nuevo):
        self.lote.peso_neto_producido = Decimal(nuevo)
        self.lote.save()
        LoteStockAdjustmentService.ajustar_por_cambio_peso(self.lote, Decimal(viejo), Decimal(nuevo), self.usuario)
        for obj in (self.stock_pt, self.stock_mp, self.orden):
            obj.refresh_from_db()

    def _con_formula(self, gramos_por_kilo='20', stock_quimico='10'):
        formula = FormulaColorFactory(sede=self.sede)
        quimico = ProductoFactory(sede=self.sede, tipo='quimico')
        DetalleFormulaFactory(fase=FaseRecetaFactory(formula=formula), producto=quimico,
                              gramos_por_kilo=Decimal(gramos_por_kilo))
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(formula_color=formula)
        self.orden.refresh_from_db()
        self.lote.refresh_from_db()
        return self._stock(self.bodega_mp, quimico, stock_quimico)

    # --- ajustar_por_cambio_peso ---
    def test_ajuste_dado_mismo_peso_cuando_ajusta_entonces_no_mueve_stock(self):
        self._ajustar('90', '90')
        self.assertEqual((self.stock_pt.cantidad, self.stock_mp.cantidad), (Decimal('90'), Decimal('50')))
        self.assertFalse(MovimientoInventario.objects.exists())

    def test_ajuste_dado_aumento_de_peso_cuando_ajusta_entonces_suma_salida_y_consume_materia_prima(self):
        self._ajustar('90', '95')
        self.assertEqual((self.stock_pt.cantidad, self.stock_mp.cantidad), (Decimal('95'), Decimal('45')))
        refs = set(MovimientoInventario.objects.values_list('documento_ref', flat=True))
        self.assertEqual(refs, {f'CORRECCION-LOTE-{self.lote.codigo_lote}'})
        self.assertEqual(MovimientoInventario.objects.count(), 2)

    def test_ajuste_dado_disminucion_de_peso_cuando_ajusta_entonces_devuelve_materia_prima(self):
        self._ajustar('90', '80')
        self.assertEqual((self.stock_pt.cantidad, self.stock_mp.cantidad), (Decimal('80'), Decimal('60')))

    def test_ajuste_dado_salida_que_quedaria_negativa_cuando_ajusta_entonces_error(self):
        StockBodega.objects.filter(pk=self.stock_pt.pk).update(cantidad=Decimal('5'))
        with self.assertRaises(ValidationError):
            self._ajustar('90', '80')

    def test_ajuste_dado_materia_prima_justa_cuando_ajusta_entonces_queda_en_cero(self):
        # BVA: consumir exactamente el stock disponible es válido
        self._ajustar('90', '140')
        self.assertEqual(self.stock_mp.cantidad, Decimal('0'))

    def test_ajuste_dado_materia_prima_insuficiente_cuando_ajusta_entonces_error(self):
        with self.assertRaises(ValidationError):
            self._ajustar('90', '140.01')

    def test_ajuste_dado_sin_stock_de_salida_cuando_ajusta_entonces_omite_la_salida_y_ajusta_la_entrada(self):
        StockBodega.objects.filter(pk=self.stock_pt.pk).delete()
        with self.assertLogs('gestion.services.lote_stock_adjustment', level='WARNING'):
            LoteStockAdjustmentService.ajustar_por_cambio_peso(
                self.lote, Decimal('90'), Decimal('95'), self.usuario)
        self.stock_mp.refresh_from_db()
        self.assertEqual(self.stock_mp.cantidad, Decimal('45'))

    def test_ajuste_dado_formula_cuando_aumenta_peso_entonces_descuenta_quimicos(self):
        stock_quimico = self._con_formula(gramos_por_kilo='20', stock_quimico='10')
        self._ajustar('90', '100')  # 10 kg más x 20 g/kg = 0.2 kg
        stock_quimico.refresh_from_db()
        self.assertEqual(stock_quimico.cantidad, Decimal('9.8'))

    def test_ajuste_dado_quimico_insuficiente_cuando_ajusta_entonces_error(self):
        self._con_formula(gramos_por_kilo='20', stock_quimico='0.1')
        with self.assertRaises(ValidationError):
            self._ajustar('90', '100')

    def test_ajuste_dado_orden_finalizada_que_queda_corta_cuando_ajusta_entonces_vuelve_a_en_proceso(self):
        self._estado('finalizada')
        self._ajustar('90', '80')
        self.assertEqual(self.orden.estado, 'en_proceso')

    def test_ajuste_dado_orden_en_proceso_que_completa_cuando_ajusta_entonces_finaliza(self):
        self._estado('en_proceso')
        self._ajustar('90', '100')
        self.assertEqual(self.orden.estado, 'finalizada')
        self.assertIsNotNone(self.orden.fecha_fin_planificada)

    def test_ajuste_dado_orden_sin_peso_requerido_cuando_ajusta_entonces_no_cambia_de_estado(self):
        # Producción continua: peso_neto_requerido es opcional (antes: TypeError al comparar con None)
        OrdenProduccion.objects.filter(pk=self.orden.pk).update(peso_neto_requerido=None, estado='en_proceso')
        self.orden.refresh_from_db()
        self.lote.refresh_from_db()
        self._ajustar('90', '95')
        self.assertEqual(self.orden.estado, 'en_proceso')

    # --- revertir_por_rechazo ---
    def test_rechazo_dado_stock_del_lote_cuando_revierte_entonces_devuelve_materia_prima_y_quimicos(self):
        stock_quimico = self._con_formula(gramos_por_kilo='20', stock_quimico='10')
        revertido = LoteStockAdjustmentService.revertir_por_rechazo(self.lote, self.usuario)
        for obj in (self.stock_pt, self.stock_mp, stock_quimico):
            obj.refresh_from_db()
        self.assertEqual(revertido, Decimal('90'))
        self.assertEqual((self.stock_pt.cantidad, self.stock_mp.cantidad), (Decimal('0'), Decimal('140')))
        self.assertEqual(stock_quimico.cantidad, Decimal('11.8'))  # 90 kg x 20 g/kg = 1.8 kg

    def test_rechazo_dado_stock_del_lote_inexistente_cuando_revierte_entonces_error(self):
        StockBodega.objects.filter(pk=self.stock_pt.pk).delete()
        with self.assertRaises(ValidationError):
            LoteStockAdjustmentService.revertir_por_rechazo(self.lote, self.usuario)

    def test_rechazo_dado_stock_del_lote_en_cero_cuando_revierte_entonces_error(self):
        StockBodega.objects.filter(pk=self.stock_pt.pk).update(cantidad=Decimal('0'))
        with self.assertRaises(ValidationError):
            LoteStockAdjustmentService.revertir_por_rechazo(self.lote, self.usuario)
