"""
Schemas Pydantic específicos para el caso de uso de validación de lotes.
SRP: solo definen la forma de los datos de entrada/salida HTTP.
ISP: un schema por caso de uso, sin lógica de negocio embebida.
"""
from typing import Optional
from pydantic import BaseModel, field_validator


class ValidateRequest(BaseModel):
    """Código escaneado que se desea validar (QR o código de barras)."""

    code: str

    @field_validator("code")
    @classmethod
    def code_no_vacio(cls, v: str) -> str:
        """BVA: rechaza strings vacíos o de solo espacios."""
        if not v.strip():
            raise ValueError("El código no puede estar vacío")
        return v.strip()


class LoteInfo(BaseModel):
    """Información del lote retornada cuando la validación es exitosa."""

    codigo: str
    producto_id: int
    producto_nombre: str
    peso: str
    bodega_id: int
    bodega_nombre: str


class ValidateResponse(BaseModel):
    """Respuesta del endpoint /validate."""

    valid: bool
    lote: Optional[LoteInfo] = None
    reason: Optional[str] = None
