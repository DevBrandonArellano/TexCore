from decimal import Decimal
from django.test import TestCase
from inventory.models import StockBodega, MovimientoInventario
from gestion.tests.factories import (
    MaquinaConMermaFactory, MaquinaFactory,
    LoteProduccionFactory, CustomUserFactory,
)


class MermaStockServiceRegistrarTest(TestCase):
    """TDD — MermaStockService.registrar(). ISO 27001 A.12.4 + COBIT MEA01."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.maquina = MaquinaConMermaFactory()
        self.lote = LoteProduccionFactory(
            maquina=self.maquina,
            peso_merma=Decimal('5.000'),
            tipo_merma='maquina',
        )

    # EP: máquina con merma configurada y peso_merma > 0 → crea StockBodega
    def test_dado_maquina_con_merma_cuando_registrar_entonces_crea_stock(self):
        from gestion.services.merma_stock import MermaStockService
        MermaStockService.registrar(self.lote, self.user)
        self.assertTrue(
            StockBodega.objects.filter(
                bodega=self.maquina.bodega_merma,
                producto=self.maquina.producto_merma,
                lote=self.lote,
            ).exists()
        )
        stock = StockBodega.objects.get(
            bodega=self.maquina.bodega_merma,
            producto=self.maquina.producto_merma,
            lote=self.lote,
        )
        self.assertEqual(stock.cantidad, Decimal('5.00'))

    # EP: máquina sin merma → no hace nada
    def test_dado_maquina_sin_merma_cuando_registrar_entonces_no_crea_stock(self):
        from gestion.services.merma_stock import MermaStockService
        maquina_simple = MaquinaFactory()
        lote = LoteProduccionFactory(maquina=maquina_simple, peso_merma=Decimal('3.000'))
        MermaStockService.registrar(lote, self.user)
        self.assertEqual(
            MovimientoInventario.objects.filter(
                documento_ref__startswith='MERMA-'
            ).count(),
            0,
        )

    # BVA: peso_merma = 0 → no crea stock
    def test_dado_peso_merma_cero_no_crea_stock(self):
        from gestion.services.merma_stock import MermaStockService
        lote = LoteProduccionFactory(maquina=self.maquina, peso_merma=Decimal('0.000'))
        MermaStockService.registrar(lote, self.user)
        self.assertFalse(
            StockBodega.objects.filter(bodega=self.maquina.bodega_merma).exists()
        )

    # BVA: peso_merma = 0.01 → crea stock
    def test_dado_peso_merma_minimo_crea_stock(self):
        from gestion.services.merma_stock import MermaStockService
        lote = LoteProduccionFactory(maquina=self.maquina, peso_merma=Decimal('0.010'))
        MermaStockService.registrar(lote, self.user)
        self.assertTrue(
            StockBodega.objects.filter(
                bodega=self.maquina.bodega_merma,
                producto=self.maquina.producto_merma,
            ).exists()
        )

    # ISO 27001 A.12.4: crea MovimientoInventario con tipo PRODUCCION y ref MERMA-
    def test_cuando_registrar_crea_movimiento_kardex(self):
        from gestion.services.merma_stock import MermaStockService
        MermaStockService.registrar(self.lote, self.user)
        mov = MovimientoInventario.objects.get(
            documento_ref=f'MERMA-{self.lote.codigo_lote}'
        )
        self.assertEqual(mov.tipo_movimiento, 'PRODUCCION')
        self.assertEqual(mov.cantidad, Decimal('5.00'))
        self.assertEqual(mov.usuario, self.user)
        self.assertEqual(mov.bodega_destino, self.maquina.bodega_merma)


class MermaStockServiceRevertirTest(TestCase):
    """STT: merma registrada → lote rechazado → stock revertido."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.maquina = MaquinaConMermaFactory()
        self.lote = LoteProduccionFactory(
            maquina=self.maquina,
            peso_merma=Decimal('5.000'),
            tipo_merma='maquina',
        )
        from gestion.services.merma_stock import MermaStockService
        MermaStockService.registrar(self.lote, self.user)

    def test_cuando_revertir_stock_decrece(self):
        from gestion.services.merma_stock import MermaStockService
        stock_antes = StockBodega.objects.get(
            bodega=self.maquina.bodega_merma,
            producto=self.maquina.producto_merma,
            lote=self.lote,
        ).cantidad

        MermaStockService.revertir(self.lote, self.user, 'Test reversión')

        stock_despues = StockBodega.objects.get(
            bodega=self.maquina.bodega_merma,
            producto=self.maquina.producto_merma,
            lote=self.lote,
        ).cantidad
        self.assertEqual(stock_despues, stock_antes - Decimal('5.00'))

    def test_cuando_revertir_crea_movimiento_devolucion(self):
        from gestion.services.merma_stock import MermaStockService
        MermaStockService.revertir(self.lote, self.user, 'Test reversión')
        self.assertTrue(
            MovimientoInventario.objects.filter(
                tipo_movimiento='DEVOLUCION',
                documento_ref=f'REV-MERMA-{self.lote.codigo_lote}',
            ).exists()
        )
