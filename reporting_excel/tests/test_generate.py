"""
Tests del endpoint genérico POST /generate — reemplaza, para el tráfico real
del backend, a los routers por-reporte (auditoría de performance 2026-08-31):
el backend ya consulta sus propios datos en proceso y solo pide el formateo.
"""
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app, headers={"Authorization": "Bearer test-token"})


def test_generate_dado_rows_con_datos_cuando_post_entonces_200_xlsx(mock_db_connection):
    resp = client.post(
        "/generate",
        json={
            "format": "xlsx",
            "filename": "reporte_test",
            "report_type": "kardex",
            "rows": [{"col": 1}, {"col": 2}],
        },
    )
    assert resp.status_code == 200
    assert "X-Report-Empty" not in resp.headers


def test_generate_dado_rows_vacio_cuando_post_entonces_200_con_mensaje(mock_db_connection):
    resp = client.post(
        "/generate",
        json={"format": "xlsx", "filename": "reporte_vacio", "report_type": "kardex", "rows": []},
    )
    assert resp.status_code == 200
    assert resp.headers.get("X-Report-Empty") == "true"


def test_generate_dado_formato_invalido_cuando_post_entonces_400(mock_db_connection):
    resp = client.post(
        "/generate",
        json={"format": "pdf", "filename": "x", "report_type": "kardex", "rows": []},
    )
    assert resp.status_code == 400


def test_generate_dado_formato_csv_cuando_post_entonces_200(mock_db_connection):
    resp = client.post(
        "/generate",
        json={"format": "csv", "filename": "reporte_csv", "report_type": "productos", "rows": [{"a": 1}]},
    )
    assert resp.status_code == 200
