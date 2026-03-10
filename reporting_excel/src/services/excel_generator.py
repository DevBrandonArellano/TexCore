import pandas as pd
from io import BytesIO
from datetime import datetime, date
import re


def _solo_ascii(s):
    """Elimina caracteres no imprimibles que causan iconos de error en Excel."""
    if not s or not isinstance(s, str):
        return ''
    return re.sub(r'[^\x20-\x7E\u00C0-\u024F]', '', s)


def _fecha_a_texto(val):
    """Convierte cualquier fecha a texto limpio: dd-mm-yyyy (solo fecha)"""
    if pd.isna(val) or val is None or val == '':
        return ''
    if isinstance(val, (bytes, bytearray)):
        return ''
    try:
        ts = pd.Timestamp(val)
        return ts.strftime('%d-%m-%Y')
    except Exception:
        try:
            s = str(val).strip()
            ts = pd.to_datetime(s)
            return ts.strftime('%d-%m-%Y')
        except Exception:
            return ''


def _prepare_df_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    """Todo a string limpio ASCII. Fechas como dd-mm-yyyy (solo fecha)."""
    df = df.copy()
    for col in df.columns:
        col_lower = str(col).lower()
        if pd.api.types.is_datetime64_any_dtype(df[col]) or col_lower == 'fecha':
            df[col] = df[col].apply(lambda x: _solo_ascii(_fecha_a_texto(x)))
        elif pd.api.types.is_timedelta64_dtype(df[col]):
            df[col] = df[col].apply(lambda x: _solo_ascii(str(x)) if pd.notna(x) else '')
        else:
            df[col] = df[col].apply(lambda x: _solo_ascii(str(x)) if pd.notna(x) else '')
    return df


def dataframe_to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Reporte") -> bytes:
    """Genera Excel con xlsxwriter. Escribe Fecha explícitamente como string ASCII."""
    output = BytesIO()
    df = _prepare_df_for_excel(df)

    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        workbook = writer.book
        worksheet = writer.sheets[sheet_name]

        header_fmt = workbook.add_format({
            'bold': True,
            'bg_color': '#333333',
            'font_color': 'white',
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
        })

        for col_idx in range(len(df.columns)):
            worksheet.write(0, col_idx, str(df.columns[col_idx]), header_fmt)

        # Sobrescribir Fecha con write_string para evitar caracteres raros
        for col_idx, col_name in enumerate(df.columns):
            if str(col_name).lower() == 'fecha':
                for row_idx in range(len(df)):
                    val = df.iloc[row_idx][col_name]
                    txt = str(val).strip() if val and pd.notna(val) else ''
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
