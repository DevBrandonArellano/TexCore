"""
Pruebas de MovimientoReversionService — revierte el efecto de stock de un
MovimientoInventario individual (a diferencia de DespachoReversionService,
que revierte un despacho completo con sus múltiples detalles).

Mismo patrón que DespachoReversionService: @transaction.atomic, justificación
obligatoria, crea un movimiento compensatorio (no borra el histórico a ciegas),
fail-loud si el stock ya fue consumido/es inconsistente.

Técnicas ISTQB:
- EP: reversión de entrada (COMPRA/PRODUCCION/DEVOLUCION/AJUSTE) vs. salida
  (VENTA/CONSUMO/MERMA) vs. TRANSFERENCIA (ambas bodegas).
- Caja blanca: guarda de movimientos ligados a un despacho (deben revertirse
  vía DespachoReversionService, no aquí).
- BVA: revertir una entrada cuyo stock actual ya es menor a la cantidad
  original (ya se consumió) -> ValueError, no deja stock negativo.
"""
from decimal import Decimal

from django.test import TestCase

from inventory.models import MovimientoInventario, StockBodega, DetalleHistorialDespacho, HistorialDespacho
from inventory.services.movimiento_reversion import MovimientoReversionService
from gestion.tests.factories import (
    SedeFactory, BodegaFactory, ProductoFactory, CustomUserFactory, StockBodegaFactory,
)


class MovimientoReversionServiceTestCase(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.bodega_a = BodegaFactory(sede=self.sede)
        self.bodega_b = BodegaFactory(sede=self.sede)
        self.producto = ProductoFactory(sede=self.sede)
        self.usuario = CustomUserFactory(sede=self.sede, groups=['bodeguero'])

    def test_revertir_entrada_compra_resta_stock_y_crea_compensatorio(self):
        StockBodegaFactory(bodega=self.bodega_a, producto=self.producto, lote=None, cantidad=Decimal('50.00'))
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto, cantidad=Decimal('50.00'),
            bodega_destino=self.bodega_a, usuario=self.usuario, saldo_resultante=Decimal('50.00'),
        )

        MovimientoReversionService.revertir(movimiento, self.usuario, 'Compra registrada por error')

        stock = StockBodega.objects.get(bodega=self.bodega_a, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('0.00'))
        compensatorio = MovimientoInventario.objects.exclude(id=movimiento.id).get()
        self.assertEqual(compensatorio.documento_ref, f"REVERT-Mov-#{movimiento.id}")

    def test_revertir_salida_merma_devuelve_stock_a_origen(self):
        StockBodegaFactory(bodega=self.bodega_a, producto=self.producto, lote=None, cantidad=Decimal('70.00'))
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='MERMA', producto=self.producto, cantidad=Decimal('30.00'),
            bodega_origen=self.bodega_a, usuario=self.usuario, saldo_resultante=Decimal('70.00'),
        )

        MovimientoReversionService.revertir(movimiento, self.usuario, 'Merma registrada por error')

        stock = StockBodega.objects.get(bodega=self.bodega_a, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('100.00'))

    def test_revertir_salida_venta_devuelve_stock_a_origen(self):
        StockBodegaFactory(bodega=self.bodega_a, producto=self.producto, lote=None, cantidad=Decimal('20.00'))
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='VENTA', producto=self.producto, cantidad=Decimal('10.00'),
            bodega_origen=self.bodega_a, usuario=self.usuario, saldo_resultante=Decimal('20.00'),
        )

        MovimientoReversionService.revertir(movimiento, self.usuario, 'Venta cancelada')

        stock = StockBodega.objects.get(bodega=self.bodega_a, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('30.00'))

    def test_revertir_transferencia_revierte_ambas_bodegas(self):
        StockBodegaFactory(bodega=self.bodega_a, producto=self.producto, lote=None, cantidad=Decimal('0.00'))
        StockBodegaFactory(bodega=self.bodega_b, producto=self.producto, lote=None, cantidad=Decimal('40.00'))
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='TRANSFERENCIA', producto=self.producto, cantidad=Decimal('40.00'),
            bodega_origen=self.bodega_a, bodega_destino=self.bodega_b,
            usuario=self.usuario, saldo_resultante=Decimal('40.00'),
        )

        MovimientoReversionService.revertir(movimiento, self.usuario, 'Transferencia equivocada de bodega')

        stock_a = StockBodega.objects.get(bodega=self.bodega_a, producto=self.producto, lote=None)
        stock_b = StockBodega.objects.get(bodega=self.bodega_b, producto=self.producto, lote=None)
        self.assertEqual(stock_a.cantidad, Decimal('40.00'))
        self.assertEqual(stock_b.cantidad, Decimal('0.00'))

    def test_revertir_sin_justificacion_valueerror(self):
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='MERMA', producto=self.producto, cantidad=Decimal('5.00'),
            bodega_origen=self.bodega_a, usuario=self.usuario, saldo_resultante=Decimal('0.00'),
        )
        with self.assertRaises(ValueError):
            MovimientoReversionService.revertir(movimiento, self.usuario, '   ')

    def test_revertir_entrada_ya_consumida_cuando_stock_insuficiente_entonces_valueerror(self):
        # BVA: el stock actual (5) es menor a la cantidad original de la entrada (50)
        # porque ya se consumió parte -> no se puede revertir sin dejar stock negativo.
        StockBodegaFactory(bodega=self.bodega_a, producto=self.producto, lote=None, cantidad=Decimal('5.00'))
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='COMPRA', producto=self.producto, cantidad=Decimal('50.00'),
            bodega_destino=self.bodega_a, usuario=self.usuario, saldo_resultante=Decimal('50.00'),
        )
        with self.assertRaises(ValueError):
            MovimientoReversionService.revertir(movimiento, self.usuario, 'Intento de reversión')
        # No debe haber modificado el stock existente (atomicidad)
        stock = StockBodega.objects.get(bodega=self.bodega_a, producto=self.producto, lote=None)
        self.assertEqual(stock.cantidad, Decimal('5.00'))

    def test_revertir_movimiento_ligado_a_despacho_entonces_valueerror(self):
        # Guarda: un movimiento VENTA que originó un despacho tiene su propio
        # flujo de reversión (DespachoReversionService) — no debe revertirse aquí.
        StockBodegaFactory(bodega=self.bodega_a, producto=self.producto, lote=None, cantidad=Decimal('0.00'))
        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='VENTA', producto=self.producto, cantidad=Decimal('10.00'),
            bodega_origen=self.bodega_a, usuario=self.usuario, saldo_resultante=Decimal('0.00'),
        )
        historial = HistorialDespacho.objects.create(
            usuario=self.usuario, total_bultos=1, total_peso=Decimal('10.00'))
        DetalleHistorialDespacho.objects.create(
            historial=historial, producto=self.producto, peso=Decimal('10.00'),
            movimiento_venta=movimiento,
        )
        with self.assertRaises(ValueError):
            MovimientoReversionService.revertir(movimiento, self.usuario, 'Intento no permitido')
