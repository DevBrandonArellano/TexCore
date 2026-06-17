"""
Domain models: objetos de dominio puros, sin acoplamiento a ORM ni HTTP.
DIP: LoteValidationService depende de estos, no de SQLAlchemy.
"""
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class Producto:
    id: int
    descripcion: str


@dataclass
class OrdenProduccion:
    id: int
    estado: str
    producto: Producto


@dataclass
class LoteProduccion:
    id: int
    codigo_lote: str
    orden_produccion: OrdenProduccion


@dataclass
class Bodega:
    id: int
    nombre: str


@dataclass
class StockBodega:
    id: int
    cantidad: Decimal
    bodega: Bodega
