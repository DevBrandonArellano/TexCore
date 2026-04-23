"""Formateador de salida CSV."""
import pandas as pd
from fastapi import Response


class CsvFormatter:
    """Convierte DataFrames a archivos .csv descargables."""

    def format(self, df: pd.DataFrame, filename: str) -> Response:
        csv_data = df.to_csv(index=False)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"},
        )
