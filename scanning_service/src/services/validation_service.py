"""
Servicio de validación de lotes.
SRP: contiene TODA la lógica de negocio del dominio de despacho.
DIP: depende de ILoteRepository (abstracción), no de SQLAlchemy directamente.
No conoce HTTP, no conoce FastAPI, no conoce SQLAlchemy.
"""
import logging
from typing import Optional

from ..repositories.base import ILoteRepository
from ..schemas.validate import LoteInfo, ValidateResponse

logger = logging.getLogger(__name__)


class LoteValidationService:
    """
    Encapsula las reglas de negocio para determinar si un lote puede ser despachado:
      1. El lote debe existir en el sistema.
      2. El lote debe tener una orden de producción con producto asociado.
      3. El lote debe tener stock disponible (cantidad > 0) en alguna bodega.
    """

    def __init__(self, repository: ILoteRepository) -> None:
        self._repo = repository

    def validate(self, codigo: str) -> ValidateResponse:
        """
        Valida un código de lote escaneado.

        Args:
            codigo: Código del lote ya limpiado (strip) por el schema Pydantic.

        Returns:
            ValidateResponse con valid=True y datos del lote, o valid=False con razón.
        """
        logger.info("Iniciando validación de lote", extra={"sd": {"code": codigo[:8]}})

        lote = self._repo.get_lote_by_codigo(codigo)
        if lote is None:
            logger.warning("Lote no encontrado", extra={"sd": {"code": codigo[:8]}})
            return ValidateResponse(valid=False, reason="Lote no encontrado en el sistema")

        if not lote.orden_produccion or not lote.orden_produccion.producto_salida:
            logger.warning("Lote sin orden o producto", extra={"sd": {"lote_id": lote.id}})
            return ValidateResponse(
                valid=False,
                reason="Lote no tiene orden de producción o producto asociado",
            )

        stock = self._repo.get_stock_activo_por_lote(lote.id)
        if stock is None:
            logger.warning("Lote sin stock", extra={"sd": {"lote_id": lote.id}})
            return ValidateResponse(
                valid=False,
                reason="Lote existe pero no tiene stock disponible (0 kg)",
            )

        producto = lote.orden_produccion.producto_salida
        bodega = stock.bodega

        logger.info(
            "Validación exitosa",
            extra={"sd": {"valid": "true", "producto_id": producto.id, "bodega_id": bodega.id}},
        )
        return ValidateResponse(
            valid=True,
            lote=LoteInfo(
                codigo=lote.codigo_lote,
                producto_id=producto.id,
                producto_nombre=producto.descripcion,
                peso=str(stock.cantidad),
                bodega_id=bodega.id,
                bodega_nombre=bodega.nombre,
            ),
        )
