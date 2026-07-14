"""
Pruebas de la rama de error (500) de src/routers/exports.py — ninguno de
los 9 endpoints tenía cubierto el caso "el SP falla".
"""
from src.main import app
from fastapi.testclient import TestClient

client = TestClient(app, headers={"Authorization": "Bearer test-token"})


def test_kardex_dado_error_en_sp_cuando_exporta_entonces_retorna_500(mock_pandas_read_sql, mock_db_connection):
    # Regresión del bug QA: cualquier error devolvía 400 (ver comentario en
    # export_kardex) — un RuntimeError del SP debe ser 500, no 400.
    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    resp = client.get("/export/kardex?bodega_id=1&format=xlsx")
    assert resp.status_code == 500


def test_kardex_dado_valueerror_cuando_exporta_entonces_retorna_400(mock_pandas_read_sql, mock_db_connection):
    mock_pandas_read_sql.side_effect = ValueError("Parámetro inválido")
    resp = client.get("/export/kardex?bodega_id=1&format=xlsx")
    assert resp.status_code == 400


def test_productos_dado_error_en_sp_cuando_exporta_entonces_retorna_500(mock_pandas_read_sql, mock_db_connection):
    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    resp = client.get("/export/productos?format=xlsx")
    assert resp.status_code == 500


def test_usuarios_dado_error_en_sp_cuando_exporta_entonces_retorna_500(mock_pandas_read_sql, mock_db_connection):
    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    resp = client.get("/export/usuarios?format=xlsx")
    assert resp.status_code == 500


def test_stock_actual_dado_error_en_sp_cuando_exporta_entonces_retorna_500(mock_pandas_read_sql, mock_db_connection):
    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    resp = client.get("/export/stock-actual?bodega_id=1&format=xlsx")
    assert resp.status_code == 500


def test_valorizacion_dado_error_en_sp_cuando_exporta_entonces_retorna_500(mock_pandas_read_sql, mock_db_connection):
    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    resp = client.get("/export/valorizacion?bodega_id=1&format=xlsx")
    assert resp.status_code == 500


def test_aging_dado_error_en_sp_cuando_exporta_entonces_retorna_500(mock_pandas_read_sql, mock_db_connection):
    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    resp = client.get("/export/aging?bodega_id=1&format=xlsx")
    assert resp.status_code == 500


def test_rotacion_dado_error_en_sp_cuando_exporta_entonces_retorna_500(mock_pandas_read_sql, mock_db_connection):
    mock_pandas_read_sql.side_effect = ValueError("Parámetro inválido")
    resp = client.get("/export/rotacion?bodega_id=1&fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx")
    assert resp.status_code == 500


def test_stock_cero_dado_error_en_sp_cuando_exporta_entonces_retorna_500(mock_pandas_read_sql, mock_db_connection):
    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    resp = client.get("/export/stock-cero?bodega_id=1&format=xlsx")
    assert resp.status_code == 500


def test_resumen_movimientos_dado_error_en_sp_cuando_exporta_entonces_retorna_500(
    mock_pandas_read_sql, mock_db_connection,
):
    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    resp = client.get(
        "/export/resumen-movimientos?bodega_id=1&fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx",
    )
    assert resp.status_code == 500
