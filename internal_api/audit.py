"""
AuditLogger: registra accesos de servicios internos.
ISO 27001 A.12.4 — Registro de eventos.
RFC 5424: niveles de severidad en logs estructurados.
SRP: única responsabilidad — registrar eventos de audit.
"""
import logging
from typing import Optional

logger = logging.getLogger("internal_api.audit")


class AuditLogger:
    """
    Registra en log estructurado (RFC 5424) cada acceso a la API interna
    con identidad de servicio, recurso y duración.

    Mapeo RFC 5424:
      INFO    (6) → acceso exitoso (status < 400)
      WARNING (4) → error cliente (status 4xx)
      ERROR   (3) → error servidor (status 5xx)
    """

    @staticmethod
    def log(
        service: str,
        action: str,
        resource: str,
        status_code: int = 200,
        duration_ms: Optional[int] = None,
        extra: Optional[dict] = None,
    ) -> None:
        """
        Emite log estructurado para trazabilidad ISO 27001 A.12.4.

        Args:
            service:     Nombre del servicio (ej: 'scanning_service')
            action:      Acción realizada (ej: 'validate_lote')
            resource:    Recurso accedido (ej: 'LOT-2026-001' o 'reports')
            status_code: Código HTTP de respuesta
            duration_ms: Duración en milisegundos (opcional)
            extra:       Datos adicionales para el SD (opcional)
        """
        sd: dict = {
            "service": service,
            "action": action,
            "resource": resource,
            "status_code": status_code,
        }
        if duration_ms is not None:
            sd["duration_ms"] = duration_ms
        if extra:
            sd.update(extra)

        if status_code < 400:
            severity = logging.INFO
            rfc_severity = 6
        elif status_code < 500:
            severity = logging.WARNING
            rfc_severity = 4
        else:
            severity = logging.ERROR
            rfc_severity = 3

        sd["rfc5424_severity"] = rfc_severity

        logger.log(
            severity,
            "[AUDIT] %s → %s on %s [%d]",
            service,
            action,
            resource,
            status_code,
            extra={"sd": sd},
        )
