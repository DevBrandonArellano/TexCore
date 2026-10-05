from datetime import UTC, datetime
from decimal import Decimal

from django.test import TestCase

from gestion.tests.factories import (
    CustomUserFactory,
    MaquinaConMermaFactory,
    OrdenProduccionFactory,
    StockBodegaFactory,
)
from inventory.models import StockBodega


class RegistroLoteTransformacionTest(TestCase):
    """TDD — RegistroLoteService con producto_entrada != producto_salida."""

    def setUp(self):
        self.user = CustomUserFactory()
        self.op = OrdenProduccionFactory(peso_neto_requerido=Decimal('100.00'))
        StockBodegaFactory(
            bodega=self.op.bodega_entrada,
            producto=self.op.producto_entrada,
            lote=None,
            cantidad=Decimal('200.00'),
        )

    def _lote_data_base(self, **kwargs):
        """Datos mínimos válidos para registrar un lote."""
        defaults = {
            'peso_neto_producido': Decimal('90.000'),
            'peso_merma': Decimal('10.000'),
            'tipo_merma': 'maquina',
            'unidades_empaque': 1,
            'presentacion': 'cono',
            'turno': 'Dia',
            'hora_inicio': datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
            'hora_final': datetime(2026, 1, 1, 16, 0, tzinfo=UTC),
        }
        defaults.update(kwargs)
        return defaults

    # EP: OP simple sin mezcla — consume producto_entrada, produce producto_salida
    def test_registro_lote_dado_op_simple_cuando_registra_entonces_transforma_entrada_en_salida(self):
        from gestion.services.registro_lote import RegistroLoteService
        lote = RegistroLoteService.registrar_lote(self.op, self._lote_data_base(), self.user)

        stock_entrada = StockBodega.objects.get(
            bodega=self.op.bodega_entrada,
            producto=self.op.producto_entrada,
            lote=None,
        )
        # 200 - (90 neto + 10 merma) = 100
        self.assertEqual(stock_entrada.cantidad, Decimal('100.00'))

        stock_salida = StockBodega.objects.get(
            bodega=self.op.bodega_salida,
            producto=self.op.producto_salida,
            lote=lote,
        )
        self.assertEqual(stock_salida.cantidad, Decimal('90.00'))

    # EP: merma vendible — MermaStockService crea stock
    def test_registro_lote_dado_maquina_con_merma_cuando_registra_entonces_crea_stock_de_merma(self):
        from gestion.services.registro_lote import RegistroLoteService
        maquina = MaquinaConMermaFactory()
        lote = RegistroLoteService.registrar_lote(
            self.op,
            self._lote_data_base(maquina=maquina.id),
            self.user,
        )
        self.assertTrue(
            StockBodega.objects.filter(
                bodega=maquina.bodega_merma,
                producto=maquina.producto_merma,
                lote=lote,
            ).exists()
        )

    # STT: pendiente → en_proceso → finalizada
    def test_registro_lote_dado_op_pendiente_cuando_registra_lotes_entonces_avanza_su_estado(self):
        from gestion.services.registro_lote import RegistroLoteService
        self.assertEqual(self.op.estado, 'pendiente')

        RegistroLoteService.registrar_lote(
            self.op,
            self._lote_data_base(
                peso_neto_producido=Decimal('90.000'),
                peso_merma=Decimal('0.000'),
            ),
            self.user,
        )
        self.op.refresh_from_db()
        self.assertEqual(self.op.estado, 'en_proceso')

        # Segundo lote — completa la OP (90 + 10 >= 100)
        # El stock ya existe (created in setUp); solo actualizar la cantidad.
        from inventory.models import StockBodega
        StockBodega.objects.filter(
            bodega=self.op.bodega_entrada,
            producto=self.op.producto_entrada,
            lote=None,
        ).update(cantidad=Decimal('20.00'))
        RegistroLoteService.registrar_lote(
            self.op,
            self._lote_data_base(
                peso_neto_producido=Decimal('10.000'),
                peso_merma=Decimal('0.000'),
                turno='Noche',
            ),
            self.user,
        )
        self.op.refresh_from_db()
        self.assertEqual(self.op.estado, 'finalizada')
