"""
Domain models: objetos de dominio puros, sin acoplamiento a ORM ni HTTP.
DIP: LoteValidationService depende de estos, no de SQLAlchemy.
"""

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class AlcanceSede:
    """
    Sede del usuario que escanea (OWASP API1).

    La pone nginx en cabeceras después de verificar la sesión contra Django
    (`auth_request`); el servicio la reenvía a la internal_api para que un lote de otra
    sede responda igual que uno inexistente. `ve_todas` es el usuario que ve todas las
    sedes (admin_sistemas, ejecutivo); sin sede y sin `ve_todas` no ve ningún lote.
    """

    sede_id: int | None
    ve_todas: bool


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
    # Sin stock porque otro despachador ya se lo llevó: quién, cuándo y en qué despacho
    # (lo arma el backend, inventory/services/despacho_lote.py).
    motivo_sin_stock: str | None = None


@dataclass
class StockBodega:
    id: int
    cantidad: Decimal
    bodega: Bodega
