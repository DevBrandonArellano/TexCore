"""
AuditRepository de scanning_service: persiste eventos de auditoría en SQLite.
DIP: IAuditRepository define el contrato; AuditRepository es la implementación concreta.
SRP: única responsabilidad — guardar ScanAuditLog sin propagar excepciones al caller.
LSP: cualquier implementación de IAuditRepository es intercambiable en tests.
ISO 27001 A.12.4: trazabilidad de eventos de escaneo para auditoría de seguridad.
RFC 5424: todos los logs incluyen SD-ELEMENT con rfc5424_severity explícito.
"""
import logging
from typing import Protocol, runtime_checkable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..schemas.validate import ValidateResponse
from .engine import get_session_factory
from .models import ScanAuditLog

logger = logging.getLogger(__name__)


@runtime_checkable
class IAuditRepository(Protocol):
    """
    Contrato de auditoría para scanning_service.
    LSP: DjangoApiClient y mocks de test son intercambiables sin romper invariantes.
    """

    async def save(self, record: ScanAuditLog) -> None:
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

    async def save(self, record: ScanAuditLog) -> None:
        try:
            async with self._session_factory() as session:
                session.add(record)
                await session.commit()
            logger.info(
                "Registro de auditoría de escaneo guardado",
                extra={"sd": {
                    "rfc5424_severity": 6,
                    "table": ScanAuditLog.__tablename__,
                    "valid": str(record.valid),
                }},
            )
        except Exception as exc:
            logger.warning(
                "No se pudo persistir el registro de auditoría de escaneo",
                extra={"sd": {
                    "rfc5424_severity": 4,
                    "table": ScanAuditLog.__tablename__,
                    "error": str(exc)[:200],
                }},
            )


def build_scan_record(codigo: str, response: ValidateResponse) -> ScanAuditLog:
    """
    Factory function — construye ScanAuditLog desde los datos del dominio.
    SRP: separa la construcción del modelo de la persistencia.
    """
    lote = response.lote
    return ScanAuditLog(
        codigo_scanned=codigo,
        valid=response.valid,
        reason=response.reason,
        lote_codigo=lote.codigo if lote else None,
        producto_id=lote.producto_id if lote else None,
        producto_nombre=lote.producto_nombre if lote else None,
        bodega_id=lote.bodega_id if lote else None,
        bodega_nombre=lote.bodega_nombre if lote else None,
        peso_kg=lote.peso if lote else None,
    )


def get_audit_repo() -> AuditRepository:
    """Dependency provider para FastAPI Depends. DIP: el router no construye el repo."""
    return AuditRepository()
