"""Tests de integración para el router de Reportes de Producción."""
import pandas as pd
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app, headers={"Authorization": "Bearer test-token"})


def test_ordenes_produccion_dado_rango_valido_cuando_exporta_entonces_retorna_xlsx(
    mock_pandas_read_sql, mock_db_connection
):
    """EP: rango válido → Excel con órdenes de producción."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "orden": ["OP-001", "OP-002"],
        "estado": ["COMPLETADA", "EN_PROCESO"],
        "cantidad_kg": [100.0, 250.0],
    })
    response = client.get(
        "/produccion/ordenes?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx"
    )
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
    assert "ordenes_produccion" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK\x03\x04")


def test_lotes_produccion_dado_rango_valido_cuando_exporta_entonces_retorna_xlsx(
    mock_pandas_read_sql, mock_db_connection
):
    """EP: rango válido → Excel con lotes de producción."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "lote": ["L-2026-001", "L-2026-002"],
        "peso_neto_kg": [500.0, 320.0],
        "estado": ["ACTIVO", "FINALIZADO"],
    })
    response = client.get(
        "/produccion/lotes?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx"
    )
    assert response.status_code == 200
    assert "lotes_produccion" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK\x03\x04")


def test_tendencia_produccion_dado_rango_valido_cuando_exporta_entonces_retorna_xlsx(
    mock_pandas_read_sql, mock_db_connection
):
    """EP: rango válido → Excel con tendencia semanal de producción."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "semana": ["2026-W01", "2026-W02", "2026-W03"],
        "produccion_kg": [1200.0, 1350.0, 980.0],
    })
    response = client.get(
        "/produccion/tendencia?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx"
    )
    assert response.status_code == 200
    assert "tendencia_produccion" in response.headers["content-disposition"]
    assert response.content.startswith(b"PK\x03\x04")


def test_ordenes_produccion_formato_invalido_retorna_400():
    """BVA: formato 'pdf' no soportado en órdenes de producción → 400 Bad Request."""
    response = client.get(
        "/produccion/ordenes?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=pdf"
    )
    assert response.status_code == 400
    assert "Formato no soportado" in response.json()["detail"]


def test_lotes_produccion_formato_invalido_retorna_400():
    """BVA: formato 'pdf' no soportado en lotes de producción → 400 Bad Request."""
    response = client.get(
        "/produccion/lotes?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=pdf"
    )
    assert response.status_code == 400
    assert "Formato no soportado" in response.json()["detail"]


def test_tendencia_produccion_formato_invalido_retorna_400():
    """BVA: formato 'pdf' no soportado en tendencia de producción → 400 Bad Request."""
    response = client.get(
        "/produccion/tendencia?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=pdf"
    )
    assert response.status_code == 400
    assert "Formato no soportado" in response.json()["detail"]
