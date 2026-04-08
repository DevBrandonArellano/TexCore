"""
conftest.py — Mocks de infraestructura para el scanning_service.

El scanning_service depende de SQL Server via pyodbc. Para los tests
unitarios se sustituye el engine y SessionLocal por mocks en memoria
ANTES de que se importe src.main, evitando que SQLAlchemy intente
conectarse a la base de datos real.
"""
import sys
import types
from unittest.mock import MagicMock, patch

# --------------------------------------------------------------------------
# Crear un módulo falso para src.database ANTES de que se importe src.main
# Esto evita que SQLAlchemy intente conectar con SQL Server en tiempo de import
# --------------------------------------------------------------------------
fake_database = types.ModuleType("scanning_service.src.database")
fake_database.SessionLocal = MagicMock
fake_database.engine = MagicMock()
fake_database.Base = MagicMock()

# Registrar el módulo falso en sys.modules con ambas claves posibles
sys.modules["scanning_service.src.database"] = fake_database
sys.modules["src.database"] = fake_database

# Hacer lo mismo para src.models — se importa con modelos SQLAlchemy
fake_models = types.ModuleType("scanning_service.src.models")


class _FakeProduct:
    id = 1
    descripcion = "Hilo Texturizado"


class _FakeBodega:
    id = 10
    nombre = "Bodega Central"


class _FakeOrden:
    producto = _FakeProduct()


class _FakeLote:
    id = 1
    codigo_lote = "LOTE-00001"
    orden_produccion = _FakeOrden()


class _FakeStock:
    cantidad = 50
    bodega = _FakeBodega()
    lote_id = 1


fake_models.Base = MagicMock()
fake_models.LoteProduccion = _FakeLote
fake_models.StockBodega = _FakeStock
fake_models.Producto = _FakeProduct
fake_models.Bodega = _FakeBodega
fake_models.OrdenProduccion = _FakeOrden

sys.modules["scanning_service.src.models"] = fake_models
sys.modules["src.models"] = fake_models
