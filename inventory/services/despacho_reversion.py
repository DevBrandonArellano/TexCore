"""
Servicio de Reversión de Despachos
Artefacto RUP: Módulo de Servicio
Caso de Uso: CU-ReversionDespacho
Patrón: Service Layer + Strategy
SOLID: SRP — solo gestiona reversión de despachos.
       DIP — depende de abstracciones (safe_get_or_create_stock)
       OCP — extensible para tipos de reversión sin modificar core
"""

import logging
from decimal import Decimal

from django.db import transaction

from gestion.models import DescargaQuimicoOP
from inventory.models import DetalleHistorialDespacho, HistorialDespacho, MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger(__name__)


class DespachoReversionService:
    """
    Servicio para revertir despachos con auditoría completa.
    Restaura stock de bodegas y marca registros de descarga como revertidos.
    """

    @staticmethod
    @transaction.atomic
    def revertir_despacho(historial: HistorialDespacho, usuario, justificacion: str):
        """
        Revierte un despacho existente:
        1. Restaura stock en cada bodega origen
        2. Marca detalles como reversión
        3. Revierte DescargaQuimicoOP asociados si existen
        4. Crea MovimientoInventario DEVOLUCION

        Args:
            historial: HistorialDespacho a revertir
            usuario: Usuario que solicita la reversión
            justificacion: Razón de la reversión

        Raises:
            ValueError si falta la justificación, el movimiento original o su bodega (la vista responde 400)
        """

        if not justificacion or not justificacion.strip():
            raise ValueError("Justificación obligatoria para reversar despacho")

        detalles = DetalleHistorialDespacho.objects.filter(
            historial=historial,
            es_devolucion=False  # Solo reversar despachos originales, no devoluciones
        ).select_related('lote', 'producto', 'movimiento_venta__bodega_origen').order_by('lote_id', 'id')
        # Mismo orden de lote con el que ProcessDespachoAPIView bloquea el stock:
        # así un despacho y una reversión concurrentes no se interbloquean.

        if not detalles.exists():
            logger.info(
                'Despacho #%s ya fue revertido o no tiene detalles para revertir',
                historial.id,
            )
            return None

        movimientos_creados = []
        lotes_revertidos = []

        # 1. Procesar cada detalle de despacho para restaurar stock
        for detalle in detalles:
            if not detalle.lote or not detalle.producto:
                logger.warning(
                    'Detalle %s sin lote o producto, saltando reversión',
                    detalle.id,
                )
                continue

            # Restaurar stock en bodega origen del despacho
            try:
                # P1-007: la FK directa es la fuente de verdad; el string
                # documento_ref queda solo como fallback para registros
                # creados antes de la migración 0029
                mov_original = detalle.movimiento_venta
                if not mov_original:
                    mov_original = MovimientoInventario.objects.filter(
                        tipo_movimiento='VENTA',
                        lote=detalle.lote,
                        producto=detalle.producto,
                        documento_ref__contains=f"Despacho #{historial.id}"
                    ).first()

                if not mov_original:
                    # Fail-loud: saltar el lote en silencio dejaba el stock
                    # inconsistente sin que nadie lo notara. La transacción
                    # atómica revierte todo lo procesado hasta aquí.
                    raise ValueError(
                        f"No se pudo localizar el movimiento VENTA original del lote "
                        f"{detalle.lote.codigo_lote} (Despacho #{historial.id}). "
                        f"La reversión se cancela para evitar stock inconsistente."
                    )

                bodega_origen = mov_original.bodega_origen
                if bodega_origen is None:
                    raise ValueError(
                        f"El movimiento de venta #{mov_original.id} no tiene bodega de origen: "
                        f"no se puede restaurar el stock del despacho #{historial.id}."
                    )
                cantidad_a_restaurar = detalle.peso

                # Restaurar stock
                stock, _created = safe_get_or_create_stock(
                    StockBodega,
                    bodega=bodega_origen,
                    producto=detalle.producto,
                    lote=detalle.lote
                )

                stock.cantidad += cantidad_a_restaurar
                if detalle.lote and detalle.lote.pedido_venta_reserva:
                    stock.stock_comprometido = min(stock.cantidad, stock.stock_comprometido + cantidad_a_restaurar)
                stock._justificacion_auditoria = f"Reversión Despacho #{historial.id}: {justificacion}"
                stock.save()

                # Crear MovimientoInventario DEVOLUCION (reversión de la VENTA)
                mov_devolucion = MovimientoInventario.objects.create(
                    tipo_movimiento='DEVOLUCION',
                    producto=detalle.producto,
                    lote=detalle.lote,
                    bodega_destino=bodega_origen,
                    cantidad=cantidad_a_restaurar,
                    usuario=usuario,
                    documento_ref=f"REVERT-Despacho-#{historial.id}",
                    saldo_resultante=stock.cantidad
                )

                movimientos_creados.append(mov_devolucion.id)
                lotes_revertidos.append(detalle.lote.codigo_lote)

                logger.info(
                    'Restaurado %s kg de %s en bodega %s - Despacho #%s',
                    cantidad_a_restaurar,
                    detalle.producto.descripcion,
                    bodega_origen.nombre,
                    historial.id,
                )

            except Exception as e:
                logger.exception(
                    "Error restaurando stock para lote %s: %s",
                    detalle.lote.codigo_lote,
                    e,
                )
                raise

        # 2. Marcar detalles como devolución
        detalles.update(es_devolucion=True)

        # 3. Revertir DescargaQuimicoOP asociados (si existen)
        # Buscar OPs asociadas a los pedidos de este despacho
        DespachoReversionService._revertir_descargas_quimicas(
            historial, usuario, justificacion
        )

        # 4. Recalcular el estado real de cada pedido vinculado a este despacho.
        # No se fuerza 'pendiente' a ciegas: si el pedido tenía OTRO despacho
        # previo (no revertido) que ya lo cubría parcialmente, debe quedar en
        # 'despachado_parcial', no volver a 'pendiente' perdiendo ese avance.
        from inventory.services.despacho_estado import DespachoEstadoService

        for pedido in historial.pedidos.all():
            nuevo_estado = DespachoEstadoService.recalcular_estado(pedido)
            if nuevo_estado != pedido.estado:
                pedido.estado = nuevo_estado
                if nuevo_estado == 'pendiente':
                    pedido.fecha_despacho = None
                pedido.save()
                logger.info(
                    "Pedido #%s recalculado a estado '%s' tras reversión",
                    pedido.id,
                    nuevo_estado,
                )

        logger.info(
            "Despacho #%s revertido exitosamente por %s. Lotes: %s",
            historial.id,
            usuario.get_full_name() or usuario.username,
            ','.join(lotes_revertidos)
        )

        return {
            'despacho_id': historial.id,
            'movimientos_creados': len(movimientos_creados),
            'lotes_revertidos': len(lotes_revertidos)
        }

    @staticmethod
    def _revertir_descargas_quimicas(historial: HistorialDespacho, usuario, justificacion: str):
        """
        Revierte registros de DescargaQuimicoOP asociados a los pedidos del despacho.

        Busca OPs que cumplan estos criterios:
        - Crear fecha entre fecha despacho y fecha actual
        - Tengan estado de descarga 'aplicada'
        - Coincidan con los lotes del despacho
        """
        from gestion.models import OrdenProduccion

        # Obtener pedidos asociados al despacho
        historial.pedidos.all()

        # Obtener detalles del despacho (lotes despachados)
        detalles = DetalleHistorialDespacho.objects.filter(
            historial=historial
        ).values_list('lote_id', flat=True)

        if not detalles:
            return

        # Buscar OPs con OPquímicos descargados que usen estos lotes
        ops = OrdenProduccion.objects.filter(
            lotes__id__in=detalles,
            inventario_descontado=True
        )

        for op in ops:
            descargas_aplicadas = DescargaQuimicoOP.objects.filter(
                orden_produccion=op,
                estado='aplicada'
            ).select_related('producto', 'bodega')

            for descarga in descargas_aplicadas:
                # Restaurar stock
                stock, _created = safe_get_or_create_stock(
                    StockBodega,
                    bodega=descarga.bodega,
                    producto=descarga.producto
                )

                # Devolución al stock (3 decimales — precisión estándar del sistema,
                # StockBodega.cantidad es DECIMAL(12,3) pero cantidad_calculada_kg es
                # DECIMAL(12,6); sin este quantize, full_clean() revienta con
                # "Ensure that there are no more than 3 decimal places" y la
                # reversión completa del despacho fallaba con 500, ver descarga_quimicos.py).
                cantidad_revertir = descarga.cantidad_calculada_kg.quantize(Decimal('0.001'))
                stock.cantidad += cantidad_revertir
                stock._justificacion_auditoria = f"Reversión Despacho por {justificacion}"
                stock.save()

                # Crear DEVOLUCION
                MovimientoInventario.objects.create(
                    tipo_movimiento='DEVOLUCION',
                    producto=descarga.producto,
                    bodega_destino=descarga.bodega,
                    cantidad=cantidad_revertir,
                    usuario=usuario,
                    documento_ref=f"REVERT-DESC-OP-{op.codigo}",
                    saldo_resultante=stock.cantidad
                )

                # Marcar como revertida
                descarga.estado = 'revertida'
                descarga.justificacion = justificacion
                descarga.save(update_fields=['estado', 'justificacion'])

                logger.info(
                    'Descarga química revertida: OP %s - %s kg de %s',
                    op.codigo,
                    descarga.cantidad_calculada_kg,
                    descarga.producto.descripcion,
                )
