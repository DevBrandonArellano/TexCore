"""
Implementación pyodbc del repositorio de reportes.
SRP: solo responsable de ejecutar queries y retornar DataFrames.
La cadena de conexión se construye en database.py (configuración separada).
"""
import logging
from typing import Optional, Tuple

import pandas as pd
import pyodbc

from ..database import get_connection_string

logger = logging.getLogger(__name__)


class SqlReportRepository:
    """
    Ejecuta Stored Procedures de SQL Server y retorna DataFrames.
    Incluye el converter de DATETIMEOFFSET para columnas de fecha.
    """

    @staticmethod
    def _handle_datetimeoffset(dto_value) -> str:
        """Converter para el tipo DATETIMEOFFSET de SQL Server (-155 en pyodbc)."""
        try:
            if isinstance(dto_value, (bytes, bytearray)):
                return ""
            return pd.Timestamp(dto_value).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return ""

    def execute_sp(self, sp_query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """
        Ejecuta el SP y retorna DataFrame. Abre y cierra la conexión en cada llamada.

        Args:
            sp_query: Cadena EXEC completa con parámetros '?'.
            params: Valores para los '?' en orden.
        """
        conn_str = get_connection_string()
        try:
            with pyodbc.connect(conn_str) as conn:
                conn.add_output_converter(-155, self._handle_datetimeoffset)
                if params:
                    df = pd.read_sql(sp_query, conn, params=params)
                else:
                    df = pd.read_sql(sp_query, conn)
            return df
        except Exception as exc:
            logger.error("Error ejecutando SP '%s': %s", sp_query, exc)
            raise
