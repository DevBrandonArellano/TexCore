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


# ---------------------------------------------------------------------------
# ReporteAvance — DTO de renderizado para reporte de avance de producción
# ---------------------------------------------------------------------------

class DetalleAvance(BaseModel):
    """
    Renglón individual del reporte de avance de producción.
    ISP: schema mínimo con solo los campos que el template necesita renderizar.
    """
    orden: str
    producto: str
    lote: str
    maquina: str
    operario: str
    kilos: float
    porcentaje_avance: float
    estado: str


class ReporteAvanceRequest(BaseModel):
    """
    DTO de entrada para generación de reporte de avance de producción.
    SRP: transporta metadatos de filtros y filas — cero lógica de negocio.
    Las agregaciones (totales, promedios) se calculan en DocumentService.
    """
    empresa_nombre: Optional[str] = "Empresa"
    sede_nombre: Optional[str] = "Matriz"
    # Metadatos de filtros aplicados (pueden ser None si el filtro no se usó)
    fecha_desde: Optional[str] = None
    fecha_hasta: Optional[str] = None
    maquina_filtro: Optional[str] = None
    operario_filtro: Optional[str] = None
    generado_en: str  # ISO datetime del momento de generación
    detalles: List[DetalleAvance]


# ---------------------------------------------------------------------------
# BalanceMasas — DTO de renderizado para balance de masas mensual
# ---------------------------------------------------------------------------

class DetalleBalanceMasas(BaseModel):
    """
    Renglón individual del balance de masas.
    ISP: schema mínimo con solo los campos que el template necesita renderizar.
    El campo `is_negativo` controla la clase CSS de alerta en el PDF.
    """
    codigo: str
    descripcion: str
    inventario_inicial: float
    produccion: float
    egresos: float
    stock_actual: float
    is_negativo: bool = False  # True → fila marcada visualmente en rojo en el PDF


class BalanceMasasRequest(BaseModel):
    """
    DTO de entrada para generación de balance de masas mensual.
    SRP: solo transporta mes, sede y filas de detalle, sin cálculos embebidos.
    """
    empresa_nombre: Optional[str] = "Empresa"
    sede_nombre: Optional[str] = "Matriz"
    mes: str          # Ej. "Julio 2025" — formateado para visualización directa
    generado_en: str  # ISO datetime del momento de generación
    detalles: List[DetalleBalanceMasas]


# ---------------------------------------------------------------------------
# HistorialDespachos — DTO de renderizado para el listado impreso del
# historial de despachos (rol Despacho), filtrado por rango de fechas.
# ---------------------------------------------------------------------------

class DetalleDespachoResumen(BaseModel):
    """Una fila del reporte de historial de despachos."""
    id: int
    fecha_despacho: str  # ya formateada por Django, dd/mm/YYYY HH:MM
    usuario_nombre: Optional[str] = None
    pedidos: str  # guías/clientes concatenados para mostrar en una sola columna
    total_bultos: int
    total_peso: float


class HistorialDespachosRequest(BaseModel):
    """DTO de entrada para el reporte impreso del historial de despachos."""
    empresa_nombre: Optional[str] = "Empresa"
    sede_nombre: Optional[str] = "Matriz"
    fecha_desde: Optional[str] = None
    fecha_hasta: Optional[str] = None
    generado_en: str
    despachos: List[DetalleDespachoResumen]


# ---------------------------------------------------------------------------
# GuiaRemisionRequest — documento INFORMATIVO de acompañamiento de mercadería
# (no es un comprobante electrónico autorizado por el SRI: la facturación
# electrónica la maneja software externo — ver
# gestion/tests/test_anticipos_pagos_parciales_p1.py). Incluye los campos que
# exige el SRI para que el conductor lo lleve físicamente en el transporte.
# ---------------------------------------------------------------------------

class DetalleMercaderiaGuia(BaseModel):
    """Un renglón de mercadería transportada."""
    codigo: Optional[str] = None
    descripcion: str
    cantidad: float
    unidad: Optional[str] = "kg"


class DestinatarioGuia(BaseModel):
    """Un destinatario de la guía — puede haber varios en un mismo traslado."""
    identificacion: Optional[str] = None
    razon_social: str
    direccion: Optional[str] = None
    documento_sustento: Optional[str] = None  # ej. nº de pedido/guía interna relacionada


class GuiaRemisionRequest(BaseModel):
    """DTO de entrada para la Guía de Remisión (PDF informativo)."""
    numero: str  # numeración interna, ej. "001-001-000000002"
    fecha_emision: str
    empresa_nombre: Optional[str] = "Empresa"
    empresa_ruc: Optional[str] = None
    punto_partida: str
    motivo_traslado: str
    fecha_inicio_transporte: str
    fecha_fin_transporte: str
    transporte_propio: bool = True
    transportista_nombre: Optional[str] = None
    transportista_ruc: Optional[str] = None
    placa_vehiculo: Optional[str] = None
    destinatarios: List[DestinatarioGuia]
    detalles: List[DetalleMercaderiaGuia]


# ---------------------------------------------------------------------------
# EtiquetaRequest — DTO de entrada para etiquetas (sin cambios)
# ---------------------------------------------------------------------------

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
    # F6: lotes que representan varias piezas físicas (ej. 12 rollos por caja,
    # LoteProduccion.unidades_empaque) — cada pieza imprime su propia etiqueta
    # física, numerada "PIEZA i/N", compartiendo el mismo lote_codigo/QR.
    pieza: Optional[int] = None
    piezas_totales: Optional[int] = None


class EtiquetaContexto(EtiquetaRequest):
    """
    Contexto enriquecido para el template PDF de etiqueta, generado por
    LabelService a partir de un EtiquetaRequest.
    ISP: agrega solo lo que el PDF necesita para pintar el código de barras y
    el QR como imágenes (WeasyPrint no dibuja símbolos de barcode/QR por sí
    mismo — solo <img>). None si la generación de la imagen falló, para que
    el template pueda degradar con gracia en vez de romper el PDF completo.
    """
    barcode_image: Optional[str] = None  # PNG Code128 en base64 (sin prefijo data:)
    qr_image: Optional[str] = None       # PNG QR en base64 (sin prefijo data:)
