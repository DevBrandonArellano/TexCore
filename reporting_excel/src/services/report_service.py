"""
ReportService: formatea los datos de un reporte a Excel/CSV.
SRP: solo coordina el caso de datos vacíos y el formateo de salida.
DIP: depende de OutputFormatter (abstracción), no de una implementación concreta.

Nota (auditoría de performance 2026-08-31): este servicio ya no consulta los
datos él mismo — el backend Django ya se los manda resueltos (ver
inventory/reporting_proxy.py y src/routers/generate.py). Antes dependía de un
IReportRepository que llamaba de vuelta a Django por HTTP; se eliminó junto
con el DSL "SP" y los routers por-reporte que ya no usa el tráfico real.
"""
import logging
from typing import Optional

import pandas as pd
from fastapi import Response

from ..formatters.base import OutputFormatter

logger = logging.getLogger(__name__)

_EMPTY_MESSAGE = "No se encontraron datos para los parámetros seleccionados."


class ReportService:
    """Recibe los datos ya resueltos y delega el formateo al OutputFormatter."""

    def __init__(self, formatter: OutputFormatter) -> None:
        self._formatter = formatter

    async def generate_from_rows(self, rows: Optional[list], filename: str) -> Response:
        """
        Formatea `rows` (lista de dicts) a Excel/CSV.
        Si está vacío, devuelve un archivo con fila de mensaje (nunca 404) y
        marca el header X-Report-Empty.
        """
        df = pd.DataFrame(rows) if rows else pd.DataFrame()
        was_empty = df.empty

        if was_empty:
            logger.info("Reporte sin datos: %s", filename)
            df = pd.DataFrame([{"mensaje": _EMPTY_MESSAGE}])

        response = self._formatter.format(df, filename)
        if was_empty:
            response.headers["X-Report-Empty"] = "true"
        return response
