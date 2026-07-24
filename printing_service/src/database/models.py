"""
PrintAuditLog: modelo ORM del registro de auditoría de documentos generados.
SRP: única responsabilidad — representar la estructura de la tabla print_audit_log.
ISO 27001 A.12.4: trazabilidad de generación de documentos comerciales y etiquetas.
COBIT MEA01: soporte de monitoreo de operaciones de impresión.

Índices en timestamp, document_type y success garantizan consultas < 500 ms.
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .engine import Base


class PrintAuditLog(Base):
    __tablename__ = "print_audit_log"
    __table_args__ = (
        Index("idx_print_timestamp", "timestamp"),          # filtros por rango de fecha
        Index("idx_print_document_type", "document_type"),  # PDF vs ZPL
        Index("idx_print_success", "success"),              # búsqueda de errores de impresión
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    document_type: Mapped[str] = mapped_column(String(10), nullable=False)   # 'PDF' | 'ZPL'
    template_used: Mapped[str] = mapped_column(String(200), nullable=False)
    pedido_id: Mapped[int | None] = mapped_column(Integer, nullable=True)    # solo PDF
    guia_remision: Mapped[str | None] = mapped_column(String(100), nullable=True)
    lote_codigo: Mapped[str | None] = mapped_column(String(200), nullable=True)  # solo ZPL
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # F2: gobernanza de reimpresión/reetiquetado — trazabilidad de quién y por qué.
    usuario: Mapped[str | None] = mapped_column(String(150), nullable=True)
    motivo: Mapped[str | None] = mapped_column(String(30), nullable=True)
    tipo_evento: Mapped[str | None] = mapped_column(String(20), nullable=True)
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
