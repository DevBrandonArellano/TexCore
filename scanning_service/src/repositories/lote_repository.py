"""
Implementación SQLAlchemy de ILoteRepository.
SRP: única responsabilidad — traducir operaciones de dominio a queries SQL.
DIP: la sesión se inyecta por constructor; no llama a SessionLocal() directamente.
Usa eager loading para evitar N+1 y lazy-load fuera de sesión.
"""
import logging
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from ..models import LoteProduccion, OrdenProduccion, StockBodega

logger = logging.getLogger(__name__)


class SqlLoteRepository:
    """
    Repositorio concreto que consulta SQL Server via SQLAlchemy.
    Implementa ILoteRepository por duck typing (compatible con el Protocol).
    """

    def __init__(self, db: Session) -> None:
        self._db = db

    def get_lote_by_codigo(self, codigo: str) -> Optional[LoteProduccion]:
        """
        Carga el lote con eager loading de orden_produccion → producto
        para evitar lazy-load después de que la sesión se cierra en el router.
        """
        return (
            self._db.query(LoteProduccion)
            .options(
                joinedload(LoteProduccion.orden_produccion)
                .joinedload(OrdenProduccion.producto)
            )
            .filter(LoteProduccion.codigo_lote == codigo)
            .first()
        )

    def get_stock_activo_por_lote(self, lote_id: int) -> Optional[StockBodega]:
        """
        Retorna el primer stock con cantidad > 0, con bodega cargada (eager)
        para evitar lazy-load después del cierre de sesión.
        """
        return (
            self._db.query(StockBodega)
            .options(joinedload(StockBodega.bodega))
            .filter(
                StockBodega.lote_id == lote_id,
                StockBodega.cantidad > 0,
            )
            .first()
        )
