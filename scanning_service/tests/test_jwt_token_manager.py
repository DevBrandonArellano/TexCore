"""Tests para JWTTokenManager. EP + BVA."""
import time as _time
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

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
    """Genera token RS256 con las claves del fixture."""
    now = datetime.now(timezone.utc)
    payload = {
        "iss": "texcore",
        "sub": "scanning_service",
        "scope": ["lotes:read"],
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=exp_seconds),
        "type": "service_access",
    }
    return jwt.encode(payload, TEST_PRIVATE_KEY, algorithm="RS256")


class TestJWTTokenManager:
    """Tests para JWTTokenManager. EP + BVA."""

    def _create_manager(self):
        from src.infrastructure.jwt_token_manager import JWTTokenManager
        return JWTTokenManager(
            django_url="http://django:8000",
            service_name="scanning_service",
            service_secret="secret",
            public_key=TEST_PUBLIC_KEY,
        )

    # EP: token fresco → devuelve el mismo sin refrescar
    def test_get_valid_token_dado_token_fresco_cuando_solicita_entonces_no_refresca(self):
        manager = self._create_manager()
        fresh_token = _make_token(exp_seconds=900)
        manager._access_token = fresh_token

        with patch.object(manager, "_fetch_token") as mock_fetch:
            result = manager.get_valid_token()
            mock_fetch.assert_not_called()
        assert result == fresh_token

    # BVA: token expira en 29s (< buffer 30s) → refresca
    def test_get_valid_token_dado_token_por_expirar_cuando_solicita_entonces_refresca(self):
        manager = self._create_manager()
        expiring_token = _make_token(exp_seconds=29)
        manager._access_token = expiring_token

        new_token = _make_token(exp_seconds=900)
        with patch.object(manager, "_fetch_token", return_value=new_token):
            result = manager.get_valid_token()
        assert result == new_token

    # EP: sin token previo → fetch automático
    def test_get_valid_token_dado_sin_token_cuando_solicita_entonces_hace_fetch(self):
        manager = self._create_manager()
        new_token = _make_token(exp_seconds=900)
        with patch.object(manager, "_fetch_token", return_value=new_token):
            result = manager.get_valid_token()
        assert result == new_token

    # BVA: token con exactamente 31s de vida → no refresca (dentro del buffer)
    def test_get_valid_token_dado_31s_de_vida_cuando_solicita_entonces_no_refresca(self):
        manager = self._create_manager()
        # Congela el tiempo ANTES de crear el token (floor a segundos enteros).
        # PyJWT trunca datetime a int al codificar: exp = floor(now + 31).
        # Con frozen_now <= T_creacion, la condición exp-30 > frozen_now es siempre False
        # independientemente de retrasos de CI o cruce de frontera de segundo.
        frozen_now = int(_time.time())
        token_31s = _make_token(exp_seconds=31)
        manager._access_token = token_31s

        with patch("src.infrastructure.jwt_token_manager.time") as mock_time:
            mock_time.time.return_value = float(frozen_now)
            with patch.object(manager, "_fetch_token") as mock_fetch:
                manager.get_valid_token()
                mock_fetch.assert_not_called()
