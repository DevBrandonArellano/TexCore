"""Tests de integración para el router de Reportes Gerenciales."""
import pandas as pd
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app, headers={"Authorization": "Bearer test-token"})


def test_ventas_gerencial_dado_rango_valido_cuando_exporta_entonces_retorna_xlsx(
    mock_pandas_read_sql, mock_db_connection
):
    """EP: rango de fechas válido → Excel con datos de ventas gerenciales."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "vendedor": ["Ana Torres", "Luis Paredes"],
        "total_ventas": [15000.0, 23000.0],
        "sede": ["Quito", "Guayaquil"],
    })
    response = client.get(
        "/gerencial/ventas?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx"
    )
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
    assert "ventas_gerencial" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK\x03\x04")


def test_top_clientes_gerencial_dado_sede_cuando_exporta_entonces_retorna_xlsx(
    mock_pandas_read_sql, mock_db_connection
):
    """EP: con sede_id específico → Excel con top clientes de esa sede."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "cliente": ["Textiles SA", "Hilos Corp"],
        "total_compras": [50000.0, 35000.0],
    })
    response = client.get(
        "/gerencial/top-clientes?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&sede_id=1&format=xlsx"
    )
    assert response.status_code == 200
    assert "top_clientes_gerencial" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK\x03\x04")


def test_deudores_gerencial_dado_dataframe_vacio_cuando_exporta_entonces_retorna_xlsx(
    mock_pandas_read_sql, mock_db_connection
):
    """EP: sin deuda pendiente → retorna Excel vacío (no 404)."""
    mock_pandas_read_sql.return_value = pd.DataFrame()
    response = client.get("/gerencial/deudores?format=xlsx")
    assert response.status_code == 200
    assert "clientes_deudores_gerencial" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK\x03\x04")
