import pandas as pd
from fastapi.testclient import TestClient
from src.main import app, INTERNAL_KEY

client = TestClient(app, headers={"X-Internal-Key": INTERNAL_KEY})

def test_health_check():
    """Prueba que el servicio encienda y esté saludable"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "reporting_excel"}

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
    """Prueba que pasa cuando el procedimiento almacenado no devuelve nada"""
    mock_pandas_read_sql.return_value = pd.DataFrame()
    
    response = client.get("/export/usuarios?format=xlsx")
    
    assert response.status_code == 404
    assert response.json() == {"detail": "No se encontraron datos para estos parámetros."}
