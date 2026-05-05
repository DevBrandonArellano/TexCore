"""
Tests del scanning_service — endpoint /validate.
Aplica técnicas ISTQB:
  - Partición de Equivalencia (EP): lote válido / lote no encontrado / sin stock
  - State Transition: lote existe pero sin stock (estado inválido para despacho)

Convención: test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]

Los tests usan TestClient de FastAPI con la sesión de BD completamente
mockeada — no requieren SQL Server ni red.
"""
import sys
import os
from unittest.mock import MagicMock, patch

# Asegurar que conftest.py ya inyectó los mocks de src.database y src.models
# antes de que importemos la app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest


# --------------------------------------------------------------------------
# Helpers para construir objetos mock del dominio
# --------------------------------------------------------------------------

def _make_producto(id: int = 1, descripcion: str = "Hilo Nylon") -> MagicMock:
    p = MagicMock()
    p.id = id
    p.descripcion = descripcion
    return p


def _make_bodega(id: int = 10, nombre: str = "Bodega Central") -> MagicMock:
    b = MagicMock()
    b.id = id
    b.nombre = nombre
    return b


def _make_orden(producto=None) -> MagicMock:
    o = MagicMock()
    o.producto = producto or _make_producto()
    return o


def _make_lote(codigo: str = "LOTE-00001", orden=None) -> MagicMock:
    lote = MagicMock()
    lote.codigo_lote = codigo
    lote.orden_produccion = orden or _make_orden()
    return lote


def _make_stock(cantidad=50, bodega=None, lote_id: int = 1) -> MagicMock:
    s = MagicMock()
    s.cantidad = cantidad
    s.bodega = bodega or _make_bodega()
    s.lote_id = lote_id
    return s


# --------------------------------------------------------------------------
# Fixture: importar app y TestClient con mocks de BD activos
# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Retorna TestClient con SessionLocal mockeado."""
    from fastapi.testclient import TestClient

    # Parchear SessionLocal globalmente en src.main antes del import
    mock_session_cls = MagicMock()
    with patch.dict(sys.modules, {}):
        # Reimportar main con SessionLocal mockeado
        import importlib
        import src.main as main_module
        original_session = main_module.SessionLocal
        main_module.SessionLocal = mock_session_cls
        yield TestClient(main_module.app), mock_session_cls
        main_module.SessionLocal = original_session


# --------------------------------------------------------------------------
# Tests del endpoint GET /health
# --------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_dado_servicio_activo_cuando_consultar_entonces_retorna_200(self, client):
        tc, mock_session_cls = client
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        response = tc.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


# --------------------------------------------------------------------------
# Tests EP — /validate con lote encontrado (válido con stock)
# --------------------------------------------------------------------------

class TestValidateEndpoint_LoteEncontrado:
    """EP Clase Válida: lote existe y tiene stock disponible."""

    def test_validate_dado_lote_existente_con_stock_cuando_validar_entonces_retorna_valido(self, client):
        tc, mock_session_cls = client
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        lote = _make_lote("LOTE-00001")
        stock = _make_stock(cantidad=25, lote_id=1)

        # Configurar el query chain de SQLAlchemy mockeado
        mock_db.query.return_value.options.return_value.filter.return_value.first.side_effect = [
            lote,   # primera query: LoteProduccion
            stock,  # segunda query: StockBodega
        ]

        response = tc.post("/validate", json={"code": "LOTE-00001"})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True
        assert data["lote"]["codigo"] == "LOTE-00001"
        assert data["lote"]["bodega_nombre"] == "Bodega Central"


# --------------------------------------------------------------------------
# Tests EP — /validate con lote no encontrado
# --------------------------------------------------------------------------

class TestValidateEndpoint_LoteNoEncontrado:
    """EP Clase Inválida: código no existe en la base de datos."""

    def test_validate_dado_codigo_inexistente_cuando_validar_entonces_retorna_invalido(self, client):
        tc, mock_session_cls = client
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        # Primera query retorna None — lote no encontrado
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None

        response = tc.post("/validate", json={"code": "LOTE-INEXISTENTE"})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert "no encontrado" in data["reason"].lower()


# --------------------------------------------------------------------------
# Tests EP — /validate lote sin stock disponible
# --------------------------------------------------------------------------

class TestValidateEndpoint_SinStock:
    """EP — lote existe pero cantidad = 0 (no puede despacharse)."""

    def test_validate_dado_lote_sin_stock_cuando_validar_entonces_retorna_invalido_con_razon(self, client):
        tc, mock_session_cls = client
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        lote = _make_lote("LOTE-SIN-STOCK")

        mock_db.query.return_value.options.return_value.filter.return_value.first.side_effect = [
            lote,  # lote encontrado
            None,  # sin stock disponible
        ]

        response = tc.post("/validate", json={"code": "LOTE-SIN-STOCK"})
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert data["reason"] is not None


# --------------------------------------------------------------------------
# Tests de validación de entrada (Pydantic)
# --------------------------------------------------------------------------

class TestValidateEndpoint_EntradaInvalida:
    """EP Clase Inválida: payload malformado."""

    def test_validate_dado_payload_sin_code_cuando_enviar_entonces_retorna_422(self, client):
        tc, _ = client
        response = tc.post("/validate", json={})
        assert response.status_code == 422

    def test_validate_dado_code_vacio_cuando_enviar_entonces_procesa_sin_error_500(self, client):
        """BVA: string vacío — límite inferior de longitud."""
        tc, mock_session_cls = client
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = None

        response = tc.post("/validate", json={"code": ""})
        # No debe ser un 500 — Pydantic acepta string vacío, la lógica responde "no encontrado"
        assert response.status_code == 200
        assert response.json()["valid"] is False
