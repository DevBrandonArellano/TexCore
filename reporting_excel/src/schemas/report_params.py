"""
Schemas Pydantic para parámetros de los reportes.
ISP: un schema por caso de uso. Facilita testing de validación de parámetros.
"""
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import date


class KardexParams(BaseModel):
    bodega_id: int
    producto_id: Optional[int] = None
    proveedor_id: Optional[int] = None
    fecha_inicio: Optional[date] = None
    fecha_fin: Optional[date] = None
    lote_codigo: Optional[str] = None
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
    sede_id: Optional[int] = None
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
    producto_id: Optional[int] = None
    format: str = "xlsx"
