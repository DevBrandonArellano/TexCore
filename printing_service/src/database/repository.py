"""
AuditRepository de printing_service: persiste eventos de auditoría en SQLite.
DIP: IAuditRepository define el contrato; AuditRepository es la implementación concreta.
SRP: única responsabilidad — guardar PrintAuditLog sin propagar excepciones al caller.
LSP: mocks de test son intercambiables con AuditRepository sin romper invariantes.
ISO 27001 A.12.4: trazabilidad de generación de documentos para auditoría de seguridad.
RFC 5424: todos los logs incluyen SD-ELEMENT con rfc5424_severity explícito.
"""
import logging
from typing import Optional, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .engine import get_session_factory
from .models import PrintAuditLog

logger = logging.getLogger(__name__)


@runtime_checkable
class IAuditRepository(Protocol):
    """Contrato de auditoría para printing_service."""

    async def save(self, record: PrintAuditLog) -> None:
        """Persiste un registro de auditoría. Nunca propaga excepciones."""
        ...


class AuditRepository:
    """
    Implementación SQLite de IAuditRepository.
    SRP: solo persiste; no construye registros ni conoce la lógica de negocio.
    ISO 27001 A.12.4: cada save() representa un evento de auditoría trazable.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()

    async def save(self, record: PrintAuditLog) -> None:
        try:
            async with self._session_factory() as session:
                session.add(record)
                await session.commit()
            logger.info(
                "Registro de auditoría de impresión guardado",
                extra={"sd": {
                    "rfc5424_severity": 6,
                    "table": PrintAuditLog.__tablename__,
                    "document_type": record.document_type,
                    "success": str(record.success),
                }},
            )
        except Exception as exc:
            logger.warning(
                "No se pudo persistir el registro de auditoría de impresión",
                extra={"sd": {
                    "rfc5424_severity": 4,
                    "table": PrintAuditLog.__tablename__,
                    "error": str(exc)[:200],
                }},
            )


def build_print_record(
    document_type: str,
    template_used: str,
    success: bool,
    pedido_id: Optional[int] = None,
    guia_remision: Optional[str] = None,
    lote_codigo: Optional[str] = None,
    error_detail: Optional[str] = None,
) -> PrintAuditLog:
    """Factory function — construye PrintAuditLog. SRP: separa construcción de persistencia."""
    return PrintAuditLog(
        document_type=document_type,
        template_used=template_used,
        pedido_id=pedido_id,
        guia_remision=guia_remision,
        lote_codigo=lote_codigo,
        success=success,
        error_detail=error_detail,
    )


def get_audit_repo() -> AuditRepository:
    """Dependency provider para FastAPI Depends. DIP: el router no construye el repo."""
    return AuditRepository()
