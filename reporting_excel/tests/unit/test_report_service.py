"""
Tests unitarios del ReportService.
Usa mocks de IReportRepository y OutputFormatter para aislar la lógica del servicio.
"""
import pytest
import pandas as pd
from unittest.mock import AsyncMock, MagicMock
from fastapi import Response

from src.services.report_service import ReportService


def _make_repo(df: pd.DataFrame):
    repo = MagicMock()
    repo.execute_sp = AsyncMock(return_value=df)
    return repo


def _make_formatter():
    fmt = MagicMock()
    fmt.format.return_value = Response(content=b"data", media_type="application/octet-stream")
    return fmt


class TestReportService_DFLleno:
    async def test_generate_dado_df_con_datos_cuando_generar_entonces_llama_formatter(self):
        df = pd.DataFrame({"col": [1, 2]})
        service = ReportService(_make_repo(df), _make_formatter())
        fmt = service._formatter
        await service.generate("EXEC sp_Test", None, "reporte")
        fmt.format.assert_called_once()

    async def test_generate_dado_df_con_datos_cuando_generar_entonces_pasa_df_original_al_formatter(self):
        df = pd.DataFrame({"col": [1, 2]})
        fmt = _make_formatter()
        service = ReportService(_make_repo(df), fmt)
        await service.generate("EXEC sp_Test", None, "reporte")
        args = fmt.format.call_args
        assert len(args[0][0]) == 2

    async def test_generate_dado_params_cuando_generar_entonces_los_pasa_al_repositorio(self):
        df = pd.DataFrame({"col": [1]})
        repo = _make_repo(df)
        service = ReportService(repo, _make_formatter())
        await service.generate("EXEC sp_Test", (42,), "reporte")
        repo.execute_sp.assert_called_once_with("EXEC sp_Test", (42,))


class TestReportService_DFVacio:
    async def test_generate_dado_df_vacio_cuando_generar_entonces_pasa_df_con_mensaje(self):
        fmt = _make_formatter()
        service = ReportService(_make_repo(pd.DataFrame()), fmt)
        await service.generate("EXEC sp_Test", None, "reporte")
        args = fmt.format.call_args
        df_pasado = args[0][0]
        assert "mensaje" in df_pasado.columns
        assert len(df_pasado) == 1

    async def test_generate_dado_df_vacio_cuando_generar_entonces_retorna_response(self):
        service = ReportService(_make_repo(pd.DataFrame()), _make_formatter())
        result = await service.generate("EXEC sp_Test", None, "reporte")
        assert result is not None

    async def test_generate_dado_df_vacio_cuando_generar_entonces_mensaje_descriptivo(self):
        fmt = _make_formatter()
        service = ReportService(_make_repo(pd.DataFrame()), fmt)
        await service.generate("EXEC sp_Test", None, "reporte")
        df_pasado = fmt.format.call_args[0][0]
        assert "No se encontraron" in df_pasado["mensaje"].iloc[0]

    async def test_generate_dado_df_vacio_cuando_generar_entonces_marca_header_x_report_empty(self):
        # El frontend (useReportesExport.ts) usa este header para mostrar un
        # toast.warning en vez de toast.success cuando el archivo descargado
        # no trae datos reales — antes el usuario siempre veía "éxito".
        service = ReportService(_make_repo(pd.DataFrame()), _make_formatter())
        result = await service.generate("EXEC sp_Test", None, "reporte")
        assert result.headers["X-Report-Empty"] == "true"


class TestReportService_DFLleno_Header:
    async def test_generate_dado_df_con_datos_cuando_generar_entonces_no_marca_header_x_report_empty(self):
        df = pd.DataFrame({"col": [1, 2]})
        service = ReportService(_make_repo(df), _make_formatter())
        result = await service.generate("EXEC sp_Test", None, "reporte")
        assert "X-Report-Empty" not in result.headers


class TestReportService_Concurrencia:
    # Regresión: generate() debe ser una corutina — si volviera a ser
    # síncrono (o el repo dejara de ser awaited), una llamada bloquearía el
    # único event loop de uvicorn (el Dockerfile no pasa --workers) y
    # congelaría el microservicio completo mientras dura la consulta.
    async def test_generate_dado_llamada_cuando_ejecuta_entonces_es_una_corutina_awaitable(self):
        import inspect

        service = ReportService(_make_repo(pd.DataFrame({"col": [1]})), _make_formatter())
        coro = service.generate("EXEC sp_Test", None, "reporte")
        assert inspect.isawaitable(coro)
        await coro
