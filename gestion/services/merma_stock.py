import logging
from decimal import Decimal
from django.db import transaction
from inventory.models import MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger(__name__)


class MermaStockService:
    """
    SRP: gestiona el stock de merma vendible por máquina.
    ISO 27001 A.12.4: cada operación crea MovimientoInventario trazable.
    COBIT MEA01: documento_ref 'MERMA-{codigo}' para KPIs de eficiencia.
    """

    @staticmethod
    @transaction.atomic
    def registrar(lote, user) -> None:
        """
        Si la máquina del lote tiene producto_merma configurado y
        peso_merma > 0, crea stock vendible en bodega_merma.
        """
        maquina = lote.maquina
        if not maquina or not maquina.producto_merma_id or not maquina.bodega_merma_id:
            return

        peso_merma = lote.peso_merma.quantize(Decimal('0.01'))
        if peso_merma <= 0:
            return

        stock, _ = safe_get_or_create_stock(
            StockBodega, maquina.bodega_merma, maquina.producto_merma, lote=lote
        )
        stock = StockBodega.objects.select_for_update().get(id=stock.id)
        stock.cantidad += peso_merma
        stock._justificacion_auditoria = f'Merma vendible de lote {lote.codigo_lote}'
        stock.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='PRODUCCION',
            producto=maquina.producto_merma,
            lote=lote,
            bodega_destino=maquina.bodega_merma,
            cantidad=peso_merma,
            documento_ref=f'MERMA-{lote.codigo_lote}',
            usuario=user,
            saldo_resultante=stock.cantidad,
        )

        logger.info(
            'Merma vendible registrada',
            extra={'sd': {
                'lote': lote.codigo_lote,
                'producto_merma': maquina.producto_merma.codigo,
                'cantidad_kg': str(peso_merma),
                'bodega': maquina.bodega_merma.nombre,
            }},
        )

    @staticmethod
    @transaction.atomic
    def revertir(lote, user, justificacion: str) -> None:
        """Revierte el stock de merma creado por este lote."""
        maquina = lote.maquina
        if not maquina or not maquina.producto_merma_id:
            return

        peso_merma = lote.peso_merma.quantize(Decimal('0.01'))
        if peso_merma <= 0:
            return

        try:
            stock = StockBodega.objects.select_for_update().get(
                bodega=maquina.bodega_merma,
                producto=maquina.producto_merma,
                lote=lote,
            )
        except StockBodega.DoesNotExist:
            return

        stock.cantidad -= peso_merma
        stock._justificacion_auditoria = justificacion
        stock.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='DEVOLUCION',
            producto=maquina.producto_merma,
            lote=lote,
            bodega_origen=maquina.bodega_merma,
            cantidad=peso_merma,
            documento_ref=f'REV-MERMA-{lote.codigo_lote}',
            usuario=user,
            saldo_resultante=stock.cantidad,
            observaciones=justificacion,
        )
