"""Tests para DjangoReportRepository. EP por endpoint representativo."""
from unittest.mock import AsyncMock, MagicMock

import httpx
import pandas as pd
import pytest


KARDEX_URL = "http://backend:8000/api/internal/v1/reports/kardex/"
PRODUCTOS_URL = "http://backend:8000/api/internal/v1/reports/productos/"
STOCK_ACTUAL_URL = "http://backend:8000/api/internal/v1/reports/stock-actual/"
AGING_URL = "http://backend:8000/api/internal/v1/reports/aging/"


@pytest.fixture
def mock_token_manager():
    mgr = MagicMock()
    mgr.get_valid_token = AsyncMock(return_value="mock-token")
    return mgr


class TestDjangoReportRepository:

    # EP: API disponible → retorna DataFrame con datos
    async def test_execute_sp_dado_kardex_disponible_cuando_ejecuta_entonces_retorna_dataframe(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoReportRepository

        respx_mock.get(KARDEX_URL).mock(
            return_value=httpx.Response(
                200,
                json=[
                    {
                        "id": 1,
                        "fecha": "2026-05-01",
                        "tipo_movimiento": "COMPRA",
                        "producto_descripcion": "Hilo",
                        "cantidad": "100.00",
                    }
                ],
            )
        )
        repo = DjangoReportRepository(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        df = await repo.execute_sp(
            "EXEC sp_GetKardexBodega @BodegaID=?, @ProductoID=?, @FechaInicio=?, @FechaFin=?, @ProveedorID=?, @LoteCodigo=?",
            (1, None, None, None, None, None),
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "producto_descripcion" in df.columns

    # EP: API retorna lista vacía → DataFrame vacío (no error)
    async def test_execute_sp_dado_sin_datos_cuando_ejecuta_entonces_retorna_dataframe_vacio(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoReportRepository

        respx_mock.get(PRODUCTOS_URL).mock(
            return_value=httpx.Response(200, json=[])
        )
        repo = DjangoReportRepository(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        df = await repo.execute_sp("EXEC sp_GetProductosCatalogo", None)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    # EP: SP no mapeado → ValueError
    async def test_execute_sp_dado_sp_desconocido_cuando_ejecuta_entonces_lanza_error(
        self, mock_token_manager
    ):
        from src.infrastructure.django_client import DjangoReportRepository

        repo = DjangoReportRepository(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        with pytest.raises(ValueError, match="SP no mapeado"):
            await repo.execute_sp("EXEC sp_NoExiste", None)

    # Regresión: exports.py arma la tupla de sp_GetStockActualBodega como
    # (bodega_id, producto_id) — 2 elementos, porque @SedeID=NULL es literal
    # en el SQL, no un placeholder. Si _SP_MAPPING declarara "sede_id" como
    # segundo nombre, el zip() posicional enviaría producto_id mal etiquetado
    # como sede_id (que StockActualView ni lee) y el filtro real se perdería.
    async def test_execute_sp_dado_stock_actual_con_producto_id_cuando_ejecuta_entonces_envia_producto_id_no_sede_id(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoReportRepository

        route = respx_mock.get(STOCK_ACTUAL_URL).mock(
            return_value=httpx.Response(200, json=[])
        )
        repo = DjangoReportRepository(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        await repo.execute_sp(
            "EXEC sp_GetStockActualBodega @BodegaID=?, @SedeID=NULL, @ProductoID=?",
            (1, 42),
        )
        sent_params = route.calls.last.request.url.params
        assert sent_params.get("producto_id") == "42"
        assert "sede_id" not in sent_params

    # Mismo caso que arriba pero para sp_GetInventarioAging: exports.py envía
    # (bodega_id, dias) — dias_minimos no debe llegar mal etiquetado como sede_id.
    async def test_execute_sp_dado_aging_con_dias_minimos_cuando_ejecuta_entonces_envia_dias_minimos_no_sede_id(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoReportRepository

        route = respx_mock.get(AGING_URL).mock(
            return_value=httpx.Response(200, json=[])
        )
        repo = DjangoReportRepository(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        await repo.execute_sp(
            "EXEC sp_GetInventarioAging @BodegaID=?, @SedeID=NULL, @DiasMinimos=?",
            (1, 90),
        )
        sent_params = route.calls.last.request.url.params
        assert sent_params.get("dias_minimos") == "90"
        assert "sede_id" not in sent_params

    # Regresión de concurrencia: execute_sp usa httpx.AsyncClient (no el
    # atajo httpx.get síncrono) — si volviera a ser síncrono, esta llamada
    # bloquearía el único event loop de uvicorn (sin --workers) y congelaría
    # el microservicio completo mientras dura la consulta a Django.
    async def test_execute_sp_dado_llamada_cuando_ejecuta_entonces_es_una_corutina_awaitable(
        self, mock_token_manager, respx_mock
    ):
        import inspect

        from src.infrastructure.django_client import DjangoReportRepository

        respx_mock.get(PRODUCTOS_URL).mock(return_value=httpx.Response(200, json=[]))
        repo = DjangoReportRepository(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        coro = repo.execute_sp("EXEC sp_GetProductosCatalogo", None)
        assert inspect.isawaitable(coro)
        await coro
