import pandas as pd
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app, headers={"Authorization": "Bearer test-token"})

def test_health_check():
    """Prueba que el servicio encienda y esté saludable"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_kardex_export_csv(mock_pandas_read_sql, mock_db_connection):
    """Prueba exportación del Kardex a CSV interceptando SQL Server"""
    # 1. Definir cómo luciría un dataframe falso de Base de datos
    mock_df = pd.DataFrame({
        'id': [1, 2],
        'fecha': ['2026-02-23', '2026-02-24'],
        'tipo_movimiento': ['COMPRA', 'VENTA'],
        'documento_ref': ['DOC-1', 'DOC-2'],
        'cantidad': [100.0, 50.0],
        'saldo_resultante': [100.0, 50.0],
        'bodega_origen_id': [None, 1],
        'bodega_destino_id': [1, None]
    })
    mock_pandas_read_sql.return_value = mock_df
    
    # 2. Emular petición web
    response = client.get("/export/kardex?bodega_id=1&producto_id=10&format=csv")
    
    # 3. Aserciones TDD
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "attachment; filename=kardex_1_10.csv" in response.headers["content-disposition"]
    assert "COMPRA" in response.text
    
def test_productos_export_excel(mock_pandas_read_sql, mock_db_connection):
    """Prueba exportación del Catálogo de Productos a Excel"""
    mock_df = pd.DataFrame({
        'id': [10],
        'codigo': ['PROD-01'],
        'descripcion': ['Tela Algodón'],
        'tipo': ['tela'],
        'unidad_medida': ['kg'],
        'stock_minimo': [50.0],
        'precio_base': [5.50]
    })
    mock_pandas_read_sql.return_value = mock_df
    
    response = client.get("/export/productos?format=xlsx")
    
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
    assert "attachment; filename=catalogo_productos.xlsx" in response.headers["content-disposition"]
    # Comprobar que el contenido es binario zip (formato de Office)
    assert response.content.startswith(b'PK\x03\x04')

def test_usuarios_export_empty(mock_pandas_read_sql, mock_db_connection):
    """Prueba que DataFrame vacío retorna Excel con fila de mensaje (no 404)."""
    mock_pandas_read_sql.return_value = pd.DataFrame()

    response = client.get("/export/usuarios?format=xlsx")

    # El servicio siempre retorna un archivo descargable, nunca 404
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
    assert response.content.startswith(b"PK\x03\x04")


def test_stock_actual_export_xlsx(mock_pandas_read_sql, mock_db_connection):
    """Prueba exportación de stock actual por bodega."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "producto": ["Hilo Nylon", "Tela Algodón"],
        "cantidad": [150.0, 300.0],
    })
    response = client.get("/export/stock-actual?bodega_id=1&format=xlsx")
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
    assert "stock_actual_bodega_1" in response.headers["content-disposition"]


def test_valorizacion_export_xlsx(mock_pandas_read_sql, mock_db_connection):
    """Prueba exportación de valorización de inventario."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "producto": ["Hilo 40/1"],
        "valor_total": [5000.0],
    })
    response = client.get("/export/valorizacion?bodega_id=2&format=xlsx")
    assert response.status_code == 200
    assert "valorizacion_bodega_2" in response.headers["content-disposition"]


def test_aging_export_xlsx(mock_pandas_read_sql, mock_db_connection):
    """Prueba exportación del reporte de aging de inventario."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "producto": ["Hilo Nylon"],
        "dias_sin_movimiento": [45],
    })
    response = client.get("/export/aging?bodega_id=1&dias=30&format=xlsx")
    assert response.status_code == 200
    assert "aging_inventario_bodega_1" in response.headers["content-disposition"]


def test_rotacion_export_xlsx(mock_pandas_read_sql, mock_db_connection):
    """Prueba exportación del reporte de rotación de inventario."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "producto": ["Tela Algodón"],
        "rotacion": [3.5],
    })
    response = client.get(
        "/export/rotacion?bodega_id=1&fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=xlsx"
    )
    assert response.status_code == 200
    assert "rotacion_bodega_1" in response.headers["content-disposition"]


def test_stock_cero_export_xlsx(mock_pandas_read_sql, mock_db_connection):
    """Prueba exportación de productos con stock cero."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "producto": ["Producto Agotado"],
        "stock": [0.0],
    })
    response = client.get("/export/stock-cero?bodega_id=3&format=xlsx")
    assert response.status_code == 200
    assert "stock_cero_bodega_3" in response.headers["content-disposition"]


def test_resumen_movimientos_export_csv(mock_pandas_read_sql, mock_db_connection):
    """Prueba exportación del resumen de movimientos en CSV."""
    mock_pandas_read_sql.return_value = pd.DataFrame({
        "tipo": ["ENTRADA", "SALIDA"],
        "total": [1000.0, 500.0],
    })
    response = client.get(
        "/export/resumen-movimientos?bodega_id=1&fecha_inicio=2026-01-01&fecha_fin=2026-03-31&format=csv"
    )
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "resumen_movimientos_bodega_1" in response.headers["content-disposition"]
