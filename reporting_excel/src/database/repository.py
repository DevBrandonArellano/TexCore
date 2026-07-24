"""
AuditRepository de reporting_excel: persiste eventos de auditoría en SQLite.
DIP: IAuditRepository define el contrato; AuditRepository es la implementación concreta.
SRP: única responsabilidad — guardar ReportAuditLog sin propagar excepciones al caller.
LSP: mocks de test son intercambiables con AuditRepository sin romper invariantes.
ISO 27001 A.12.4: trazabilidad de quién solicita qué reporte y con qué resultado.
COBIT MEA01: registro de acceso a información gerencial y ejecutiva.
RFC 5424: todos los logs incluyen SD-ELEMENT con rfc5424_severity explícito.
"""
import logging
from typing import Optional, Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .engine import get_session_factory
from .models import ReportAuditLog

logger = logging.getLogger(__name__)


@runtime_checkable
class IAuditRepository(Protocol):
    """Contrato de auditoría para reporting_excel."""

    async def save(self, record: ReportAuditLog) -> None:
        """Persiste un registro de auditoría. Nunca propaga excepciones."""
        ...


class AuditRepository:
    """
    Implementación SQLite de IAuditRepository.
    SRP: solo persiste; no construye registros ni conoce la lógica de negocio.
    ISO 27001 A.12.4: cada save() es un evento de auditoría de acceso a datos.
    COBIT MEA01: trazabilidad de reportes para evaluación del desempeño.
    """

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
    ) -> None:
        self._session_factory = session_factory or get_session_factory()

    async def save(self, record: ReportAuditLog) -> None:
        try:
            async with self._session_factory() as session:
                session.add(record)
                await session.commit()
            logger.info(
                "Registro de auditoría de reporte guardado",
                extra={"sd": {
                    "rfc5424_severity": 6,
                    "table": ReportAuditLog.__tablename__,
                    "requested_by": record.requested_by,
                    "report_type": record.report_type,
                    "success": str(record.success),
                }},
            )
        except Exception as exc:
            logger.warning(
                "No se pudo persistir el registro de auditoría de reporte",
                extra={"sd": {
                    "rfc5424_severity": 4,
                    "table": ReportAuditLog.__tablename__,
                    "error": str(exc)[:200],
                }},
            )


def build_report_record(
    requested_by: str,
    report_type: str,
    endpoint: str,
    success: bool,
    params_json: Optional[str] = None,
    format: Optional[str] = None,
    error_detail: Optional[str] = None,
) -> ReportAuditLog:
    """Factory function — construye ReportAuditLog. SRP: separa construcción de persistencia."""
    return ReportAuditLog(
        requested_by=requested_by,
        report_type=report_type,
        endpoint=endpoint,
        params_json=params_json,
        format=format,
        success=success,
        error_detail=error_detail,
    )


def get_audit_repo() -> AuditRepository:
    """Dependency provider para FastAPI Depends. DIP: el router no construye el repo."""
    return AuditRepository()
