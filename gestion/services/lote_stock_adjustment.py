import logging
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from inventory.models import MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger(__name__)


class LoteStockAdjustmentService:
    """
    SRP (barrido de higiene Fase 5.2): extraído de LoteProduccionViewSet —
    la vista solo hace parseo HTTP, este service hace el ajuste/reversión de
    stock (mismo patrón ya usado en kpi_views.py).
    """

    @staticmethod
    @transaction.atomic
    def ajustar_por_cambio_peso(updated_lote, old_peso_neto, new_peso_neto, user):
        """
        Ajusta stock de salida/entrada/químicos cuando el peso neto de un lote
        cambia, y recalcula el estado de la OP. Reutilizado por perform_update
        (PATCH directo) y por reetiquetar/ (F4).
        """
        if old_peso_neto == new_peso_neto:
            return

        diff = new_peso_neto - old_peso_neto
        orden = updated_lote.orden_produccion
        # Fase 14: el flujo de transformación separa entrada/salida. La salida
        # va a bodega_salida (producto_salida) y la materia prima/químicos se
        # consumen de bodega_entrada (producto_entrada). Fallbacks por compat.
        bodega_salida = orden.bodega_salida or orden.bodega_entrada
        bodega_entrada = orden.bodega_entrada or orden.bodega_salida
        producto_salida = orden.producto_salida or orden.producto_entrada
        producto_entrada = orden.producto_entrada or orden.producto_salida

        # 1. Adjust Output Stock
        try:
            stock_output = StockBodega.objects.select_for_update().get(
                bodega=bodega_salida, producto=producto_salida, lote=updated_lote
            )
            if stock_output.cantidad + diff < 0:
                raise ValidationError(
                    {"peso_neto_producido": "El cambio resultaría en stock negativo de producto terminado."})

            stock_output.cantidad = (stock_output.cantidad + diff).quantize(Decimal('0.01'))
            stock_output._justificacion_auditoria = f"Correccion de lote {updated_lote.codigo_lote}"
            stock_output.save()

            MovimientoInventario.objects.create(
                tipo_movimiento='AJUSTE',
                producto=producto_salida,
                lote=updated_lote,
                bodega_destino=bodega_salida if diff > 0 else None,
                bodega_origen=bodega_salida if diff < 0 else None,
                cantidad=abs(diff).quantize(Decimal('0.01')),
                usuario=user,
                documento_ref=f'CORRECCION-LOTE-{updated_lote.codigo_lote}',
                saldo_resultante=stock_output.cantidad
            )
        except StockBodega.DoesNotExist:
            # El stock de producto terminado ya no existe (movido, vendido o
            # consumido): no se puede ajustar la salida. Se omite ese paso
            # pero se DEJA RASTRO — antes se silenciaba sin log, ocultando
            # una corrección de lote parcialmente aplicada.
            logger.warning(
                "Ajuste de stock de salida omitido: no existe StockBodega del lote",
                extra={"sd": {
                    "entity": "LoteProduccion",
                    "id": updated_lote.id,
                    "codigo_lote": updated_lote.codigo_lote,
                    "bodega_salida": getattr(bodega_salida, "id", None),
                    "producto_salida": getattr(producto_salida, "id", None),
                }},
            )

        # 2. Adjust Raw Material
        producto_input = producto_entrada
        stock_input, _ = safe_get_or_create_stock(
            StockBodega, bodega=bodega_entrada, producto=producto_input, lote=None)

        if stock_input.cantidad - diff < 0:
            raise ValidationError(
                {"peso_neto_producido": "No hay suficiente stock de materia prima para esta corrección."})

        stock_input.cantidad = (stock_input.cantidad - diff).quantize(Decimal('0.01'))
        stock_input._justificacion_auditoria = f"Correccion de lote {updated_lote.codigo_lote}"
        stock_input.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='AJUSTE',
            producto=producto_input,
            bodega_origen=bodega_entrada if diff > 0 else None,
            bodega_destino=bodega_entrada if diff < 0 else None,
            cantidad=abs(diff).quantize(Decimal('0.01')),
            usuario=user,
            documento_ref=f'CORRECCION-LOTE-{updated_lote.codigo_lote}'
        )

        # 3. Adjust Chemicals
        if orden.formula_color:
            from gestion.models import DetalleFormula
            for detalle in DetalleFormula.objects.filter(fase__formula=orden.formula_color):
                quimico = detalle.producto
                cantidad_diff = ((diff * detalle.gramos_por_kilo) / Decimal('1000.0')).quantize(Decimal('0.01'))
                if cantidad_diff != 0:
                    stock_quimico, _ = safe_get_or_create_stock(
                        StockBodega, bodega=bodega_entrada, producto=quimico, lote=None)
                    if stock_quimico.cantidad - cantidad_diff < 0:
                        raise ValidationError(
                            {"peso_neto_producido": f"No hay suficiente stock de quimico {quimico.codigo}."})
                    stock_quimico.cantidad = (stock_quimico.cantidad - cantidad_diff).quantize(Decimal('0.01'))
                    stock_quimico._justificacion_auditoria = f"Correccion de lote {updated_lote.codigo_lote}"
                    stock_quimico.save()

                    MovimientoInventario.objects.create(
                        tipo_movimiento='AJUSTE',
                        producto=quimico,
                        bodega_origen=bodega_entrada if cantidad_diff > 0 else None,
                        bodega_destino=bodega_entrada if cantidad_diff < 0 else None,
                        cantidad=abs(cantidad_diff),
                        usuario=user,
                        documento_ref=f'CORRECCION-LOTE-{updated_lote.codigo_lote}'
                    )

        # 4. Update order status
        total_producido = orden.lotes.aggregate(Sum('peso_neto_producido'))[
            'peso_neto_producido__sum'] or Decimal('0.00')
        if total_producido < orden.peso_neto_requerido and orden.estado == 'finalizada':
            orden.estado = 'en_proceso'
        elif total_producido >= orden.peso_neto_requerido and orden.estado == 'en_proceso':
            orden.estado = 'finalizada'
            orden.fecha_fin_planificada = timezone.now().date()
        orden.save()

    @staticmethod
    @transaction.atomic
    def revertir_por_rechazo(lote, user) -> Decimal:
        """
        Reversión manual de stock al rechazar un lote: salida producida,
        materia prima consumida y químicos descargados. No incluye reversión
        de mezcla ni de merma vendible — esas ya delegan a
        ConsumoMezclaService/MermaStockService (llamadas aparte por la vista,
        antes de invocar este método).

        Retorna la cantidad revertida (Decimal). Lanza ValidationError si no
        hay stock del lote para revertir.
        """
        orden = lote.orden_produccion
        bodega_salida = orden.bodega_salida or orden.bodega_entrada
        bodega_entrada_op = orden.bodega_entrada or orden.bodega_salida

        # 1. Reverse Output (Remove the produced lot from stock)
        try:
            # Find the stock item. If it doesn't exist (already sold/moved), we have a problem.
            # We assume it's still there for a "rejection".
            stock_output = StockBodega.objects.select_for_update().get(
                bodega=bodega_salida, producto=orden.producto_salida or orden.producto_entrada, lote=lote
            )
        except StockBodega.DoesNotExist:
            raise ValidationError("El stock del lote no existe en la bodega de origen.")

        cantidad_revertir = stock_output.cantidad
        if cantidad_revertir <= 0:
            raise ValidationError("No hay stock del lote para revertir (ya fue movido o vendido).")

        stock_output.cantidad = Decimal('0.00')
        stock_output._justificacion_auditoria = f"Reversion por rechazo de lote {lote.codigo_lote}"
        stock_output.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='AJUSTE',
            producto=orden.producto_salida or orden.producto_entrada,
            lote=lote,
            bodega_origen=bodega_salida,
            cantidad=cantidad_revertir,
            usuario=user,
            documento_ref=f'RECHAZO-LOTE-{lote.codigo_lote}',
            saldo_resultante=stock_output.cantidad
        )

        # 2.1 Raw Material
        producto_input = orden.producto_entrada or orden.producto_salida
        stock_input, _ = safe_get_or_create_stock(
            StockBodega,
            bodega=bodega_entrada_op,
            producto=producto_input,
            lote=None
        )
        stock_input.cantidad = (stock_input.cantidad + cantidad_revertir).quantize(Decimal('0.01'))
        stock_input._justificacion_auditoria = f"Reversion por rechazo de lote {lote.codigo_lote}"
        stock_input.save()

        MovimientoInventario.objects.create(
            tipo_movimiento='DEVOLUCION',
            producto=producto_input,
            bodega_destino=bodega_entrada_op,
            cantidad=cantidad_revertir.quantize(Decimal('0.01')),
            usuario=user,
            documento_ref=f'REV-LOTE-{lote.codigo_lote}'
        )

        # 2.2 Chemicals
        if orden.formula_color:
            from gestion.models import DetalleFormula
            for detalle in DetalleFormula.objects.filter(fase__formula=orden.formula_color):
                quimico = detalle.producto
                cantidad_devuelta = (
                    (cantidad_revertir * detalle.gramos_por_kilo) / Decimal('1000.0')
                ).quantize(Decimal('0.01'))

                stock_quimico, _ = safe_get_or_create_stock(
                    StockBodega,
                    bodega=bodega_entrada_op,
                    producto=quimico,
                    lote=None
                )
                stock_quimico.cantidad += cantidad_devuelta
                stock_quimico._justificacion_auditoria = f"Reversion por rechazo de lote {lote.codigo_lote}"
                stock_quimico.save()

                MovimientoInventario.objects.create(
                    tipo_movimiento='DEVOLUCION',
                    producto=quimico,
                    bodega_destino=bodega_entrada_op,
                    cantidad=cantidad_devuelta,
                    usuario=user,
                    documento_ref=f'REV-LOTE-{lote.codigo_lote}'
                )

        return cantidad_revertir
