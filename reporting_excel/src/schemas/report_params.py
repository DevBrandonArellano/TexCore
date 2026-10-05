"""
Schemas Pydantic para parámetros de los reportes.
ISP: un schema por caso de uso. Facilita testing de validación de parámetros.
"""
from datetime import date

from pydantic import BaseModel, field_validator


class KardexParams(BaseModel):
    bodega_id: int
    producto_id: int | None = None
    proveedor_id: int | None = None
    fecha_inicio: date | None = None
    fecha_fin: date | None = None
    lote_codigo: str | None = None
    format: str = "xlsx"

    @field_validator("format")
    @classmethod
    def formato_valido(cls, v: str) -> str:
        if v not in ("xlsx", "csv"):
            raise ValueError("El formato debe ser 'xlsx' o 'csv'")
        return v


class RangoFechaParams(BaseModel):
    """Parámetros comunes para reportes con rango de fechas y sede opcional."""
    fecha_inicio: date
    fecha_fin: date
    sede_id: int | None = None
    format: str = "xlsx"

    @field_validator("format")
    @classmethod
    def formato_valido(cls, v: str) -> str:
        if v not in ("xlsx", "csv"):
            raise ValueError("El formato debe ser 'xlsx' o 'csv'")
        return v


class VendedorParams(BaseModel):
    """Parámetros para reportes por vendedor."""
    vendedor_id: int
    fecha_inicio: date
    fecha_fin: date
    format: str = "xlsx"


class StockParams(BaseModel):
    bodega_id: int
    producto_id: int | None = None
    format: str = "xlsx"
