"""
Artefacto RUP: Módulo de Servicio
Caso de Uso: CU-TransicionBodegas (Protocolo 3-Fase, Sprint 6)
Patrón: Service Layer + State (estado_movimiento)
SOLID: SRP — solo gestiona el ciclo de vida de materiales en tránsito.

Fases:  solicitado → en_transito → completado   (o → revertido)
Antes:  Bodega A → (desaparece) → Bodega B
Ahora:  Bodega A (descuento) → Bodega Tránsito (visible) → Bodega B (entrada)

Nota de adaptación: la especificación original descontaba el origen y sumaba
al destino sin tocar la bodega de tránsito en 'completar' — eso duplicaba el
material. Aquí cada fase mueve el stock exactamente una vez.
"""

import logging
from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ValidationError

from inventory.models import StockBodega, MovimientoInventario
from inventory.utils import safe_get_or_create_stock

logger = logging.getLogger('inventory.services.transicion_bodega')


class TransicionBodegaService:
    """Gestiona las 3 fases de movimiento de materiales entre bodegas."""

    @staticmethod
    @transaction.atomic
    def iniciar_transicion(
        producto,
        bodega_origen,
        bodega_destino,
        bodega_transicion,
        cantidad,
        usuario,
        documento_ref='',
    ) -> MovimientoInventario:
        """FASE 1+2: descuenta del origen y deja el material visible en la
        bodega de tránsito, con movimiento en estado 'en_transito'.
        """
        cantidad = Decimal(str(cantidad)).quantize(Decimal('0.001'))
        if cantidad <= 0:
            raise ValidationError('La cantidad a transferir debe ser mayor a cero.')

        # Origen: validar y descontar bajo lock
        stock_origen = StockBodega.objects.select_for_update().filter(
            bodega=bodega_origen, producto=producto, lote__isnull=True
        ).first()
        if not stock_origen or stock_origen.cantidad < cantidad:
            disponible = stock_origen.cantidad if stock_origen else Decimal('0.000')
            raise ValidationError(
                f'Stock insuficiente de {producto.descripcion} en {bodega_origen.nombre}: '
                f'disponible {disponible} kg, requerido {cantidad} kg.'
            )
        stock_origen.cantidad -= cantidad
        stock_origen._justificacion_auditoria = f'Transición 3-fase iniciada → {bodega_destino.nombre}'
        stock_origen.save()

        # Tránsito: el material queda visible en la bodega intermedia
        stock_transito, _ = safe_get_or_create_stock(
            StockBodega, bodega=bodega_transicion, producto=producto, lote=None,
        )
        stock_transito.cantidad += cantidad
        stock_transito._justificacion_auditoria = f'Material en tránsito {documento_ref}'
        stock_transito.save()

        movimiento = MovimientoInventario.objects.create(
            tipo_movimiento='TRANSFERENCIA',
            producto=producto,
            bodega_origen=bodega_origen,
            bodega_destino=bodega_destino,
            bodega_transicion=bodega_transicion,
            cantidad=cantidad,
            usuario=usuario,
            documento_ref=documento_ref or f'TRANSITO-{bodega_origen.nombre}-{bodega_destino.nombre}',
            estado_movimiento='en_transito',
            saldo_resultante=stock_origen.cantidad,
        )

        logger.info(
            f'Transición iniciada: {cantidad} kg de {producto.descripcion} '
            f'{bodega_origen.nombre} → [{bodega_transicion.nombre}] → {bodega_destino.nombre}'
        )
        return movimiento

    @staticmethod
    @transaction.atomic
    def completar_transicion(movimiento: MovimientoInventario, usuario) -> MovimientoInventario:
        """FASE 3: el material llega — sale de la bodega de tránsito y entra
        a la bodega destino. Se dispara cuando el bodeguero escanea la entrada
        o el tintorero confirma el consumo.
        """
        if movimiento.estado_movimiento != 'en_transito':
            raise ValidationError(
                f'El movimiento debe estar en tránsito; está "{movimiento.estado_movimiento}".'
            )

        cantidad = movimiento.cantidad

        # Salida de la bodega de tránsito (sin duplicar material)
        if movimiento.bodega_transicion:
            stock_transito = StockBodega.objects.select_for_update().filter(
                bodega=movimiento.bodega_transicion,
                producto=movimiento.producto,
                lote__isnull=True,
            ).first()
            if not stock_transito or stock_transito.cantidad < cantidad:
                raise ValidationError(
                    f'El stock en tránsito de {movimiento.producto.descripcion} es menor '
                    f'al esperado — verifique movimientos manuales en '
                    f'{movimiento.bodega_transicion.nombre}.'
                )
            stock_transito.cantidad -= cantidad
            stock_transito._justificacion_auditoria = f'Transición completada {movimiento.documento_ref}'
            stock_transito.save()

        # Entrada a la bodega destino
        stock_destino, _ = safe_get_or_create_stock(
            StockBodega,
            bodega=movimiento.bodega_destino,
            producto=movimiento.producto,
            lote=None,
        )
        stock_destino.cantidad += cantidad
        stock_destino._justificacion_auditoria = f'Recepción de transición {movimiento.documento_ref}'
        stock_destino.save()

        movimiento.estado_movimiento = 'completado'
        movimiento.saldo_resultante = stock_destino.cantidad
        movimiento._justificacion_auditoria = 'Transición 3-fase completada'
        movimiento.save()

        logger.info(f'Transición completada: {movimiento.documento_ref}')
        return movimiento

    @staticmethod
    @transaction.atomic
    def revertir_transicion(movimiento: MovimientoInventario, usuario, justificacion: str) -> MovimientoInventario:
        """Cancela una transición en curso: el material vuelve al origen y la
        bodega de tránsito se limpia. Solo aplica a 'solicitado'/'en_transito'.
        """
        if not justificacion or not justificacion.strip():
            raise ValidationError('Justificación obligatoria para revertir una transición.')
        if movimiento.estado_movimiento not in ('solicitado', 'en_transito'):
            raise ValidationError(
                'Solo se pueden revertir movimientos solicitados o en tránsito; '
                f'está "{movimiento.estado_movimiento}".'
            )

        cantidad = movimiento.cantidad

        # Restaurar el origen
        stock_origen, _ = safe_get_or_create_stock(
            StockBodega,
            bodega=movimiento.bodega_origen,
            producto=movimiento.producto,
            lote=None,
        )
        stock_origen.cantidad += cantidad
        stock_origen._justificacion_auditoria = f'Reversión de transición: {justificacion}'
        stock_origen.save()

        # Limpiar la bodega de tránsito si el material estaba ahí
        if movimiento.estado_movimiento == 'en_transito' and movimiento.bodega_transicion:
            stock_transito = StockBodega.objects.select_for_update().filter(
                bodega=movimiento.bodega_transicion,
                producto=movimiento.producto,
                lote__isnull=True,
            ).first()
            if stock_transito:
                stock_transito.cantidad -= cantidad
                stock_transito._justificacion_auditoria = f'Reversión de transición: {justificacion}'
                stock_transito.save()

        movimiento.estado_movimiento = 'revertido'
        movimiento._justificacion_auditoria = justificacion
        movimiento.save()

        logger.info(f'Transición revertida: {movimiento.documento_ref} — {justificacion}')
        return movimiento
