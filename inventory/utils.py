import logging

from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef, Q

logger = logging.getLogger(__name__)

INTENTOS_DEADLOCK = 3


def es_deadlock(exc) -> bool:
    """SQL Server elige una víctima de deadlock (error 1205, SQLSTATE 40001) y
    pide reejecutar la transacción completa."""
    texto = f"{exc} {exc.__cause__}"
    return '1205' in texto or '40001' in texto


def stock_del_lote(queryset, lotes):
    """Filas de stock del producto de cada lote.

    Un lote con merma vendible tiene dos filas con el mismo lote: el producto terminado
    y la merma (producto_merma de la máquina, en bodega_merma). Buscar solo por lote
    toma cualquiera de las dos; aquí se fija el producto del lote. Un lote sin producto
    (dato antiguo sin orden) conserva la búsqueda solo por lote.
    """
    condicion = Q(pk__in=[])
    for lote in lotes:
        producto_id = lote.producto_del_stock_id
        condicion |= Q(lote_id=lote.pk, producto_id=producto_id) if producto_id else Q(lote_id=lote.pk)
    return queryset.filter(condicion)


def stock_vendible_del_lote(queryset, lotes):
    """Filas de stock de los lotes que el despacho puede vender: todas salvo la merma.

    El movimiento manual permite registrar en un lote un producto distinto al de su OP
    (decisión de producto del 2026-10-07) y el despacho debe venderlo. La merma vendible
    no sale al escanear el lote: se reconoce por el movimiento MERMA-<lote> que deja
    MermaStockService (producto y lote), no por la configuración actual de la máquina,
    que puede cambiar; y vale aunque la merma se haya trasladado a otra bodega.
    """
    from inventory.models import MovimientoInventario

    es_merma = MovimientoInventario.objects.filter(
        tipo_movimiento='PRODUCCION',
        lote_id=OuterRef('lote_id'),
        producto_id=OuterRef('producto_id'),
        documento_ref__startswith='MERMA-',
    )
    return queryset.filter(lote__in=lotes).exclude(Exists(es_merma))


def principal_primero(filas, lote):
    """Ordena las filas de un lote con la de su producto (el de la OP) primero."""
    principal = lote.producto_del_stock_id
    return sorted(filas, key=lambda fila: (fila.producto_id != principal, fila.id))


def safe_get_or_create_stock(model_class, bodega, producto, lote=None, defaults=None):
    """
    Versión robusta de get_or_create para StockBodega que maneja race conditions
    especialmente en SQL Server dentro de transacciones atómicas.

    Utiliza savepoints (transaction.atomic()) para capturar el IntegrityError
    sin invalidar la transacción externa.
    """
    if defaults is None:
        defaults = {'cantidad': 0}

    try:
        # Intento primario con select_for_update para bloquear si ya existe
        with transaction.atomic():
            return model_class.objects.select_for_update().get_or_create(
                bodega=bodega,
                producto=producto,
                lote=lote,
                defaults=defaults
            )
    except IntegrityError:
        # Si falló por IntegrityError (alguien más lo creó entre el SELECT y el INSERT)
        # el registro DEBE existir ahora.
        logger.info(
            "Race condition detectada en StockBodega para %s en %s (lote=%s). Reintentando...", producto, bodega, lote)
        return model_class.objects.select_for_update().get(
            bodega=bodega,
            producto=producto,
            lote=lote
        ), False
