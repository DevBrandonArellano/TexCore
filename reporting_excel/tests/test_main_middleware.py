"""
Tests de src/main.py: middleware JWT (ISO 27001 A.9.4), /health y lifespan.

El conftest acepta cualquier Bearer parcheando jwt.decode para toda la sesión;
aquí se vuelve a parchear por prueba para ejercitar cada rechazo.
"""
from unittest.mock import AsyncMock, patch

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient

from src.main import _get_required_env, app

_BODY = {"format": "csv", "filename": "r", "report_type": "kardex", "rows": [{"a": 1}]}
_PAYLOAD_OK = {"iss": "texcore", "sub": "svc", "type": "service_access"}


def _post(headers=None):
    return TestClient(app).post("/generate", json=_BODY, headers=headers or {})


class TestGetRequiredEnv:
    def test_get_required_env_dado_variable_ausente_cuando_lee_entonces_runtime_error(self, monkeypatch):
        monkeypatch.delenv("TEXCORE_VAR_INEXISTENTE", raising=False)
        with pytest.raises(RuntimeError, match="TEXCORE_VAR_INEXISTENTE"):
            _get_required_env("TEXCORE_VAR_INEXISTENTE")

    def test_get_required_env_dado_variable_definida_cuando_lee_entonces_retorna_valor(self, monkeypatch):
        monkeypatch.setenv("TEXCORE_VAR_PRUEBA", "valor")
        assert _get_required_env("TEXCORE_VAR_PRUEBA") == "valor"


class TestVerifyJwtServiceToken:
    def test_middleware_dado_sin_header_authorization_cuando_post_entonces_401(self):
        resp = _post()
        assert resp.status_code == 401
        assert "Bearer" in resp.json()["detail"]

    def test_middleware_dado_esquema_basic_cuando_post_entonces_401(self):
        resp = _post({"Authorization": "Basic abc"})
        assert resp.status_code == 401

    def test_middleware_dado_token_expirado_cuando_post_entonces_401_token_expirado(self):
        with patch("src.main.jwt.decode", side_effect=jwt.ExpiredSignatureError("exp")):
            resp = _post({"Authorization": "Bearer t"})
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Token expirado."}

    def test_middleware_dado_token_invalido_cuando_post_entonces_401(self):
        with patch("src.main.jwt.decode", side_effect=jwt.InvalidSignatureError("firma")):
            resp = _post({"Authorization": "Bearer t"})
        assert resp.status_code == 401
        assert resp.json()["detail"].startswith("Token inválido")

    def test_middleware_dado_refresh_token_cuando_post_entonces_401_tipo_incorrecto(self):
        with patch("src.main.jwt.decode", return_value={**_PAYLOAD_OK, "type": "refresh"}):
            resp = _post({"Authorization": "Bearer t"})
        assert resp.status_code == 401
        assert "service_access" in resp.json()["detail"]

    def test_middleware_dado_emisor_ajeno_cuando_post_entonces_401(self):
        with patch("src.main.jwt.decode", return_value={**_PAYLOAD_OK, "iss": "otro"}):
            resp = _post({"Authorization": "Bearer t"})
        assert resp.status_code == 401
        assert resp.json() == {"detail": "Emisor de token no reconocido."}

    def test_middleware_dado_token_valido_cuando_post_entonces_200(self):
        with patch("src.main.jwt.decode", return_value=_PAYLOAD_OK):
            resp = _post({"Authorization": "Bearer t"})
        assert resp.status_code == 200


class TestHealth:
    def test_health_dado_django_200_cuando_get_entonces_healthy_sin_token(self):
        with patch("src.main.httpx.get", return_value=httpx.Response(200)):
            resp = TestClient(app).get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "healthy", "django_api": "connected"}

    def test_health_dado_django_503_cuando_get_entonces_degraded_con_codigo(self):
        with patch("src.main.httpx.get", return_value=httpx.Response(503)):
            resp = TestClient(app).get("/health")
        assert resp.json() == {"status": "degraded", "django_api": "HTTP 503"}

    def test_health_dado_django_inalcanzable_cuando_get_entonces_degraded_unreachable(self):
        with patch("src.main.httpx.get", side_effect=httpx.ConnectError("sin red")):
            resp = TestClient(app).get("/health")
        assert resp.json() == {"status": "degraded", "django_api": "unreachable"}


class TestLifespan:
    def test_lifespan_dado_arranque_cuando_inicia_app_entonces_inicializa_bd_de_auditoria(self):
        with patch("src.main.init_db", new=AsyncMock()) as init_db, \
             patch("src.main.httpx.get", return_value=httpx.Response(200)), \
             TestClient(app) as c:
            c.get("/health")
        init_db.assert_awaited_once()
