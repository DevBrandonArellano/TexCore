"""
ReportService: orquesta el repositorio con el formateador.
SRP: solo coordina la obtención de datos y su formato de salida.
DIP: depende de abstracciones (IReportRepository, OutputFormatter), no de implementaciones.
"""
import logging
from typing import Optional, Tuple

import pandas as pd
from fastapi import Response

from ..repositories.base import IReportRepository
from ..formatters.base import OutputFormatter

logger = logging.getLogger(__name__)

_EMPTY_MESSAGE = "No se encontraron datos para los parámetros seleccionados."


class ReportService:
    """
    Servicio que ejecuta un SP, maneja el caso de DataFrame vacío,
    y delega el formateo al OutputFormatter correspondiente.
    """

    def __init__(
        self,
        repository: IReportRepository,
        formatter: OutputFormatter,
    ) -> None:
        self._repo = repository
        self._formatter = formatter

    async def generate(
        self,
        sp_query: str,
        params: Optional[Tuple],
        filename: str,
    ) -> Response:
        """
        Ejecuta el SP y retorna la Response formateada.
        Si el DataFrame está vacío devuelve un archivo con fila de mensaje (nunca 404).
        """
        df = await self._repo.execute_sp(sp_query, params)
        was_empty = df.empty

        if was_empty:
            logger.info("SP retornó DataFrame vacío: %s", sp_query)
            df = pd.DataFrame([{"mensaje": _EMPTY_MESSAGE}])

        response = self._formatter.format(df, filename)
        if was_empty:
            response.headers["X-Report-Empty"] = "true"
        return response
