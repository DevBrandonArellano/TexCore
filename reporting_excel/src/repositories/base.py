"""
Protocolo del repositorio de reportes.
LSP/DIP: permite sustituir la implementación pyodbc por una en memoria para tests.
"""
from typing import Optional, Protocol, Tuple, runtime_checkable
import pandas as pd


@runtime_checkable
class IReportRepository(Protocol):
    async def execute_sp(self, sp_query: str, params: Optional[Tuple] = None) -> pd.DataFrame:
        """
        Ejecuta un stored procedure y retorna un DataFrame.
        sp_query: la cadena EXEC completa (ej: "EXEC sp_GetKardexBodega @BodegaID=?, ...")
        params: tupla de parámetros posicionales para los '?' en sp_query.
        """
        ...
