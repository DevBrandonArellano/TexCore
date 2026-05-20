"""
Protocolo (interfaz) del repositorio de lotes.
LSP + DIP: cualquier implementación (SQL Server real, mock en memoria)
es intercambiable en los servicios que dependan de ILoteRepository.
Los tests de integración usan app.dependency_overrides en lugar de sys.modules hacks.
"""
from typing import Optional, Protocol, runtime_checkable

from ..models import LoteProduccion, StockBodega


@runtime_checkable
class ILoteRepository(Protocol):
    """Contrato de acceso a datos para lotes de producción."""

    def get_lote_by_codigo(self, codigo: str) -> Optional[LoteProduccion]:
        """Retorna el LoteProduccion con sus relaciones cargadas, o None si no existe."""
        ...

    def get_stock_activo_por_lote(self, lote_id: int) -> Optional[StockBodega]:
        """Retorna el primer StockBodega con cantidad > 0 para el lote, o None."""
        ...
