"""Tests para DjangoApiClient. EP + circuit breaker."""
from decimal import Decimal
from unittest.mock import MagicMock

import httpx
import pytest


MOCK_VALIDATE_RESPONSE = {
    "lote_id": 1,
    "codigo_lote": "LOT-001",
    "producto": {"id": 7, "descripcion": "Hilo 40/1"},
    "estado": "finalizada",
    "orden_produccion_id": 3,
    "stock_id": 10,
    "peso_kg": "95.500",
    "bodega": {"id": 2, "nombre": "Bodega Principal"},
}

VALIDATE_URL = "http://backend:8000/api/internal/v1/lotes/LOT-001/validate/"
VALIDATE_URL_NO_EXIST = "http://backend:8000/api/internal/v1/lotes/NO-EXISTE/validate/"


@pytest.fixture
def mock_token_manager():
    mgr = MagicMock()
    mgr.get_valid_token.return_value = "mock-token"
    return mgr


class TestDjangoApiClient:

    # EP: API disponible, lote válido → retorna LoteProduccion
    def test_get_lote_by_codigo_dado_api_ok_cuando_valida_entonces_retorna_lote(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        respx_mock.get(VALIDATE_URL).mock(
            return_value=httpx.Response(200, json=MOCK_VALIDATE_RESPONSE)
        )
        client = DjangoApiClient(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        lote = client.get_lote_by_codigo("LOT-001")

        assert lote is not None
        assert lote.codigo_lote == "LOT-001"
        assert lote.orden_produccion.producto.descripcion == "Hilo 40/1"

    # EP: lote no encontrado → retorna None
    def test_get_lote_by_codigo_dado_lote_inexistente_cuando_valida_entonces_retorna_none(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        respx_mock.get(VALIDATE_URL_NO_EXIST).mock(
            return_value=httpx.Response(404, json={"detail": "No encontrado"})
        )
        client = DjangoApiClient(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        result = client.get_lote_by_codigo("NO-EXISTE")
        assert result is None

    # EP: stock disponible retorna StockBodega desde cache
    def test_get_stock_activo_dado_cache_poblado_cuando_solicita_entonces_retorna_stock(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        respx_mock.get(VALIDATE_URL).mock(
            return_value=httpx.Response(200, json=MOCK_VALIDATE_RESPONSE)
        )
        client = DjangoApiClient(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        lote = client.get_lote_by_codigo("LOT-001")  # puebla el cache
        stock = client.get_stock_activo_por_lote(lote.id)

        assert stock is not None
        assert stock.cantidad == Decimal("95.500")
        assert stock.bodega.nombre == "Bodega Principal"

    # BVA: peso_kg=None en response → get_stock retorna None
    def test_get_stock_activo_dado_sin_stock_cuando_solicita_entonces_retorna_none(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        response_sin_stock = {
            **MOCK_VALIDATE_RESPONSE,
            "stock_id": None,
            "peso_kg": None,
            "bodega": None,
        }
        respx_mock.get(VALIDATE_URL).mock(
            return_value=httpx.Response(200, json=response_sin_stock)
        )
        client = DjangoApiClient(
            token_manager=mock_token_manager, base_url="http://backend:8000"
        )
        lote = client.get_lote_by_codigo("LOT-001")
        stock = client.get_stock_activo_por_lote(lote.id)
        assert stock is None
