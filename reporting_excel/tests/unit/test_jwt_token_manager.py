"""Tests para JWTTokenManager. EP + BVA."""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

TEST_PRIVATE_KEY = None
TEST_PUBLIC_KEY = None


@pytest.fixture(autouse=True)
def rsa_keys():
    """Genera un par RSA temporal para tests."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa

    global TEST_PRIVATE_KEY, TEST_PUBLIC_KEY

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    TEST_PRIVATE_KEY = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ).decode()
    TEST_PUBLIC_KEY = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


def _make_token(exp_seconds: int = 900) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "texcore", "sub": "reporting_excel", "scope": ["reports:read"],
        "jti": str(uuid.uuid4()), "iat": now, "exp": now + timedelta(seconds=exp_seconds),
        "type": "service_access",
    }
    return jwt.encode(payload, TEST_PRIVATE_KEY, algorithm="RS256")


def _mock_httpx_async_client(response):
    """
    Mock utilizable como reemplazo de httpx.AsyncClient — soporta
    `async with httpx.AsyncClient() as client: await client.post(...)`,
    que es el patrón real que usa _fetch_token() (no el atajo httpx.post
    síncrono, que bloquearía el event loop de uvicorn).
    """
    client = AsyncMock()
    client.post = AsyncMock(return_value=response)
    cm = MagicMock()
    cm.return_value.__aenter__ = AsyncMock(return_value=client)
    cm.return_value.__aexit__ = AsyncMock(return_value=False)
    return cm


class TestJWTTokenManager:
    def _create_manager(self):
        from src.infrastructure.jwt_token_manager import JWTTokenManager
        return JWTTokenManager(
            django_url="http://django:8000", service_name="reporting_excel",
            service_secret="secret", public_key=TEST_PUBLIC_KEY,
        )

    async def test_get_valid_token_dado_token_fresco_cuando_solicita_entonces_no_refresca(self):
        # El conftest.py de este servicio parchea jwt.decode a nivel de sesión
        # (bypass_jwt) para simplificar los tests de endpoints — pero eso
        # también rompe _is_expiring (que necesita el 'exp' real del payload).
        # jwt.api_jwt.decode conserva la implementación real y no fue tocado
        # por ese parche de sesión (vive en un módulo distinto).
        import jwt as jwt_module

        manager = self._create_manager()
        fresh_token = _make_token(exp_seconds=900)
        manager._access_token = fresh_token

        with patch("jwt.decode", side_effect=jwt_module.api_jwt.decode):
            with patch.object(manager, "_fetch_token") as mock_fetch:
                result = await manager.get_valid_token()
                mock_fetch.assert_not_called()
        assert result == fresh_token

    async def test_get_valid_token_dado_token_por_expirar_cuando_solicita_entonces_refresca(self):
        import jwt as jwt_module

        manager = self._create_manager()
        manager._access_token = _make_token(exp_seconds=29)
        new_token = _make_token(exp_seconds=900)
        with patch("jwt.decode", side_effect=jwt_module.api_jwt.decode):
            with patch.object(manager, "_fetch_token", AsyncMock(return_value=new_token)):
                result = await manager.get_valid_token()
        assert result == new_token

    async def test_get_valid_token_dado_sin_token_cuando_solicita_entonces_hace_fetch(self):
        manager = self._create_manager()
        new_token = _make_token(exp_seconds=900)
        with patch.object(manager, "_fetch_token", AsyncMock(return_value=new_token)):
            result = await manager.get_valid_token()
        assert result == new_token

    async def test_get_valid_token_dado_token_invalido_cuando_solicita_entonces_trata_como_expirado(self):
        # Caja blanca: rama `except Exception: return True` en _is_expiring
        manager = self._create_manager()
        manager._access_token = "no-es-un-jwt-valido"
        new_token = _make_token(exp_seconds=900)
        with patch.object(manager, "_fetch_token", AsyncMock(return_value=new_token)):
            result = await manager.get_valid_token()
        assert result == new_token

    async def test_fetch_token_dado_respuesta_200_cuando_llama_entonces_retorna_access_y_guarda_refresh(self):
        manager = self._create_manager()
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"access_token": "new-access", "refresh_token": "new-refresh"}

        mock_async_client = _mock_httpx_async_client(mock_response)
        with patch("src.infrastructure.jwt_token_manager.httpx.AsyncClient", mock_async_client):
            result = await manager._fetch_token()

        assert result == "new-access"
        assert manager._refresh_token == "new-refresh"
        sent_client = mock_async_client.return_value.__aenter__.return_value
        sent_url = sent_client.post.call_args[0][0]
        assert sent_url == "http://django:8000/api/internal/v1/auth/token/"

    async def test_fetch_token_dado_respuesta_error_cuando_llama_entonces_lanza_runtimeerror(self):
        manager = self._create_manager()
        mock_response = MagicMock(status_code=401)
        mock_async_client = _mock_httpx_async_client(mock_response)
        with patch("src.infrastructure.jwt_token_manager.httpx.AsyncClient", mock_async_client):
            with pytest.raises(RuntimeError, match="HTTP 401"):
                await manager._fetch_token()

    # Regresión de concurrencia: get_valid_token() debe ser una corutina —
    # antes usaba httpx.post síncrono, que bloquea el único event loop de
    # uvicorn (sin --workers) y congela el microservicio completo mientras
    # dura el refresh del token.
    async def test_get_valid_token_dado_llamada_cuando_ejecuta_entonces_es_una_corutina_awaitable(self):
        import inspect

        manager = self._create_manager()
        manager._access_token = _make_token(exp_seconds=900)
        with patch("jwt.decode", side_effect=jwt.api_jwt.decode):
            coro = manager.get_valid_token()
            assert inspect.isawaitable(coro)
            await coro
