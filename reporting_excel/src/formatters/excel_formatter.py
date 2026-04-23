"""
Formateador de salida Excel.
Extrae la lógica de excel_generator.py y la encapsula en el patrón Strategy.
SRP: solo responsable de convertir DataFrames a archivos Excel descargables.
"""
import re
from io import BytesIO

import pandas as pd
from fastapi import Response

EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _solo_ascii(s) -> str:
    if not s or not isinstance(s, str):
        return ""
    return re.sub(r"[^\x20-\x7EÀ-ɏ]", "", s)


def _fecha_a_texto(val) -> str:
    if pd.isna(val) or val is None or val == "":
        return ""
    if isinstance(val, (bytes, bytearray)):
        return ""
    try:
        return pd.Timestamp(val).strftime("%d-%m-%Y")
    except Exception:
        try:
            return pd.to_datetime(str(val).strip()).strftime("%d-%m-%Y")
        except Exception:
            return ""


def _prepare_df(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza el DataFrame para escritura Excel: fechas como texto, numéricos redondeados."""
    df = df.copy()
    for col in df.columns:
        col_lower = str(col).lower()
        if pd.api.types.is_datetime64_any_dtype(df[col]) or col_lower == "fecha":
            df[col] = df[col].apply(lambda x: _solo_ascii(_fecha_a_texto(x)))
        elif pd.api.types.is_numeric_dtype(df[col]):
            df[col] = df[col].astype(float).round(3)
        else:
            df[col] = df[col].apply(lambda x: _solo_ascii(str(x)) if pd.notna(x) else "")
    return df


class ExcelFormatter:
    """Convierte DataFrames a archivos .xlsx descargables con formato TexCore."""

    def __init__(self, sheet_name: str = "Reporte") -> None:
        self._sheet_name = sheet_name

    def _to_bytes(self, df: pd.DataFrame) -> bytes:
        output = BytesIO()
        df = _prepare_df(df)
        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            df.to_excel(writer, sheet_name=self._sheet_name, index=False)
            workbook = writer.book
            worksheet = writer.sheets[self._sheet_name]
            header_fmt = workbook.add_format({
                "bold": True, "bg_color": "#333333", "font_color": "white",
                "align": "center", "valign": "vcenter", "border": 1,
            })
            for col_idx in range(len(df.columns)):
                worksheet.write(0, col_idx, str(df.columns[col_idx]), header_fmt)
            for col_idx, col_name in enumerate(df.columns):
                if str(col_name).lower() == "fecha":
                    for row_idx in range(len(df)):
                        val = df.iloc[row_idx][col_name]
                        txt = str(val).strip() if val and pd.notna(val) else ""
                        worksheet.write_string(row_idx + 1, col_idx, txt)
                    break
            for col_idx, col_name in enumerate(df.columns):
                try:
                    col_max = df[col_name].astype(str).str.len().max()
                except Exception:
                    col_max = 0
                max_len = max(col_max if len(df) > 0 else 0, len(str(col_name)))
                worksheet.set_column(col_idx, col_idx, min(max_len + 2, 50))
        return output.getvalue()

    def format(self, df: pd.DataFrame, filename: str) -> Response:
        """Retorna Response HTTP con el archivo Excel como adjunto."""
        return Response(
            content=self._to_bytes(df),
            media_type=EXCEL_MEDIA_TYPE,
            headers={
                "Content-Disposition": f"attachment; filename={filename}.xlsx",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
