"""
Pruebas de la rama de error (500) del router Gerencial — cuando el SP
falla, cada endpoint debe registrar la auditoría (success=False) y responder
500 con el detalle del error.
"""


def test_ventas_gerencial_dado_error_en_sp_cuando_exporta_entonces_retorna_500(
    mock_pandas_read_sql, mock_db_connection,
):
    from tests.test_gerencial import client

    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    response = client.get(
        "/gerencial/ventas?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx",
    )
    assert response.status_code == 500
    assert "SP no disponible" in response.json()["detail"]


def test_top_clientes_gerencial_dado_error_en_sp_cuando_exporta_entonces_retorna_500(
    mock_pandas_read_sql, mock_db_connection,
):
    from tests.test_gerencial import client

    mock_pandas_read_sql.side_effect = RuntimeError("SP no disponible")
    response = client.get(
        "/gerencial/top-clientes?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx",
    )
    assert response.status_code == 500


def test_deudores_gerencial_dado_error_en_sp_cuando_exporta_entonces_retorna_500(
    mock_pandas_read_sql, mock_db_connection,
):
    from tests.test_gerencial import client

    mock_pandas_read_sql.side_effect = ValueError("Parámetro inválido en el SP")
    response = client.get(
        "/gerencial/deudores?fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx",
    )
    assert response.status_code == 500
    assert "Parámetro inválido" in response.json()["detail"]
