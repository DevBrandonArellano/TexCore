"""
Protocol para formateadores de salida (Strategy Pattern).
OCP: agregar formato PDF, JSON, etc. solo requiere nueva clase, no modificar routers.
"""
from typing import Protocol
import pandas as pd
from fastapi.responses import Response


class OutputFormatter(Protocol):
    def format(self, df: pd.DataFrame, filename: str) -> Response:
        """Convierte un DataFrame en una Response HTTP descargable."""
        ...
