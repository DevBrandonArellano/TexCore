"""
Tests P0-006: La descarga de químicos NO debe dejar stock negativo.
Artefacto RUP: Suite de Pruebas
Caso de Uso: CU-DescargaQuimicaAutomatica

Diagnóstico CONTEXTO.md (10-Jun-2026):
descarga_quimicos.py descuenta stock sin validar disponibilidad
(stock.cantidad -= cantidad) — el stock puede quedar negativo, rompiendo
Kardex, MRP y despachos.

Técnicas ISTQB: EP (stock suficiente/insuficiente), BVA (stock == requerido,
stock = requerido - 0.01), STT (rollback parcial multi-químico).

Cálculo de dosificación (igual que test_descarga_quimicos_tdd):
peso_neto_requerido kg × relación baño 10 = litros; litros × gr/L / 1000 = kg químico.
OP de 100 kg con 10 gr/L → requiere 10 kg de químico.
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase

from gestion.tests.factories import (
    CustomUserFactory, SedeFactory, ProductoFactory,
    FormulaColorFactory, BodegaFactory, AreaFactory,
    FaseRecetaFactory, DetalleFormulaFactory,
)
from gestion.models import OrdenProduccion, DescargaQuimicoOP
from gestion.services.descarga_quimicos import DescargaQuimicosService
from inventory.models import StockBodega


class DescargaQuimicosStockInsuficienteTestCase(APITestCase):
    """La descarga debe validar disponibilidad ANTES de descontar."""

    def setUp(self):
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.user = CustomUserFactory(sede=self.sede, groups=['admin_sistemas'])

        self.producto_tela = ProductoFactory(tipo='tela', sede=self.sede)
        self.quimico = ProductoFactory(
            tipo='quimico', sede=self.sede, descripcion='Soda Cáustica P0'
        )
        self.bodega = BodegaFactory(sede=self.sede, nombre='Bodega Químicos P0')

        self.formula = FormulaColorFactory(
            nombre_color='Azul P0', sede=self.sede, estado='aprobada'
        )
        self.fase = FaseRecetaFactory(formula=self.formula, nombre='tintura')
        DetalleFormulaFactory(
            fase=self.fase,
            producto=self.quimico,
            concentracion_gr_l=Decimal('10.00'),  # OP 100kg → requiere 10 kg
            tipo_calculo='gr_l',
        )

    def _set_stock(self, producto, cantidad):
        stock, _ = StockBodega.objects.get_or_create(
            bodega=self.bodega, producto=producto, lote=None,
            defaults={'cantidad': Decimal('0.00')},
        )
        stock.cantidad = Decimal(str(cantidad))
        stock._justificacion_auditoria = 'Stock inicial para test P0-006'
        stock.save()
        return stock

    def _crear_orden(self, codigo='OP-P006', peso='100.00'):
        return OrdenProduccion.objects.create(
            codigo=codigo,
            formula_color=self.formula,
            bodega_quimicos=self.bodega,
            peso_neto_requerido=Decimal(peso),
            sede=self.sede,
            area=self.area,
        )

    def test_stock_insuficiente_lanza_validation_error(self):
        """EP insuficiente: stock 5 kg, requiere 10 kg → ValidationError."""
        self._set_stock(self.quimico, '5.00')
        orden = self._crear_orden()

        with self.assertRaises(ValidationError) as ctx:
            DescargaQuimicosService.descargar_para_op(orden, self.user)

        self.assertIn('insuficiente', str(ctx.exception).lower())

    def test_stock_insuficiente_no_modifica_inventario(self):
        """EP insuficiente: tras el error, el stock queda intacto (nunca negativo)."""
        self._set_stock(self.quimico, '5.00')
        orden = self._crear_orden(codigo='OP-P006-B')

        with self.assertRaises(ValidationError):
            DescargaQuimicosService.descargar_para_op(orden, self.user)

        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico)
        self.assertEqual(stock.cantidad, Decimal('5.00'),
                         'El stock no debe modificarse si la descarga falla')
        self.assertGreaterEqual(stock.cantidad, Decimal('0.00'),
                                'El stock JAMÁS debe quedar negativo')
        self.assertFalse(
            DescargaQuimicoOP.objects.filter(orden_produccion=orden).exists(),
            'No deben quedar registros de descarga de una operación fallida',
        )
        orden.refresh_from_db()
        self.assertFalse(orden.inventario_descontado)

    def test_stock_exactamente_igual_al_requerido_descarga_ok(self):
        """BVA límite exacto: stock 10 kg, requiere 10 kg → éxito, stock final 0."""
        self._set_stock(self.quimico, '10.00')
        orden = self._crear_orden(codigo='OP-P006-C')

        registros = DescargaQuimicosService.descargar_para_op(orden, self.user)

        self.assertEqual(len(registros), 1)
        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico)
        self.assertEqual(stock.cantidad, Decimal('0.00'))
        orden.refresh_from_db()
        self.assertTrue(orden.inventario_descontado)

    def test_stock_apenas_insuficiente_es_rechazado(self):
        """BVA límite - 0.01: stock 9.99 kg, requiere 10 kg → ValidationError."""
        self._set_stock(self.quimico, '9.99')
        orden = self._crear_orden(codigo='OP-P006-D')

        with self.assertRaises(ValidationError):
            DescargaQuimicosService.descargar_para_op(orden, self.user)

        stock = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico)
        self.assertEqual(stock.cantidad, Decimal('9.99'))

    def test_fallo_en_segundo_quimico_revierte_el_primero(self):
        """
        STT rollback: fórmula con 2 químicos; el primero tiene stock de sobra,
        el segundo no alcanza → la transacción debe revertir TODO (el stock
        del primero vuelve a su valor original).
        """
        quimico_b = ProductoFactory(
            tipo='quimico', sede=self.sede, descripcion='Colorante P0'
        )
        DetalleFormulaFactory(
            fase=self.fase,
            producto=quimico_b,
            concentracion_gr_l=Decimal('10.00'),  # también requiere 10 kg
            tipo_calculo='gr_l',
        )
        self._set_stock(self.quimico, '100.00')  # suficiente
        self._set_stock(quimico_b, '5.00')       # insuficiente
        orden = self._crear_orden(codigo='OP-P006-E')

        with self.assertRaises(ValidationError):
            DescargaQuimicosService.descargar_para_op(orden, self.user)

        stock_a = StockBodega.objects.get(bodega=self.bodega, producto=self.quimico)
        stock_b = StockBodega.objects.get(bodega=self.bodega, producto=quimico_b)
        self.assertEqual(stock_a.cantidad, Decimal('100.00'),
                         'Rollback: el primer químico debe restaurarse')
        self.assertEqual(stock_b.cantidad, Decimal('5.00'))
        self.assertFalse(
            DescargaQuimicoOP.objects.filter(orden_produccion=orden).exists()
        )
