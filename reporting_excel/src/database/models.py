"""
ReportAuditLog: modelo ORM del registro de auditoría de generación de reportes.
SRP: única responsabilidad — representar la estructura de la tabla report_audit_log.
ISO 27001 A.12.4: trazabilidad de quién solicita qué reporte y con qué resultado.
COBIT MEA01: soporte de monitoreo del acceso a información gerencial y ejecutiva.

Índices en timestamp, requested_by y report_type garantizan consultas < 500 ms.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .engine import Base


class ReportAuditLog(Base):
    __tablename__ = "report_audit_log"
    __table_args__ = (
        Index("idx_report_timestamp", "timestamp"),        # filtros por rango de fecha
        Index("idx_report_requested_by", "requested_by"),  # quién solicita más reportes
        Index("idx_report_type", "report_type"),           # qué reporte se pide más
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)  # JWT sub claim
    report_type: Mapped[str] = mapped_column(String(100), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(200), nullable=False)
    params_json: Mapped[str | None] = mapped_column(Text, nullable=True)    # query params
    format: Mapped[str | None] = mapped_column(String(10), nullable=True)   # 'xlsx' | 'csv'
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(String(1000), nullable=True)
