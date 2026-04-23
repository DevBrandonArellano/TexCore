"""
Tests unitarios del ReportService.
Usa mocks de IReportRepository y OutputFormatter para aislar la lógica del servicio.
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock
from fastapi import Response

from src.services.report_service import ReportService


def _make_repo(df: pd.DataFrame):
    repo = MagicMock()
    repo.execute_sp.return_value = df
    return repo


def _make_formatter():
    fmt = MagicMock()
    fmt.format.return_value = Response(content=b"data", media_type="application/octet-stream")
    return fmt


class TestReportService_DFLleno:
    def test_generate_dado_df_con_datos_cuando_generar_entonces_llama_formatter(self):
        df = pd.DataFrame({"col": [1, 2]})
        service = ReportService(_make_repo(df), _make_formatter())
        fmt = service._formatter
        service.generate("EXEC sp_Test", None, "reporte")
        fmt.format.assert_called_once()

    def test_generate_dado_df_con_datos_cuando_generar_entonces_pasa_df_original_al_formatter(self):
        df = pd.DataFrame({"col": [1, 2]})
        fmt = _make_formatter()
        service = ReportService(_make_repo(df), fmt)
        service.generate("EXEC sp_Test", None, "reporte")
        args = fmt.format.call_args
        assert len(args[0][0]) == 2

    def test_generate_dado_params_cuando_generar_entonces_los_pasa_al_repositorio(self):
        df = pd.DataFrame({"col": [1]})
        repo = _make_repo(df)
        service = ReportService(repo, _make_formatter())
        service.generate("EXEC sp_Test", (42,), "reporte")
        repo.execute_sp.assert_called_once_with("EXEC sp_Test", (42,))


class TestReportService_DFVacio:
    def test_generate_dado_df_vacio_cuando_generar_entonces_pasa_df_con_mensaje(self):
        fmt = _make_formatter()
        service = ReportService(_make_repo(pd.DataFrame()), fmt)
        service.generate("EXEC sp_Test", None, "reporte")
        args = fmt.format.call_args
        df_pasado = args[0][0]
        assert "mensaje" in df_pasado.columns
        assert len(df_pasado) == 1

    def test_generate_dado_df_vacio_cuando_generar_entonces_retorna_response(self):
        service = ReportService(_make_repo(pd.DataFrame()), _make_formatter())
        result = service.generate("EXEC sp_Test", None, "reporte")
        assert result is not None

    def test_generate_dado_df_vacio_cuando_generar_entonces_mensaje_descriptivo(self):
        fmt = _make_formatter()
        service = ReportService(_make_repo(pd.DataFrame()), fmt)
        service.generate("EXEC sp_Test", None, "reporte")
        df_pasado = fmt.format.call_args[0][0]
        assert "No se encontraron" in df_pasado["mensaje"].iloc[0]
