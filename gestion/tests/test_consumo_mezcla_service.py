from decimal import Decimal
from django.test import TestCase
from django.core.exceptions import ValidationError
from inventory.models import StockBodega, MovimientoInventario
from gestion.models import ConsumoLoteDetalle
from gestion.tests.factories import (
    OrdenProduccionFactory, ComponenteMezclaOPFactory,
    LoteProduccionFactory, CustomUserFactory, StockBodegaFactory,
)


class ConsumoMezclaServiceConsumir(TestCase):
    """TDD — ConsumoMezclaService. COBIT DSS06 + ISO 27001 A.12.4."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.op = OrdenProduccionFactory(peso_neto_requerido=Decimal('100.00'))

        self.comp1 = ComponenteMezclaOPFactory(
            orden=self.op,
            porcentaje=Decimal('50.00'),
            cantidad_kg=Decimal('50.000'),
        )
        self.comp2 = ComponenteMezclaOPFactory(
            orden=self.op,
            porcentaje=Decimal('50.00'),
            cantidad_kg=Decimal('50.000'),
        )

        self.lote_origen1 = LoteProduccionFactory(peso_neto_producido=Decimal('100.000'))
        self.lote_origen2 = LoteProduccionFactory(peso_neto_producido=Decimal('100.000'))

        # Stock disponible para cada lote de origen
        StockBodegaFactory(
            bodega=self.comp1.bodega,
            producto=self.comp1.producto,
            lote=self.lote_origen1,
            cantidad=Decimal('100.00'),
        )
        StockBodegaFactory(
            bodega=self.comp2.bodega,
            producto=self.comp2.producto,
            lote=self.lote_origen2,
            cantidad=Decimal('100.00'),
        )

        self.lote_output = LoteProduccionFactory(orden_produccion=self.op)

    def _consumos_validos(self):
        return [
            {
                'lote_origen_id': self.lote_origen1.id,
                'cantidad_kg': Decimal('50.000'),
                'genera_nuevo_lote': True,
                'bodega_id': self.comp1.bodega.id,
                'producto_id': self.comp1.producto.id,
            },
            {
                'lote_origen_id': self.lote_origen2.id,
                'cantidad_kg': Decimal('50.000'),
                'genera_nuevo_lote': True,
                'bodega_id': self.comp2.bodega.id,
                'producto_id': self.comp2.producto.id,
            },
        ]

    # EP: mezcla válida 2 componentes
    def test_mezcla_valida_descuenta_ambos_stocks(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        ConsumoMezclaService.consumir(
            self.op, self.lote_output, self._consumos_validos(), self.user
        )
        stock1 = StockBodega.objects.get(
            bodega=self.comp1.bodega, producto=self.comp1.producto, lote=self.lote_origen1
        )
        stock2 = StockBodega.objects.get(
            bodega=self.comp2.bodega, producto=self.comp2.producto, lote=self.lote_origen2
        )
        self.assertEqual(stock1.cantidad, Decimal('50.00'))
        self.assertEqual(stock2.cantidad, Decimal('50.00'))

    # EP: crea ConsumoLoteDetalle por cada componente
    def test_mezcla_crea_consumo_lote_detalle(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        ConsumoMezclaService.consumir(
            self.op, self.lote_output, self._consumos_validos(), self.user
        )
        self.assertEqual(
            ConsumoLoteDetalle.objects.filter(lote_produccion=self.lote_output).count(), 2
        )

    # BVA: suma cantidades != consumo_total → ValidationError (COBIT DSS06)
    def test_suma_incorrecta_lanza_error(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        consumos = [
            {**self._consumos_validos()[0], 'cantidad_kg': Decimal('40.000')},
            {**self._consumos_validos()[1], 'cantidad_kg': Decimal('40.000')},
        ]
        with self.assertRaises(ValidationError):
            ConsumoMezclaService.consumir(
                self.op, self.lote_output, consumos, self.user,
                consumo_total=Decimal('100.000'),
            )

    # EP: stock insuficiente → ValidationError + rollback
    def test_stock_insuficiente_hace_rollback(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        consumos = [{
            'lote_origen_id': self.lote_origen1.id,
            'cantidad_kg': Decimal('200.000'),
            'genera_nuevo_lote': True,
            'bodega_id': self.comp1.bodega.id,
            'producto_id': self.comp1.producto.id,
        }]
        with self.assertRaises(ValidationError):
            ConsumoMezclaService.consumir(self.op, self.lote_output, consumos, self.user)

        stock = StockBodega.objects.get(
            bodega=self.comp1.bodega, producto=self.comp1.producto, lote=self.lote_origen1
        )
        self.assertEqual(stock.cantidad, Decimal('100.00'))

    # ISO 27001 A.12.4: crea MovimientoInventario por cada componente
    def test_mezcla_crea_movimientos_kardex(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        ConsumoMezclaService.consumir(
            self.op, self.lote_output, self._consumos_validos(), self.user
        )
        movs = MovimientoInventario.objects.filter(
            tipo_movimiento='CONSUMO',
            documento_ref=f'OP-{self.op.codigo}',
        )
        self.assertEqual(movs.count(), 2)


class ConsumoMezclaServiceRevertir(TestCase):
    """STT: mezcla consumida → revertir → stock restaurado."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.op = OrdenProduccionFactory(peso_neto_requerido=Decimal('100.00'))
        self.comp = ComponenteMezclaOPFactory(
            orden=self.op, porcentaje=Decimal('100.00'), cantidad_kg=Decimal('100.000')
        )
        self.lote_origen = LoteProduccionFactory()
        StockBodegaFactory(
            bodega=self.comp.bodega, producto=self.comp.producto,
            lote=self.lote_origen, cantidad=Decimal('100.00')
        )
        self.lote_output = LoteProduccionFactory(orden_produccion=self.op)
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        ConsumoMezclaService.consumir(self.op, self.lote_output, [{
            'lote_origen_id': self.lote_origen.id,
            'cantidad_kg': Decimal('100.000'),
            'genera_nuevo_lote': True,
            'bodega_id': self.comp.bodega.id,
            'producto_id': self.comp.producto.id,
        }], self.user)

    def test_revertir_restaura_stock(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        ConsumoMezclaService.revertir(self.lote_output, self.user, 'Test')
        stock = StockBodega.objects.get(
            bodega=self.comp.bodega, producto=self.comp.producto, lote=self.lote_origen
        )
        self.assertEqual(stock.cantidad, Decimal('100.00'))

    def test_revertir_elimina_consumo_detalle(self):
        from gestion.services.consumo_mezcla import ConsumoMezclaService
        ConsumoMezclaService.revertir(self.lote_output, self.user, 'Test')
        self.assertFalse(
            ConsumoLoteDetalle.objects.filter(lote_produccion=self.lote_output).exists()
        )
