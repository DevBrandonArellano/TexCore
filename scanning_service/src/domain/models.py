"""
Domain models: objetos de dominio puros, sin acoplamiento a ORM ni HTTP.
DIP: LoteValidationService depende de estos, no de SQLAlchemy.
"""
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class Producto:
    id: int
    descripcion: str


@dataclass
class OrdenProduccion:
    id: int
    estado: str
    producto_salida: Producto


@dataclass
class Bodega:
    id: int
    nombre: str


@dataclass
class LineaStock:
    """Fila vendible del lote: un lote puede traer productos agregados a mano."""

    producto: Producto
    cantidad: Decimal
    bodega: Bodega


@dataclass
class LoteProduccion:
    id: int
    codigo_lote: str
    orden_produccion: OrdenProduccion
    # Filas vendibles (sin la merma), la del producto del lote primero.
    productos: list[LineaStock] = field(default_factory=list)


@dataclass
class StockBodega:
    id: int
    cantidad: Decimal
    bodega: Bodega
