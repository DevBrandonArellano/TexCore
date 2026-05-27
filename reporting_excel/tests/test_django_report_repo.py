"""Tests para DjangoReportRepository. EP por endpoint representativo."""
from unittest.mock import MagicMock

import httpx
import pandas as pd
import pytest


KARDEX_URL = "http://backend:8000/api/internal/v1/reports/kardex/"
PRODUCTOS_URL = "http://backend:8000/api/internal/v1/reports/productos/"


@pytest.fixture
def mock_token_manager():
    mgr = MagicMock()
    mgr.get_valid_token.return_value = "mock-token"
    return mgr


class TestDjangoReportRepository:

    # EP: API disponible → retorna DataFrame con datos
    def test_execute_sp_dado_kardex_disponible_cuando_ejecuta_entonces_retorna_dataframe(
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
        df = repo.execute_sp(
            "EXEC sp_GetKardexBodega @BodegaID=?, @ProductoID=?, @FechaInicio=?, @FechaFin=?, @ProveedorID=?, @LoteCodigo=?",
            (1, None, None, None, None, None),
        )
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert "producto_descripcion" in df.columns

    # EP: API retorna lista vacía → DataFrame vacío (no error)
    def test_execute_sp_dado_sin_datos_cuando_ejecuta_entonces_retorna_dataframe_vacio(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoReportRepository

        respx_mock.get(PRODUCTOS_URL).mock(
            return_value=httpx.Response(200, json=[])
        )
        repo = DjangoReportRepository(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        df = repo.execute_sp("EXEC sp_GetProductosCatalogo", None)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    # EP: SP no mapeado → ValueError
    def test_execute_sp_dado_sp_desconocido_cuando_ejecuta_entonces_lanza_error(
        self, mock_token_manager
    ):
        from src.infrastructure.django_client import DjangoReportRepository

        repo = DjangoReportRepository(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        with pytest.raises(ValueError, match="SP no mapeado"):
            repo.execute_sp("EXEC sp_NoExiste", None)
