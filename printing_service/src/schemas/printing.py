"""
Schemas Pydantic del printing_service.
ISP: un schema por caso de uso, sin lógica de negocio embebida (SRP).
NotaVentaRequest es un DTO de entrada HTTP puro.
"""
from pydantic import BaseModel
from typing import List, Optional


class DetallePedido(BaseModel):
    """Un renglón del pedido con su peso, precio y condición de IVA."""
    producto_descripcion: str
    cantidad: float
    piezas: int
    peso: float
    precio_unitario: float
    incluye_iva: bool = False


class NotaVentaRequest(BaseModel):
    """
    DTO de entrada para generación de nota de venta.
    SRP: solo transporta datos del cliente HTTP al servicio.
    NO contiene lógica de negocio (subtotal/iva/total se calculan en DocumentService).
    """
    id: int
    guia_remision: Optional[str] = None
    fecha_pedido: str
    cliente_nombre: Optional[str] = "Consumidor Final"
    cliente_ruc: Optional[str] = None
    cliente_direccion: Optional[str] = None
    vendedor_nombre: Optional[str] = None
    sede_nombre: Optional[str] = "Matriz"
    empresa_nombre: Optional[str] = "Empresa"
    esta_pagado: bool = False
    valor_retencion: float = 0.0
    detalles: List[DetallePedido]


class NotaVentaContexto(BaseModel):
    """
    Schema enriquecido con cálculos ya realizados por DocumentService.
    Es el objeto que se pasa al template Jinja2 (ISP: schema específico para render).
    """
    id: int
    guia_remision: Optional[str]
    fecha_pedido: str
    fecha_pedido_formatted: str
    cliente_nombre: Optional[str]
    cliente_ruc: Optional[str]
    cliente_direccion: Optional[str]
    vendedor_nombre: Optional[str]
    sede_nombre: Optional[str]
    empresa_nombre: Optional[str]
    esta_pagado: bool
    valor_retencion: float
    detalles: List[DetallePedido]
    subtotal: float
    iva: float
    total: float


class EtiquetaRequest(BaseModel):
    """DTO de entrada para generación de etiqueta ZPL."""
    empresa: Optional[str] = "TexCore Industrial"
    producto_desc: str
    lote_codigo: str
    peso_neto: float
    tara: Optional[float] = 0.0
    peso_bruto: Optional[float] = 0.0
    cantidad_metros: Optional[float] = None
    unidad: Optional[str] = "kg"
    qr_data: str
    # F2: gobernanza de reimpresión/reetiquetado — sello visual y auditoría.
    tipo_evento: Optional[str] = "ORIGINAL"  # ORIGINAL | REIMPRESION | REETIQUETADO
    version: Optional[int] = 1
    motivo: Optional[str] = None
    usuario: Optional[str] = None
    reimpreso: Optional[bool] = False
