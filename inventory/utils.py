from django.db import transaction, IntegrityError
import logging

logger = logging.getLogger(__name__)

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
        logger.info(f"Race condition detectada en StockBodega para {producto} en {bodega} (lote={lote}). Reintentando...")
        return model_class.objects.select_for_update().get(
            bodega=bodega,
            producto=producto,
            lote=lote
        ), False
