"""
RFC 5424 Syslog Formatter — TexCore Backend (Django)
=====================================================
Implementa el estándar IETF RFC 5424 (The Syslog Protocol) para todos
los loggers del backend Django.

Formato de mensaje:
    <PRI>1 TIMESTAMP HOSTNAME APP-NAME PROCID MSGID [SD-ELEMENT] MSG

    PRI        = Facility × 8 + Severity
    Facility   = 16  (local0) — reservado para el backend Django principal
    Severity   = mapeado desde niveles estándar de Python logging
    SD-ELEMENT = [texcore@32473 key="value" ...]
                  └── SD-ID fijo para todo el ecosistema TexCore

Uso con extra structured data:
    logger.info("Orden creada", extra={'sd': {'entity': 'OrdenProduccion', 'id': '42'}})
"""

from __future__ import annotations

import logging
import os
import socket
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constantes de protocolo
# ---------------------------------------------------------------------------

# Private Enterprise Number placeholder (IANA not registered — uso interno)
SD_ID = "texcore@32473"

# Facility 16 = local0 → backend Django principal
_FACILITY_DJANGO = 16

# Mapeo de niveles Python → severidades RFC 5424
_SEVERITY: dict[int, int] = {
    logging.CRITICAL: 2,  # CRIT         — condición crítica
    logging.ERROR:    3,  # ERROR         — error en operación
    logging.WARNING:  4,  # WARNING       — condición de advertencia
    logging.INFO:     6,  # INFORMATIONAL — mensaje informativo
    logging.DEBUG:    7,  # DEBUG         — mensaje de debug
}
_SEVERITY_DEFAULT = 5    # NOTICE — para niveles no mapeados

# Valores de cabecera resueltos una sola vez al importar el módulo
_HOSTNAME: str = socket.gethostname()[:255]
_PROCID: str = str(os.getpid())


# ---------------------------------------------------------------------------
# Formatter principal
# ---------------------------------------------------------------------------

class RFC5424Formatter(logging.Formatter):
    """
    Formatter RFC 5424 para Django/Python logging.

    Produce una línea por registro con el formato Syslog estándar.
    Compatible con rsyslog, syslog-ng, Elastic Stack, Loki y cualquier
    agente que consuma syslog estructurado.

    Args:
        facility: Código de facilidad RFC 5424 (default 16 = local0).
        app_name: Nombre de la aplicación en la cabecera (default: env APP_NAME).
    """

    def __init__(
        self,
        facility: int = _FACILITY_DJANGO,
        app_name: str | None = None,
    ) -> None:
        super().__init__()
        self._facility = facility
        self._app_name = (
            app_name
            or os.environ.get("APP_NAME", "texcore-backend")
        )[:48]  # RFC 5424 §6.2.5 — max 48 chars

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def format(self, record: logging.LogRecord) -> str:
        """Formatea un LogRecord como mensaje RFC 5424 completo."""
        pri = self._priority(record.levelno)
        timestamp = self._timestamp(record.created)
        msgid = self._msgid(record.name)
        sd = self._structured_data(record)
        msg = self._message(record)

        return (
            f"<{pri}>1 {timestamp} {_HOSTNAME} {self._app_name} "
            f"{_PROCID} {msgid} {sd} {msg}"
        )

    # ------------------------------------------------------------------
    # Métodos privados
    # ------------------------------------------------------------------

    def _priority(self, levelno: int) -> int:
        """PRI = Facility × 8 + Severity."""
        severity = _SEVERITY.get(levelno, _SEVERITY_DEFAULT)
        return self._facility * 8 + severity

    @staticmethod
    def _timestamp(created: float) -> str:
        """ISO 8601 UTC con precisión de milisegundos — RFC 5424 §6.2.3."""
        dt = datetime.fromtimestamp(created, tz=timezone.utc)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"

    @staticmethod
    def _msgid(logger_name: str) -> str:
        """
        MSGID derivado del nombre del logger.
        RFC 5424 §6.2.7 — max 32 chars, solo US-ASCII imprimibles, sin espacios.
        """
        return logger_name.replace(".", "-")[:32] or "-"

    def _structured_data(self, record: logging.LogRecord) -> str:
        """
        Construye el campo STRUCTURED-DATA.
        Incluye siempre module y lineno; mezcla record.sd si existe.
        """
        params: dict[str, str] = {
            "module": record.module,
            "line": str(record.lineno),
            "level": record.levelname,
        }
        extra_sd = getattr(record, "sd", None)
        if isinstance(extra_sd, dict):
            params.update({k: str(v) for k, v in extra_sd.items()})

        return self._build_sd(params)

    def _build_sd(self, params: dict[str, str]) -> str:
        """
        Construye un SD-ELEMENT RFC 5424 §6.3:
            [SD-ID PARAM-NAME="PARAM-VALUE" ...]
        Devuelve '-' (NILVALUE) si no hay parámetros.
        """
        if not params:
            return "-"
        parts = [f'{k}="{self._escape(v)}"' for k, v in params.items()]
        return f"[{SD_ID} {' '.join(parts)}]"

    @staticmethod
    def _escape(value: str) -> str:
        """
        Escaping obligatorio de valores SD-PARAM — RFC 5424 §6.3.3.
        Los tres caracteres que deben escaparse: \\ → \\\\ | " → \\" | ] → \\]
        """
        return value.replace("\\", "\\\\").replace('"', '\\"').replace("]", "\\]")

    @staticmethod
    def _message(record: logging.LogRecord) -> str:
        """Mensaje principal + excepción si aplica."""
        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + logging.Formatter().formatException(record.exc_info)
        return msg
