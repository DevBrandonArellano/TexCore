"""
Servicio de Reversión de un Movimiento de Inventario individual.
Artefacto RUP: Módulo de Servicio
Patrón: Service Layer (mismo patrón que DespachoReversionService, a nivel de
un único MovimientoInventario en vez de un despacho completo con múltiples
detalles).
SOLID: SRP — solo gestiona la reversión de stock de un movimiento.
       DIP — depende de abstracciones (safe_get_or_create_stock).
"""
from django.db import transaction

from inventory.models import MovimientoInventario, StockBodega
from inventory.utils import safe_get_or_create_stock

# Mismas categorías que MovimientoInventarioViewSet.create()
TIPOS_ENTRADA = ('COMPRA', 'PRODUCCION', 'DEVOLUCION', 'AJUSTE')
TIPOS_SALIDA = ('VENTA', 'CONSUMO', 'MERMA')


class MovimientoReversionService:
    """
    Revierte el efecto de stock de un MovimientoInventario y deja un
    movimiento compensatorio para trazabilidad (no borra el histórico
    contable a ciegas — el movimiento original se elimina aparte, por el
    caller, una vez que la reversión de stock fue exitosa).
    """

    @staticmethod
    @transaction.atomic
    def revertir(movimiento: MovimientoInventario, usuario, justificacion: str):
        if not justificacion or not justificacion.strip():
            raise ValueError("Debe proporcionar una justificación para revertir el movimiento.")

        # Guarda: un movimiento ligado a un despacho (FK inversa
        # detalles_despacho, ver DetalleHistorialDespacho.movimiento_venta)
        # tiene su propio flujo de reversión — revertirlo aquí dejaría el
        # HistorialDespacho/DetalleHistorialDespacho inconsistente.
        if movimiento.detalles_despacho.exists():
            raise ValueError(
                "Este movimiento pertenece a un despacho; revierta el despacho completo "
                "desde el historial de despachos en vez de eliminar el movimiento directamente."
            )

        tipo = movimiento.tipo_movimiento
        cantidad = movimiento.cantidad
        compensatorio_origen = None
        compensatorio_destino = None

        if tipo == 'TRANSFERENCIA':
            if movimiento.bodega_origen:
                MovimientoReversionService._devolver_a_origen(movimiento, cantidad, justificacion)
                compensatorio_destino = movimiento.bodega_origen
            if movimiento.bodega_destino:
                MovimientoReversionService._restar_de_destino(movimiento, cantidad, justificacion)
                compensatorio_origen = movimiento.bodega_destino
        elif tipo in TIPOS_ENTRADA:
            MovimientoReversionService._restar_de_destino(movimiento, cantidad, justificacion)
            compensatorio_origen = movimiento.bodega_destino
        elif tipo in TIPOS_SALIDA:
            MovimientoReversionService._devolver_a_origen(movimiento, cantidad, justificacion)
            compensatorio_destino = movimiento.bodega_origen
        else:
            raise ValueError(f"Tipo de movimiento '{tipo}' no soportado para reversión.")

        MovimientoInventario.objects.create(
            tipo_movimiento='DEVOLUCION',
            producto=movimiento.producto,
            cantidad=cantidad,
            lote=movimiento.lote,
            bodega_origen=compensatorio_origen,
            bodega_destino=compensatorio_destino,
            usuario=usuario,
            documento_ref=f"REVERT-Mov-#{movimiento.id}",
            observaciones=f"Reversión de movimiento #{movimiento.id} ({tipo}). Motivo: {justificacion}"[:500],
        )

    @staticmethod
    def _restar_de_destino(movimiento, cantidad, justificacion):
        """Revierte una entrada: resta de la bodega donde había entrado."""
        if not movimiento.bodega_destino:
            raise ValueError("El movimiento de entrada no tiene bodega de destino registrada.")
        stock = StockBodega.objects.select_for_update().get(
            bodega=movimiento.bodega_destino, producto=movimiento.producto, lote=movimiento.lote)
        if stock.cantidad < cantidad:
            raise ValueError(
                f"No se puede revertir: el stock actual ({stock.cantidad}) es menor a la "
                f"cantidad del movimiento ({cantidad}) — probablemente ya se consumió.")
        stock.cantidad -= cantidad
        stock._justificacion_auditoria = justificacion
        stock.save()

    @staticmethod
    def _devolver_a_origen(movimiento, cantidad, justificacion):
        """Revierte una salida: devuelve a la bodega de donde había salido."""
        if not movimiento.bodega_origen:
            raise ValueError("El movimiento de salida no tiene bodega de origen registrada.")
        stock, _ = safe_get_or_create_stock(
            StockBodega, bodega=movimiento.bodega_origen,
            producto=movimiento.producto, lote=movimiento.lote)
        stock.cantidad += cantidad
        stock._justificacion_auditoria = justificacion
        stock.save()
