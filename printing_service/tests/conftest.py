"""conftest.py del printing_service. Proporciona fixtures compartidos para tests."""
import os
from unittest.mock import patch

import pytest

# Configurar env vars ANTES de importar src.main (que llama _get_required_env en módulo).
os.environ.setdefault("INTERNAL_JWT_PUBLIC_KEY", "test-placeholder")

from src.main import app  # noqa: E402 — import después de configurar env

_VALID_JWT_PAYLOAD = {
    "iss": "texcore",
    "sub": "test-service",
    "type": "service_access",
    "scope": ["printing:write"],
    "jti": "test-jti",
}


@pytest.fixture(scope="session", autouse=True)
def bypass_jwt():
    """Reemplaza jwt.decode por un mock que acepta cualquier Bearer token en tests."""
    with patch("src.main.jwt.decode", return_value=_VALID_JWT_PAYLOAD):
        yield


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def app_client():
    from fastapi.testclient import TestClient
    return TestClient(app)
