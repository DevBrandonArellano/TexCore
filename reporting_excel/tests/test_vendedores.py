import pandas as pd
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_ventas_vendedor_export_csv(mock_db_connection, mock_pandas_read_sql):
    """Prueba exportación de ventas de vendedor a CSV interceptando SQL Server"""
    mock_df = pd.DataFrame({
        'PedidoID': [100, 101],
        'Fecha': ['2026-02-23', '2026-02-24'],
        'Cliente': ['Empresa A', 'Empresa B'],
        'Estado': ['Finalizada', 'Pendiente'],
        'GuiaRemision': ['GR-001', 'GR-002'],
        'TotalVenta': [1500.50, 800.00]
    })
    mock_pandas_read_sql.return_value = mock_df
    
    response = client.get("/vendedores/5/ventas?fecha_inicio=2026-02-01&fecha_fin=2026-02-28&format=csv")
    
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "ventas_vendedor_5_" in response.headers["content-disposition"]
    assert "Empresa A" in response.text
    assert "1500.5" in response.text

def test_top_clientes_vendedor_export_excel(mock_db_connection, mock_pandas_read_sql):
    """Prueba exportación de clientes top a Excel"""
    mock_df = pd.DataFrame({
        'Cliente': ['Empresa C', 'Empresa D'],
        'TotalComprado': [5000.00, 3200.00],
        'CantidadPedidos': [5, 2]
    })
    mock_pandas_read_sql.return_value = mock_df
    
    response = client.get("/vendedores/5/top-clientes?fecha_inicio=2026-02-01&fecha_fin=2026-02-28&format=xlsx")
    
    assert response.status_code == 200
    assert "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" in response.headers["content-type"]
    assert "top_clientes_vendedor_5_" in response.headers["content-disposition"]
    assert response.content.startswith(b'PK\x03\x04')

def test_deudores_vendedor_empty(mock_db_connection, mock_pandas_read_sql):
    """Prueba cuando el vendedor no tiene clientes deudores"""
    mock_pandas_read_sql.return_value = pd.DataFrame()
    
    response = client.get("/vendedores/5/deudores?format=xlsx")
    
    assert response.status_code == 404
    assert response.json() == {"detail": "No se encontraron datos para estos parámetros."}
