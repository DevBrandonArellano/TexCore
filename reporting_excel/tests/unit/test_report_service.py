"""
Tests unitarios del ReportService.
Usa un mock de OutputFormatter para aislar la lógica del servicio — ya no
depende de un repositorio (ver auditoría de performance 2026-08-31: el
backend Django manda los datos ya resueltos, este servicio solo formatea).
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock
from fastapi import Response

from src.services.report_service import ReportService


def _make_formatter():
    fmt = MagicMock()
    fmt.format.return_value = Response(content=b"data", media_type="application/octet-stream")
    return fmt


class TestReportService_DFLleno:
    async def test_generate_dado_rows_con_datos_cuando_generar_entonces_llama_formatter(self):
        service = ReportService(_make_formatter())
        fmt = service._formatter
        await service.generate_from_rows([{"col": 1}, {"col": 2}], "reporte")
        fmt.format.assert_called_once()

    async def test_generate_dado_rows_con_datos_cuando_generar_entonces_pasa_df_correcto_al_formatter(self):
        fmt = _make_formatter()
        service = ReportService(fmt)
        await service.generate_from_rows([{"col": 1}, {"col": 2}], "reporte")
        args = fmt.format.call_args
        assert len(args[0][0]) == 2


class TestReportService_DFVacio:
    async def test_generate_dado_rows_none_cuando_generar_entonces_pasa_df_con_mensaje(self):
        fmt = _make_formatter()
        service = ReportService(fmt)
        await service.generate_from_rows(None, "reporte")
        args = fmt.format.call_args
        df_pasado = args[0][0]
        assert "mensaje" in df_pasado.columns
        assert len(df_pasado) == 1

    async def test_generate_dado_rows_vacio_cuando_generar_entonces_retorna_response(self):
        service = ReportService(_make_formatter())
        result = await service.generate_from_rows([], "reporte")
        assert result is not None

    async def test_generate_dado_rows_vacio_cuando_generar_entonces_mensaje_descriptivo(self):
        fmt = _make_formatter()
        service = ReportService(fmt)
        await service.generate_from_rows([], "reporte")
        df_pasado = fmt.format.call_args[0][0]
        assert "No se encontraron" in df_pasado["mensaje"].iloc[0]

    async def test_generate_dado_rows_vacio_cuando_generar_entonces_marca_header_x_report_empty(self):
        # El frontend (useReportesExport.ts) usa este header para mostrar un
        # toast.warning en vez de toast.success cuando el archivo descargado
        # no trae datos reales — antes el usuario siempre veía "éxito".
        service = ReportService(_make_formatter())
        result = await service.generate_from_rows([], "reporte")
        assert result.headers["X-Report-Empty"] == "true"


class TestReportService_DFLleno_Header:
    async def test_generate_dado_rows_con_datos_cuando_generar_entonces_no_marca_header_x_report_empty(self):
        service = ReportService(_make_formatter())
        result = await service.generate_from_rows([{"col": 1}, {"col": 2}], "reporte")
        assert "X-Report-Empty" not in result.headers


class TestReportService_Concurrencia:
    # Regresión: generate_from_rows() debe ser una corutina — si volviera a
    # ser síncrono, una llamada bloquearía el único event loop de uvicorn (el
    # Dockerfile no pasa --workers) y congelaría el microservicio completo.
    async def test_generate_dado_llamada_cuando_ejecuta_entonces_es_una_corutina_awaitable(self):
        import inspect

        service = ReportService(_make_formatter())
        coro = service.generate_from_rows([{"col": 1}], "reporte")
        assert inspect.isawaitable(coro)
        await coro
