"""
ScanAuditLog: modelo ORM del registro de auditoría de escaneos.
SRP: única responsabilidad — representar la estructura de la tabla scan_audit_log.
ISO 27001 A.12.4: trazabilidad de eventos de escaneo de lotes de producción.
COBIT MEA01: soporte de monitoreo de operaciones de escaneo en tiempo real.

Normalización parcial: producto_nombre y bodega_nombre se desnormalizan
intencionalmente para preservar el valor histórico exacto del momento del evento.
Índices en timestamp, valid y lote_codigo garantizan consultas < 500 ms.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .engine import Base


class ScanAuditLog(Base):
    __tablename__ = "scan_audit_log"
    __table_args__ = (
        Index("idx_scan_timestamp", "timestamp"),      # filtros por rango de fecha
        Index("idx_scan_valid", "valid"),              # búsqueda de escaneos fallidos
        Index("idx_scan_lote_codigo", "lote_codigo"),  # lookup por código de lote
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    codigo_scanned: Mapped[str] = mapped_column(String(200), nullable=False)
    valid: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    lote_codigo: Mapped[str | None] = mapped_column(String(200), nullable=True)
    producto_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    producto_nombre: Mapped[str | None] = mapped_column(String(500), nullable=True)
    bodega_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bodega_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    peso_kg: Mapped[str | None] = mapped_column(String(50), nullable=True)
