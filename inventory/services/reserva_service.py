import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from gestion.models import (
    Bodega,
    DetallePedido,
    LoteProduccion,
    OperacionProduccion,
    OrdenProduccion,
    PedidoVenta,
    Producto,
)
from inventory.models import StockBodega

logger = logging.getLogger('inventory.reserva')


class ReservaService:
    """
    Servicio de Reserva Inmutable y Producción Bajo Pedido (Make-to-Order / MTO).
    Garantiza el aislamiento entre inventario de venta libre y lotes fabricados
    a la medida para pedidos comerciales específicos, impidiendo que sean
    desviados o despachados a otros clientes.
    """

    @classmethod
    @transaction.atomic
    def crear_orden_desde_pedido(
        cls,
        detalle_pedido: DetallePedido,
        user=None,
        bodega_salida: Optional[Bodega] = None,
        bodega_entrada: Optional[Bodega] = None,
        formula_color=None,
        maquina_asignada=None,
        prioridad: str = 'alta',
        peso_solicitado: Optional[Decimal] = None,
    ) -> OrdenProduccion:
        """
        Crea una OrdenProduccion MTO vinculada formalmente a un DetallePedido.
        """
        if not detalle_pedido or not detalle_pedido.pk:
            raise ValidationError("Se requiere un detalle de pedido válido.")

        pedido = detalle_pedido.pedido_venta
        if not pedido:
            raise ValidationError("El detalle no pertenece a ningún pedido de venta.")

        if pedido.anulado:
            raise ValidationError("No se pueden crear órdenes de producción para pedidos anulados.")

        if pedido.estado in ['facturado', 'despachado']:
            raise ValidationError(
                f"No se pueden generar órdenes para un pedido en estado '{pedido.get_estado_display()}'."
            )

        saldo_pendiente = detalle_pedido.saldo_pendiente_fabricacion
        if saldo_pendiente <= Decimal('0.000'):
            raise ValidationError(
                f"El ítem {detalle_pedido.producto.codigo} ya ha completado su requerimiento de fabricación."
            )

        peso_requerido = peso_solicitado if peso_solicitado is not None else saldo_pendiente
        if peso_requerido <= Decimal('0.000'):
            raise ValidationError("El peso requerido debe ser mayor a 0.")

        if not bodega_salida:
            bodega_salida = Bodega.objects.filter(
                sede=pedido.sede,
            ).order_by('id').first()

        correlativo = OrdenProduccion.objects.filter(
            pedido_venta=pedido,
        ).count() + 1
        codigo_op = f"MTO-PED-{pedido.id}-{detalle_pedido.producto.codigo}-{correlativo}"
        if len(codigo_op) > 100:
            codigo_op = codigo_op[:100]

        op = OrdenProduccion.objects.create(
            codigo=codigo_op,
            producto_salida=detalle_pedido.producto,
            peso_neto_requerido=Decimal(str(peso_requerido)).quantize(Decimal('0.01')),
            bodega_salida=bodega_salida,
            bodega_entrada=bodega_entrada,
            formula_color=formula_color,
            prioridad=prioridad,
            maquina_asignada=maquina_asignada,
            operario_asignado=user,
            sede=pedido.sede,
            pedido_venta=pedido,
            detalle_pedido=detalle_pedido,
            estado='pendiente',
            observaciones=(
                f"Producción MTO vinculada al Pedido #{pedido.id} "
                f"({pedido.cliente.nombre_razon_social if pedido.cliente else 'Sin Cliente'})"
            ),
        )

        detalle_pedido.estado_fabricacion = 'en_proceso'
        detalle_pedido.save(update_fields=['estado_fabricacion'])

        logger.info(
            f"Orden de Producción MTO {op.codigo} generada exitosamente para Pedido #{pedido.id} "
            f"(Producto: {detalle_pedido.producto.codigo}, Requerido: {op.peso_neto_requerido}kg)"
        )
        return op

    @classmethod
    @transaction.atomic
    def reservar_lote_para_pedido(
        cls,
        lote: LoteProduccion,
        pedido: PedidoVenta,
        detalle_pedido: Optional[DetallePedido] = None,
        cantidad: Optional[Decimal] = None,
        user=None,
    ) -> None:
        """
        Asigna la reserva inmutable de un lote producido a un PedidoVenta.
        Aumenta el stock_comprometido en StockBodega y actualiza la cantidad fabricada en DetallePedido.
        """
        if not lote or not lote.pk:
            raise ValidationError("Se requiere un lote válido.")
        if not pedido or not pedido.pk:
            raise ValidationError("Se requiere un pedido válido.")

        if lote.pedido_venta_reserva and lote.pedido_venta_reserva_id != pedido.id:
            raise ValidationError(
                f"El lote {lote.codigo_lote} ya está reservado para el Pedido #{lote.pedido_venta_reserva.id}."
            )

        cant_reserva = Decimal(str(cantidad if cantidad is not None else lote.peso_neto_producido)).quantize(Decimal('0.001'))

        # Actualizar lote
        if lote.pedido_venta_reserva_id != pedido.id:
            lote.pedido_venta_reserva = pedido
            lote.save(update_fields=['pedido_venta_reserva'])

        # Bloquear fila de StockBodega y aumentar stock_comprometido
        stock_qs = StockBodega.objects.select_for_update().filter(lote=lote)
        for stock in stock_qs:
            stock.stock_comprometido = min(stock.cantidad, stock.stock_comprometido + cant_reserva)
            stock._justificacion_auditoria = f"Reserva MTO para Pedido #{pedido.id}"
            stock.save(update_fields=['stock_comprometido'])

        # Actualizar DetallePedido
        det = detalle_pedido
        if not det and lote.orden_produccion and lote.orden_produccion.detalle_pedido:
            det = lote.orden_produccion.detalle_pedido

        prod = lote.producto or (
            (lote.orden_produccion.producto_salida or lote.orden_produccion.producto_entrada)
            if lote.orden_produccion else None
        )
        if not det and prod:
            det = pedido.detalles.filter(producto=prod).first()

        if det:
            det_locked = DetallePedido.objects.select_for_update().get(pk=det.pk)
            det_locked.cantidad_fabricada += cant_reserva
            if det_locked.cantidad_fabricada >= det_locked.peso:
                det_locked.estado_fabricacion = 'fabricado'
            else:
                det_locked.estado_fabricacion = 'en_proceso'
            det_locked.save(update_fields=['cantidad_fabricada', 'estado_fabricacion'])

        logger.info(
            f"Lote {lote.codigo_lote} ({cant_reserva}kg) reservado exitosamente para Pedido #{pedido.id}."
        )

    @classmethod
    @transaction.atomic
    def liberar_reserva_lote(
        cls,
        lote: LoteProduccion,
        user=None,
        justificacion: str = '',
    ) -> None:
        """
        Libera la reserva MTO de un lote, retornando el saldo a venta libre
        y descontando la cantidad fabricada en DetallePedido.
        """
        if not lote or not lote.pk or not lote.pedido_venta_reserva:
            return

        pedido = lote.pedido_venta_reserva
        cant_liberar = lote.peso_neto_producido

        stock_qs = StockBodega.objects.select_for_update().filter(lote=lote)
        for stock in stock_qs:
            stock.stock_comprometido = max(Decimal('0.000'), stock.stock_comprometido - cant_liberar)
            stock._justificacion_auditoria = f"Liberación de Reserva MTO: {justificacion}"
            stock.save(update_fields=['stock_comprometido'])

        det = None
        if lote.orden_produccion and lote.orden_produccion.detalle_pedido:
            det = lote.orden_produccion.detalle_pedido

        prod = lote.producto or (
            (lote.orden_produccion.producto_salida or lote.orden_produccion.producto_entrada)
            if lote.orden_produccion else None
        )
        if not det and prod:
            det = pedido.detalles.filter(producto=prod).first()

        if det:
            det_locked = DetallePedido.objects.select_for_update().get(pk=det.pk)
            det_locked.cantidad_fabricada = max(Decimal('0.000'), det_locked.cantidad_fabricada - cant_liberar)
            if det_locked.cantidad_fabricada >= det_locked.peso:
                det_locked.estado_fabricacion = 'fabricado'
            elif det_locked.cantidad_fabricada > Decimal('0.000'):
                det_locked.estado_fabricacion = 'en_proceso'
            else:
                det_locked.estado_fabricacion = 'pendiente'
            det_locked.save(update_fields=['cantidad_fabricada', 'estado_fabricacion'])

        lote.pedido_venta_reserva = None
        lote.save(update_fields=['pedido_venta_reserva'])

        logger.info(
            f"Reserva MTO de Lote {lote.codigo_lote} liberada para Pedido #{pedido.id}. "
            f"Motivo: {justificacion}"
        )

    @classmethod
    def validar_despacho_lote(cls, lote: LoteProduccion, pedido_id: int) -> None:
        """
        Verifica que el lote escaneado para despacho no pertenezca a una reserva
        de otro pedido comercial diferente.
        """
        if lote.pedido_venta_reserva_id and lote.pedido_venta_reserva_id != pedido_id:
            raise ValidationError(
                f"El lote {lote.codigo_lote} está reservado exclusivamente para el Pedido "
                f"#{lote.pedido_venta_reserva_id} ({lote.pedido_venta_reserva.cliente.nombre_razon_social if lote.pedido_venta_reserva.cliente else 'N/A'}) "
                f"y no puede ser despachado en el Pedido #{pedido_id}."
            )
