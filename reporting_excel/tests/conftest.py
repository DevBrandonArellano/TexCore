"""conftest.py del reporting_excel. Proporciona fixtures compartidos para tests."""
import os
import pytest
from unittest.mock import patch

# Configurar env vars ANTES de importar src.main (que llama _get_required_env en módulo).
# setdefault no sobreescribe si ya están definidas (ej: en CI con INTERNAL_JWT_PUBLIC_KEY real).
os.environ.setdefault("INTERNAL_JWT_PUBLIC_KEY", "test-placeholder")
os.environ.setdefault("DJANGO_INTERNAL_URL", "http://localhost:8000")

from src.main import app  # noqa: E402 — import después de configurar env

_VALID_JWT_PAYLOAD = {
    "iss": "texcore",
    "sub": "test-service",
    "type": "service_access",
    "scope": ["reports:read"],
    "jti": "test-jti",
}


@pytest.fixture(scope="session", autouse=True)
def bypass_jwt():
    """Reemplaza jwt.decode por un mock que acepta cualquier Bearer token en tests."""
    with patch("src.main.jwt.decode", return_value=_VALID_JWT_PAYLOAD):
        yield


@pytest.fixture
def mock_db_connection():
    """
    No-op: fixture mantenido por compatibilidad de firma con tests existentes
    que lo piden como parámetro (no hace falta mockear nada — este servicio no
    tiene acceso a BD desde la auditoría de performance 2026-08-31, que
    eliminó también su único cliente HTTP saliente hacia Django).
    """
    yield
