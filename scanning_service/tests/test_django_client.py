"""Tests para DjangoApiClient. EP + circuit breaker.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): api ok / lote inexistente / cache poblado / codigo con barras / sin stock.
- Análisis de valores límite (BVA): sin stock.
"""

from decimal import Decimal
from unittest.mock import MagicMock

import httpx
import pytest

from src.domain.models import AlcanceSede

TODAS = AlcanceSede(sede_id=None, ve_todas=True)

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
    def test_get_lote_by_codigo_dado_api_ok_cuando_valida_entonces_retorna_lote(self, mock_token_manager, respx_mock):
        from src.infrastructure.django_client import DjangoApiClient

        respx_mock.get(VALIDATE_URL).mock(return_value=httpx.Response(200, json=MOCK_VALIDATE_RESPONSE))
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        lote = client.get_lote_by_codigo("LOT-001", TODAS)

        assert lote is not None
        assert lote.codigo_lote == "LOT-001"
        assert lote.orden_produccion.producto_salida.descripcion == "Hilo 40/1"

    # EP: lote no encontrado → retorna None
    def test_get_lote_by_codigo_dado_lote_inexistente_cuando_valida_entonces_retorna_none(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        respx_mock.get(VALIDATE_URL_NO_EXIST).mock(return_value=httpx.Response(404, json={"detail": "No encontrado"}))
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        result = client.get_lote_by_codigo("NO-EXISTE", TODAS)
        assert result is None

    # EP: stock disponible retorna StockBodega desde cache
    def test_get_stock_activo_dado_cache_poblado_cuando_solicita_entonces_retorna_stock(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        respx_mock.get(VALIDATE_URL).mock(return_value=httpx.Response(200, json=MOCK_VALIDATE_RESPONSE))
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        lote = client.get_lote_by_codigo("LOT-001", TODAS)  # puebla el cache
        stock = client.get_stock_activo_por_lote(lote.id)

        assert stock is not None
        assert stock.cantidad == Decimal("95.500")
        assert stock.bodega.nombre == "Bodega Principal"

    # BVA: código con '/' (ej. quien escanea por error el QR de trazabilidad,
    # que es una URL) no debe corromper el path de la request a Django.
    def test_get_lote_by_codigo_dado_codigo_con_barras_cuando_valida_entonces_codifica_la_url(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        codigo_url = "http://localhost/trazabilidad/LOT-001"
        url_esperada = (
            "http://backend:8000/api/internal/v1/lotes/http%3A%2F%2Flocalhost%2Ftrazabilidad%2FLOT-001/validate/"
        )
        route = respx_mock.get(url_esperada).mock(return_value=httpx.Response(404, json={"detail": "No encontrado"}))
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")

        result = client.get_lote_by_codigo(codigo_url, TODAS)

        assert result is None
        assert route.called

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
        respx_mock.get(VALIDATE_URL).mock(return_value=httpx.Response(200, json=response_sin_stock))
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        lote = client.get_lote_by_codigo("LOT-001", TODAS)
        stock = client.get_stock_activo_por_lote(lote.id)
        assert stock is None


class TestDjangoApiClientProductosDelLote:
    """La API interna informa todas las filas vendibles del lote (productos agregados a mano)."""

    def test_get_lote_by_codigo_dado_productos_del_lote_cuando_valida_entonces_los_traduce_al_dominio(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        respuesta = {
            **MOCK_VALIDATE_RESPONSE,
            "peso_total_kg": "125.500",
            "productos": [
                {
                    "producto_id": 7,
                    "descripcion": "Hilo 40/1",
                    "peso_kg": "95.500",
                    "bodega": {"id": 2, "nombre": "Bodega Principal"},
                },
                {
                    "producto_id": 8,
                    "descripcion": "Cono",
                    "peso_kg": "30.000",
                    "bodega": {"id": 4, "nombre": "Tránsito"},
                },
            ],
        }
        respx_mock.get(VALIDATE_URL).mock(return_value=httpx.Response(200, json=respuesta))
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")

        lote = client.get_lote_by_codigo("LOT-001", TODAS)

        assert [(linea.producto.id, linea.cantidad, linea.bodega.nombre) for linea in lote.productos] == [
            (7, Decimal("95.500"), "Bodega Principal"),
            (8, Decimal("30.000"), "Tránsito"),
        ]

    def test_get_lote_by_codigo_dado_respuesta_sin_productos_cuando_valida_entonces_lista_vacia(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        respx_mock.get(VALIDATE_URL).mock(return_value=httpx.Response(200, json=MOCK_VALIDATE_RESPONSE))
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")

        assert client.get_lote_by_codigo("LOT-001", TODAS).productos == []


class TestDjangoApiClientAlcanceSede:
    """OWASP API1: la sede del usuario viaja a la internal_api como `sede_id`."""

    def test_get_lote_dado_usuario_de_una_sede_cuando_valida_entonces_envia_su_sede(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        ruta = respx_mock.get(VALIDATE_URL).mock(return_value=httpx.Response(404, json={"detail": "x"}))
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        client.get_lote_by_codigo("LOT-001", AlcanceSede(sede_id=3, ve_todas=False))
        assert ruta.calls.last.request.url.params["sede_id"] == "3"

    def test_get_lote_dado_usuario_que_ve_todas_cuando_valida_entonces_no_envia_sede(
        self, mock_token_manager, respx_mock
    ):
        from src.infrastructure.django_client import DjangoApiClient

        ruta = respx_mock.get(VALIDATE_URL).mock(return_value=httpx.Response(404, json={"detail": "x"}))
        client = DjangoApiClient(token_manager=mock_token_manager, base_url="http://backend:8000")
        client.get_lote_by_codigo("LOT-001", TODAS)
        assert "sede_id" not in ruta.calls.last.request.url.params
