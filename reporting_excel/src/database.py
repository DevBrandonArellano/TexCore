import pyodbc
import os
import logging
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

# Configuración via variables de entorno, usando defaults si no se proveen (para pasarlo del docker-compose)
DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = os.getenv("DB_PORT", "1433")
DB_NAME = os.getenv("DB_NAME", "texcore_db")
DB_USER = os.getenv("DB_USER", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

def get_connection_string() -> str:
    """Construye la cadena de conexión de pyodbc para conectar a MS SQL Server usando TrustServerCertificate=yes para entornos locales."""
    conn_str = (
        f"DRIVER={{{DB_DRIVER}}};"
        f"SERVER={DB_HOST},{DB_PORT};"
        f"DATABASE={DB_NAME};"
        f"UID={DB_USER};"
        f"PWD={DB_PASSWORD};"
        f"TrustServerCertificate=yes;"
    )
    return conn_str

def get_db_connection():
    """Generador que retorna una conexión a la BD"""
    conn = None
    try:
        conn_str = get_connection_string()
        conn = pyodbc.connect(conn_str)
        yield conn
    except Exception as e:
        logger.error(f"Error conectando a la base de datos: {e}")
        raise
    finally:
        if conn:
            conn.close()

def execute_sp_to_dataframe(sp_query: str, params: Optional[tuple] = None) -> pd.DataFrame:
    """
    Ejecuta un procedimiento almacenado u otra query usando pandas read_sql.
    Esto devuelve un DataFrame directamente.
    """
    conn_str = get_connection_string()
    try:
        # En pyodbc, pd.read_sql maneja muy bien la conexión si le pasamos sqlalchemy engine
        # Pero podemos usar la conexión directamente de pyodbc
        with pyodbc.connect(conn_str) as conn:
            # Añadir conversor para tipo -155 (DATETIMEOFFSET) que lanza error nativo en pyodbc
            def handle_datetimeoffset(dto_value):
                # Usualmente pyodbc trae bytes o bytearray para tipos desconocidos, o simplemente string
                if isinstance(dto_value, bytes):
                    return dto_value.decode('utf-16le', errors='ignore')
                return str(dto_value)
            
            conn.add_output_converter(-155, handle_datetimeoffset)
            
            if params:
                df = pd.read_sql(sp_query, conn, params=params)
            else:
                df = pd.read_sql(sp_query, conn)
            return df
    except Exception as e:
        logger.error(f"Error ejecutando SP {sp_query}: {e}")
        raise
