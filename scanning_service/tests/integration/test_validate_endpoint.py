"""
Tests de integración del endpoint /validate y /health.
Usa app.dependency_overrides para inyectar servicios mock — sin sys.modules hacks.
Aplica ISTQB: EP (clases válida/inválida) + BVA (strings vacíos/espacios).
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from src.main import app
from src.routers.validate import get_validation_service
from src.schemas.validate import LoteInfo, ValidateResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lote_info(
    codigo: str = "LOTE-00001",
    producto_id: int = 1,
    producto_nombre: str = "Hilo Nylon",
    peso: str = "25.00",
    bodega_id: int = 10,
    bodega_nombre: str = "Bodega Central",
) -> LoteInfo:
    return LoteInfo(
        codigo=codigo,
        producto_id=producto_id,
        producto_nombre=producto_nombre,
        peso=peso,
        bodega_id=bodega_id,
        bodega_nombre=bodega_nombre,
    )


def _mock_service(response: ValidateResponse) -> MagicMock:
    svc = MagicMock()
    svc.validate.return_value = response
    return svc


# ---------------------------------------------------------------------------
# Fixtures: cada uno instala/limpia su dependency_override
# ---------------------------------------------------------------------------

@pytest.fixture
def client_lote_valido():
    mock_svc = _mock_service(ValidateResponse(valid=True, lote=_lote_info()))
    app.dependency_overrides[get_validation_service] = lambda: mock_svc
    yield TestClient(app), mock_svc
    app.dependency_overrides.clear()


@pytest.fixture
def client_lote_no_encontrado():
    mock_svc = _mock_service(ValidateResponse(valid=False, reason="Lote no encontrado en el sistema"))
    app.dependency_overrides[get_validation_service] = lambda: mock_svc
    yield TestClient(app), mock_svc
    app.dependency_overrides.clear()


@pytest.fixture
def client_sin_stock():
    mock_svc = _mock_service(
        ValidateResponse(valid=False, reason="Lote existe pero no tiene stock disponible (0 kg)")
    )
    app.dependency_overrides[get_validation_service] = lambda: mock_svc
    yield TestClient(app), mock_svc
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Tests EP Clase Válida: lote con stock
# ---------------------------------------------------------------------------

class TestValidateEndpoint_LoteValido:

    def test_validate_dado_lote_con_stock_cuando_post_entonces_200_y_valid_true(self, client_lote_valido):
        tc, _ = client_lote_valido
        response = tc.post("/validate", json={"code": "LOTE-00001"})
        assert response.status_code == 200
        assert response.json()["valid"] is True

    def test_validate_dado_lote_valido_cuando_post_entonces_retorna_codigo_lote(self, client_lote_valido):
        tc, _ = client_lote_valido
        data = tc.post("/validate", json={"code": "LOTE-00001"}).json()
        assert data["lote"]["codigo"] == "LOTE-00001"

    def test_validate_dado_lote_valido_cuando_post_entonces_retorna_bodega(self, client_lote_valido):
        tc, _ = client_lote_valido
        data = tc.post("/validate", json={"code": "LOTE-00001"}).json()
        assert data["lote"]["bodega_nombre"] == "Bodega Central"
        assert data["lote"]["bodega_id"] == 10

    def test_validate_dado_lote_valido_cuando_post_entonces_servicio_recibe_codigo(self, client_lote_valido):
        tc, mock_svc = client_lote_valido
        tc.post("/validate", json={"code": "LOTE-00001"})
        mock_svc.validate.assert_called_once_with("LOTE-00001")


# ---------------------------------------------------------------------------
# Tests EP Clase Inválida: lote no encontrado
# ---------------------------------------------------------------------------

class TestValidateEndpoint_LoteNoEncontrado:

    def test_validate_dado_codigo_inexistente_cuando_post_entonces_200_y_valid_false(self, client_lote_no_encontrado):
        tc, _ = client_lote_no_encontrado
        data = tc.post("/validate", json={"code": "LOTE-FAKE"}).json()
        assert data["valid"] is False
        assert "no encontrado" in data["reason"].lower()

    def test_validate_dado_codigo_inexistente_cuando_post_entonces_lote_es_null(self, client_lote_no_encontrado):
        tc, _ = client_lote_no_encontrado
        data = tc.post("/validate", json={"code": "LOTE-FAKE"}).json()
        assert data["lote"] is None


# ---------------------------------------------------------------------------
# Tests EP: lote sin stock
# ---------------------------------------------------------------------------

class TestValidateEndpoint_SinStock:

    def test_validate_dado_lote_sin_stock_cuando_post_entonces_200_y_valid_false(self, client_sin_stock):
        tc, _ = client_sin_stock
        data = tc.post("/validate", json={"code": "LOTE-SIN-STOCK"}).json()
        assert data["valid"] is False
        assert data["reason"] is not None


# ---------------------------------------------------------------------------
# Tests BVA: validación Pydantic (sin override, Pydantic actúa antes del servicio)
# ---------------------------------------------------------------------------

class TestValidateEndpoint_ValidacionPydantic:

    def test_validate_dado_payload_sin_code_cuando_post_entonces_422(self):
        response = TestClient(app).post("/validate", json={})
        assert response.status_code == 422

    def test_validate_dado_code_vacio_cuando_post_entonces_422(self):
        response = TestClient(app).post("/validate", json={"code": ""})
        assert response.status_code == 422

    def test_validate_dado_code_solo_espacios_cuando_post_entonces_422(self):
        # BVA: string de solo espacios — el validator lo rechaza
        response = TestClient(app).post("/validate", json={"code": "   "})
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Tests del endpoint /health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:

    def test_health_dado_django_api_accesible_cuando_get_entonces_200(self):
        from unittest.mock import patch, MagicMock as MM
        mock_resp = MM()
        mock_resp.status_code = 200
        with patch("src.routers.health._health_client") as mock_client:
            mock_client.get.return_value = mock_resp
            response = TestClient(app).get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["django_api"] == "connected"
