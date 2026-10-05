import logging

from django.db import IntegrityError, transaction

logger = logging.getLogger(__name__)

INTENTOS_DEADLOCK = 3


def es_deadlock(exc) -> bool:
    """SQL Server elige una víctima de deadlock (error 1205, SQLSTATE 40001) y
    pide reejecutar la transacción completa."""
    texto = f"{exc} {exc.__cause__}"
    return '1205' in texto or '40001' in texto


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
