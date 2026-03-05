import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from src.main import app
import pandas as pd

# Cliente global de pruebas
client = TestClient(app)

@pytest.fixture
def mock_db_connection():
    """Simula o 'Mockea' la conexión con pyodbc y los DataFrames resultantes"""
    with patch('src.database.pyodbc.connect') as mock_connect:
        yield mock_connect

@pytest.fixture
def mock_pandas_read_sql():
    """Simula la ejecución del procedimiento almacenado interceptando a read_sql"""
    with patch('src.database.pd.read_sql') as mock_read:
        yield mock_read
