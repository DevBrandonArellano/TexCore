"""
Tests unitarios para src/services/excel_generator.py.
Cubre las funciones de utilidad de generación Excel.
"""
import pytest
import pandas as pd
from datetime import date

from src.services.excel_generator import (
    _solo_ascii,
    _fecha_a_texto,
    _prepare_df_for_excel,
    dataframe_to_excel_bytes,
)


class TestSoloAscii:

    def test_dado_string_ascii_cuando_limpia_entonces_retorna_igual(self):
        assert _solo_ascii("Hola Mundo") == "Hola Mundo"

    def test_dado_string_con_caracteres_especiales_cuando_limpia_entonces_los_elimina(self):
        result = _solo_ascii("Texto\x00con\x01control")
        assert "\x00" not in result
        assert "\x01" not in result

    def test_dado_none_cuando_limpia_entonces_retorna_vacio(self):
        assert _solo_ascii(None) == ""

    def test_dado_string_vacio_cuando_limpia_entonces_retorna_vacio(self):
        assert _solo_ascii("") == ""

    def test_dado_numero_cuando_limpia_entonces_retorna_vacio(self):
        assert _solo_ascii(123) == ""

    def test_dado_string_con_tildes_cuando_limpia_entonces_los_mantiene(self):
        result = _solo_ascii("producción")
        assert "producci" in result


class TestFechaATexto:

    def test_dado_fecha_date_cuando_convierte_entonces_formato_correcto(self):
        result = _fecha_a_texto(date(2026, 3, 15))
        assert result == "15-03-2026"

    def test_dado_string_fecha_cuando_convierte_entonces_formato_correcto(self):
        result = _fecha_a_texto("2026-03-15")
        assert result == "15-03-2026"

    def test_dado_none_cuando_convierte_entonces_retorna_vacio(self):
        assert _fecha_a_texto(None) == ""

    def test_dado_string_vacio_cuando_convierte_entonces_retorna_vacio(self):
        assert _fecha_a_texto("") == ""

    def test_dado_bytes_cuando_convierte_entonces_retorna_vacio(self):
        assert _fecha_a_texto(b"2026-03-15") == ""

    def test_dado_nan_cuando_convierte_entonces_retorna_vacio(self):
        assert _fecha_a_texto(float("nan")) == ""

    def test_dado_timestamp_cuando_convierte_entonces_formato_correcto(self):
        ts = pd.Timestamp("2026-06-01")
        result = _fecha_a_texto(ts)
        assert result == "01-06-2026"


class TestPrepareDfForExcel:

    def test_dado_df_con_columna_numerica_cuando_prepara_entonces_redondea(self):
        df = pd.DataFrame({"precio": [1.23456, 7.89012]})
        result = _prepare_df_for_excel(df)
        assert result["precio"].iloc[0] == pytest.approx(1.235, abs=1e-3)

    def test_dado_df_con_columna_fecha_cuando_prepara_entonces_convierte_a_texto(self):
        df = pd.DataFrame({"fecha": ["2026-03-15", "2026-06-01"]})
        result = _prepare_df_for_excel(df)
        assert result["fecha"].iloc[0] == "15-03-2026"

    def test_dado_df_con_columna_texto_cuando_prepara_entonces_mantiene_texto(self):
        df = pd.DataFrame({"nombre": ["Empresa A", "Empresa B"]})
        result = _prepare_df_for_excel(df)
        assert result["nombre"].iloc[0] == "Empresa A"

    def test_dado_df_con_nulos_cuando_prepara_entonces_convierte_a_vacio(self):
        df = pd.DataFrame({"nombre": [None, "Empresa B"]})
        result = _prepare_df_for_excel(df)
        assert result["nombre"].iloc[0] == ""

    def test_dado_df_vacio_cuando_prepara_entonces_retorna_df_vacio(self):
        df = pd.DataFrame()
        result = _prepare_df_for_excel(df)
        assert result.empty


class TestDataframeToExcelBytes:

    def test_dado_df_simple_cuando_genera_entonces_retorna_bytes_xlsx(self):
        df = pd.DataFrame({"id": [1, 2], "nombre": ["A", "B"]})
        result = dataframe_to_excel_bytes(df)
        assert isinstance(result, bytes)
        assert result[:4] == b"PK\x03\x04"

    def test_dado_df_vacio_cuando_genera_entonces_retorna_bytes_xlsx(self):
        df = pd.DataFrame()
        result = dataframe_to_excel_bytes(df)
        assert isinstance(result, bytes)
        assert result[:4] == b"PK\x03\x04"

    def test_dado_df_con_columna_fecha_cuando_genera_entonces_retorna_xlsx(self):
        df = pd.DataFrame({
            "fecha": ["2026-03-15", "2026-06-01"],
            "valor": [100.0, 200.0],
        })
        result = dataframe_to_excel_bytes(df, sheet_name="Ventas")
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_dado_sheet_name_personalizado_cuando_genera_entonces_retorna_xlsx(self):
        df = pd.DataFrame({"col": [1]})
        result = dataframe_to_excel_bytes(df, sheet_name="MiHoja")
        assert isinstance(result, bytes)
        assert result[:4] == b"PK\x03\x04"
