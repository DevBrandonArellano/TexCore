import logging
from decimal import Decimal
from django.db import transaction
from django.core.exceptions import ValidationError
from inventory.models import MovimientoInventario, StockBodega
from gestion.models import ConsumoLoteDetalle, LoteProduccion

logger = logging.getLogger(__name__)

TOLERANCIA_KG = Decimal('0.01')


class ConsumoMezclaService:
    """
    SRP: gestiona el consumo de múltiples lotes de entrada para producir un lote de mezcla.
    COBIT DSS06: valida integridad de suma de componentes.
    ISO 27001 A.12.4: ConsumoLoteDetalle es inmutable post-creación.

    consumos_data esperado: list de dict con claves:
      - lote_origen_id: int
      - cantidad_kg: Decimal
      - genera_nuevo_lote: bool
      - bodega_id: int  (bodega donde está el stock del lote origen)
      - producto_id: int (producto del stock a consumir)
    """

    @staticmethod
    @transaction.atomic
    def consumir(
        orden,
        lote_output,
        consumos_data: list,
        user,
        consumo_total: Decimal = None,
    ) -> None:
        suma = sum(Decimal(str(c['cantidad_kg'])) for c in consumos_data)

        if consumo_total is not None:
            if abs(suma - consumo_total) > TOLERANCIA_KG:
                raise ValidationError(
                    f'La suma de cantidades ({suma} kg) no coincide con el consumo '
                    f'total esperado ({consumo_total} kg). '
                    f'Diferencia: {abs(suma - consumo_total)} kg.'
                )

        for consumo in consumos_data:
            lote_origen = LoteProduccion.objects.select_for_update().get(
                id=consumo['lote_origen_id']
            )
            cantidad = Decimal(str(consumo['cantidad_kg'])).quantize(Decimal('0.001'))
            bodega_id = consumo['bodega_id']
            producto_id = consumo['producto_id']

            try:
                stock = StockBodega.objects.select_for_update().get(
                    bodega_id=bodega_id,
                    producto_id=producto_id,
                    lote=lote_origen,
                )
            except StockBodega.DoesNotExist:
                raise ValidationError(
                    f'No se encontró stock para lote {lote_origen.codigo_lote} '
                    f'en bodega id={bodega_id}.'
                )

            cantidad_consumir = cantidad.quantize(Decimal('0.01'))
            if stock.cantidad < cantidad_consumir:
                raise ValidationError(
                    f'Stock insuficiente para lote {lote_origen.codigo_lote}. '
                    f'Disponible: {stock.cantidad} kg. Requerido: {cantidad_consumir} kg.'
                )

            stock.cantidad -= cantidad_consumir
            stock._justificacion_auditoria = f'Consumo en mezcla OP-{orden.codigo}'
            stock.save()

            MovimientoInventario.objects.create(
                tipo_movimiento='CONSUMO',
                producto_id=producto_id,
                lote=lote_origen,
                bodega_origen_id=bodega_id,
                cantidad=cantidad_consumir,
                documento_ref=f'OP-{orden.codigo}',
                usuario=user,
                saldo_resultante=stock.cantidad,
            )

            ConsumoLoteDetalle.objects.create(
                lote_produccion=lote_output,
                lote_origen=lote_origen,
                cantidad_consumida=cantidad,
                genera_nuevo_lote=consumo.get('genera_nuevo_lote', True),
                # Se guarda la bodega/producto exactos del stock descontado
                # (ya disponibles arriba) para que revertir() no tenga que
                # adivinar si el lote origen termina con stock en más de una
                # bodega (caso frecuente: reprocesos mueven el mismo lote
                # entre áreas/bodegas).
                bodega_id=bodega_id,
                producto_id=producto_id,
            )

        logger.info(
            'Mezcla de lotes consumida',
            extra={'sd': {
                'op': orden.codigo,
                'lote_output': lote_output.codigo_lote,
                'componentes': len(consumos_data),
                'total_kg': str(suma),
            }},
        )

    @staticmethod
    @transaction.atomic
    def revertir(lote_output, user, justificacion: str) -> None:
        """Revierte todos los ConsumoLoteDetalle de un lote_output."""
        consumos = ConsumoLoteDetalle.objects.filter(
            lote_produccion=lote_output
        ).select_related('lote_origen')

        for consumo in consumos:
            lote_origen = consumo.lote_origen
            try:
                if consumo.bodega_id and consumo.producto_id:
                    # Bodega/producto exactos, capturados en consumir() — restaura
                    # al lugar correcto aunque el lote tenga stock en más de una
                    # bodega (reprocesos).
                    stock = StockBodega.objects.select_for_update().get(
                        bodega_id=consumo.bodega_id,
                        producto_id=consumo.producto_id,
                        lote=lote_origen,
                    )
                else:
                    # Fila legacy (creada antes de este fix): no se guardó bodega/
                    # producto en su momento y no se puede reconstruir con certeza.
                    # Best-effort — mismo comportamiento que existía antes.
                    stock = StockBodega.objects.select_for_update().get(
                        lote=lote_origen,
                    )
            except StockBodega.DoesNotExist:
                continue
            except StockBodega.MultipleObjectsReturned:
                stock = StockBodega.objects.select_for_update().filter(
                    lote=lote_origen
                ).first()

            cantidad = consumo.cantidad_consumida.quantize(Decimal('0.01'))
            stock.cantidad += cantidad
            stock._justificacion_auditoria = justificacion
            stock.save()

            MovimientoInventario.objects.create(
                tipo_movimiento='DEVOLUCION',
                producto=stock.producto,
                lote=lote_origen,
                bodega_destino=stock.bodega,
                cantidad=cantidad,
                documento_ref=f'REV-{lote_output.codigo_lote}',
                usuario=user,
                saldo_resultante=stock.cantidad,
                observaciones=justificacion,
            )

        consumos.delete()
