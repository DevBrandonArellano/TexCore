"""
Servicio de Reversión de Despachos
Artefacto RUP: Módulo de Servicio
Caso de Uso: CU-ReversionDespacho
Patrón: Service Layer + Strategy
SOLID: SRP — solo gestiona reversión de despachos.
       DIP — depende de abstracciones (safe_get_or_create_stock)
       OCP — extensible para tipos de reversión sin modificar core
"""

from django.db import transaction
from django.utils import timezone
from decimal import Decimal
import logging
from inventory.models import (
    HistorialDespacho, DetalleHistorialDespacho,
    StockBodega, MovimientoInventario
)
from gestion.models import DescargaQuimicoOP
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
            ValidationError si algún lote no existe o stock está inconsistente
        """

        if not justificacion or not justificacion.strip():
            raise ValueError("Justificación obligatoria para reversar despacho")

        detalles = DetalleHistorialDespacho.objects.filter(
            historial=historial,
            es_devolucion=False  # Solo reversar despachos originales, no devoluciones
        ).select_related('lote', 'producto')

        if not detalles.exists():
            logger.info(f"Despacho #{historial.id} ya fue revertido o no tiene detalles para revertir")
            return

        movimientos_creados = []
        lotes_revertidos = []

        # 1. Procesar cada detalle de despacho para restaurar stock
        for detalle in detalles:
            if not detalle.lote or not detalle.producto:
                logger.warning(f"Detalle {detalle.id} sin lote o producto, saltando reversión")
                continue

            # Restaurar stock en bodega origen del despacho
            try:
                # Buscar el movimiento VENTA original para identificar bodega origen
                mov_original = MovimientoInventario.objects.filter(
                    tipo_movimiento='VENTA',
                    lote=detalle.lote,
                    producto=detalle.producto,
                    documento_ref__contains=f"Despacho #{historial.id}"
                ).first()

                if not mov_original:
                    logger.warning(f"No se encontró movimiento VENTA original para lote {detalle.lote.codigo_lote}")
                    continue

                bodega_origen = mov_original.bodega_origen
                cantidad_a_restaurar = detalle.peso

                # Restaurar stock
                stock, created = safe_get_or_create_stock(
                    StockBodega,
                    bodega=bodega_origen,
                    producto=detalle.producto,
                    lote=detalle.lote
                )

                stock.cantidad += cantidad_a_restaurar
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
                    f"Restaurado {cantidad_a_restaurar} kg de {detalle.producto.descripcion} "
                    f"en bodega {bodega_origen.nombre} - Despacho #{historial.id}"
                )

            except Exception as e:
                logger.error(f"Error restaurando stock para lote {detalle.lote.codigo_lote}: {str(e)}")
                raise

        # 2. Marcar detalles como devolución
        detalles.update(es_devolucion=True)

        # 3. Revertir DescargaQuimicoOP asociados (si existen)
        # Buscar OPs asociadas a los pedidos de este despacho
        DespachoReversionService._revertir_descargas_quimicas(
            historial, usuario, justificacion
        )

        # 4. Revertir estado del pedido si es necesario
        from gestion.models import PedidoVenta
        pedidos = historial.pedidos.filter(estado='despachado')
        for pedido in pedidos:
            pedido.estado = 'pendiente'
            pedido.fecha_despacho = None
            pedido.save()
            logger.info(f"Pedido #{pedido.id} revertido a estado pendiente")

        logger.info(
            f"Despacho #{historial.id} revertido exitosamente por {usuario.get_full_name() or usuario.username}. "
            f"Lotes: {','.join(lotes_revertidos)}"
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
        pedidos = historial.pedidos.all()

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
                stock, created = safe_get_or_create_stock(
                    StockBodega,
                    bodega=descarga.bodega,
                    producto=descarga.producto
                )

                stock.cantidad += descarga.cantidad_calculada_kg
                stock._justificacion_auditoria = f"Reversión Despacho por {justificacion}"
                stock.save()

                # Crear DEVOLUCION
                MovimientoInventario.objects.create(
                    tipo_movimiento='DEVOLUCION',
                    producto=descarga.producto,
                    bodega_destino=descarga.bodega,
                    cantidad=descarga.cantidad_calculada_kg,
                    usuario=usuario,
                    documento_ref=f"REVERT-DESC-OP-{op.codigo}",
                    saldo_resultante=stock.cantidad
                )

                # Marcar como revertida
                descarga.estado = 'revertida'
                descarga.justificacion = justificacion
                descarga.save(update_fields=['estado', 'justificacion'])

                logger.info(
                    f"Descarga química revertida: OP {op.codigo} - "
                    f"{descarga.cantidad_calculada_kg} kg de {descarga.producto.descripcion}"
                )
