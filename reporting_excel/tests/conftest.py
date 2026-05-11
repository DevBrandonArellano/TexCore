import pytest
import pandas as pd
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app, INTERNAL_KEY

# Cliente global con autenticación interna
client = TestClient(app, headers={"X-Internal-Key": INTERNAL_KEY})


@pytest.fixture
def mock_db_connection():
    """Mockea pyodbc.connect en el repositorio SQL."""
    with patch("src.repositories.sql_repository.pyodbc.connect") as mock_connect:
        yield mock_connect


@pytest.fixture
def mock_pandas_read_sql():
    """Mockea pd.read_sql en el repositorio SQL."""
    with patch("src.repositories.sql_repository.pd.read_sql") as mock_read:
        yield mock_read


@pytest.fixture
def mock_repo():
    """Mock de IReportRepository para tests unitarios de ReportService."""
    repo = MagicMock()
    repo.execute_sp.return_value = pd.DataFrame()
    return repo
