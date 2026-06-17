"""conftest.py del reporting_excel. Proporciona fixtures compartidos para tests."""
import os
import pytest
import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Configurar env vars ANTES de importar src.main (que llama _get_required_env en módulo).
# setdefault no sobreescribe si ya están definidas (ej: en CI con INTERNAL_JWT_PUBLIC_KEY real).
os.environ.setdefault("INTERNAL_JWT_PUBLIC_KEY", "test-placeholder")
os.environ.setdefault("DJANGO_INTERNAL_URL", "http://localhost:8000")
os.environ.setdefault("SERVICE_NAME", "reporting_excel")
os.environ.setdefault("SERVICE_SECRET", "test-secret")

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
    """No-op: pyodbc fue reemplazado por DjangoReportRepository. Fixture mantenido por compatibilidad de firma."""
    yield


@pytest.fixture
def mock_pandas_read_sql():
    """Mockea DjangoReportRepository.execute_sp (reemplaza la anterior capa pyodbc/pd.read_sql)."""
    with patch("src.infrastructure.django_client.DjangoReportRepository.execute_sp") as mock_exec:
        yield mock_exec


@pytest.fixture
def mock_repo():
    """Mock de IReportRepository para tests unitarios de ReportService."""
    repo = MagicMock()
    repo.execute_sp.return_value = pd.DataFrame()
    return repo
