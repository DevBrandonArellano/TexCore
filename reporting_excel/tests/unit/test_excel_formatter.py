"""Tests unitarios del ExcelFormatter. Sin BD, sin HTTP."""
import pytest
import pandas as pd
from src.formatters.excel_formatter import ExcelFormatter, _prepare_df, _fecha_a_texto


class TestFechaATexto:
    def test_fecha_a_texto_dado_none_cuando_convertir_entonces_retorna_vacio(self):
        assert _fecha_a_texto(None) == ""

    def test_fecha_a_texto_dado_bytes_cuando_convertir_entonces_retorna_vacio(self):
        assert _fecha_a_texto(b"2026-01-01") == ""

    def test_fecha_a_texto_dado_fecha_valida_cuando_convertir_entonces_retorna_ddmmyyyy(self):
        result = _fecha_a_texto(pd.Timestamp("2026-01-15"))
        assert result == "15-01-2026"

    def test_fecha_a_texto_dado_string_fecha_cuando_convertir_entonces_parsea(self):
        result = _fecha_a_texto("2026-06-20 10:30:00")
        assert result == "20-06-2026"


class TestPrepareDF:
    def test_prepare_df_dado_columna_numerica_cuando_preparar_entonces_redondea_3_decimales(self):
        df = pd.DataFrame({"precio": [1.23456]})
        result = _prepare_df(df)
        assert result["precio"].iloc[0] == pytest.approx(1.235)

    def test_prepare_df_dado_columna_fecha_cuando_preparar_entonces_convierte_a_texto(self):
        df = pd.DataFrame({"fecha": [pd.Timestamp("2026-01-15")]})
        result = _prepare_df(df)
        assert result["fecha"].iloc[0] == "15-01-2026"

    def test_prepare_df_dado_columna_texto_cuando_preparar_entonces_es_string(self):
        df = pd.DataFrame({"nombre": ["Ana"]})
        result = _prepare_df(df)
        assert result["nombre"].iloc[0] == "Ana"


class TestExcelFormatter:
    def test_format_dado_dataframe_valido_cuando_formatear_entonces_retorna_200(self):
        df = pd.DataFrame({"col1": ["dato1"], "col2": [42.0]})
        formatter = ExcelFormatter()
        response = formatter.format(df, "test_reporte")
        assert response.status_code == 200

    def test_format_dado_dataframe_valido_cuando_formatear_entonces_magic_bytes_xlsx(self):
        df = pd.DataFrame({"col1": ["dato1"], "col2": [42.0]})
        formatter = ExcelFormatter()
        response = formatter.format(df, "test_reporte")
        assert response.body[:4] == b"PK\x03\x04"

    def test_format_dado_filename_cuando_formatear_entonces_content_disposition_correcto(self):
        df = pd.DataFrame({"col": ["val"]})
        formatter = ExcelFormatter()
        response = formatter.format(df, "mi_reporte")
        assert "mi_reporte.xlsx" in response.headers["content-disposition"]

    def test_format_dado_dataframe_vacio_cuando_formatear_entonces_no_lanza_excepcion(self):
        df = pd.DataFrame()
        formatter = ExcelFormatter()
        response = formatter.format(df, "reporte_vacio")
        assert response.status_code == 200
