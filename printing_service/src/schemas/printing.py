"""
Schemas Pydantic del printing_service.
ISP: un schema por caso de uso, sin lógica de negocio embebida (SRP).
NotaVentaRequest es un DTO de entrada HTTP puro.
"""

from pydantic import BaseModel


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
    guia_remision: str | None = None
    fecha_pedido: str
    cliente_nombre: str | None = "Consumidor Final"
    cliente_ruc: str | None = None
    cliente_direccion: str | None = None
    vendedor_nombre: str | None = None
    sede_nombre: str | None = "Matriz"
    empresa_nombre: str | None = "Empresa"
    esta_pagado: bool = False
    valor_retencion: float = 0.0
    detalles: list[DetallePedido]


class NotaVentaContexto(BaseModel):
    """
    Schema enriquecido con cálculos ya realizados por DocumentService.
    Es el objeto que se pasa al template Jinja2 (ISP: schema específico para render).
    """
    id: int
    guia_remision: str | None
    fecha_pedido: str
    fecha_pedido_formatted: str
    cliente_nombre: str | None
    cliente_ruc: str | None
    cliente_direccion: str | None
    vendedor_nombre: str | None
    sede_nombre: str | None
    empresa_nombre: str | None
    esta_pagado: bool
    valor_retencion: float
    detalles: list[DetallePedido]
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
    empresa_nombre: str | None = "Empresa"
    sede_nombre: str | None = "Matriz"
    # Metadatos de filtros aplicados (pueden ser None si el filtro no se usó)
    fecha_desde: str | None = None
    fecha_hasta: str | None = None
    maquina_filtro: str | None = None
    operario_filtro: str | None = None
    generado_en: str  # ISO datetime del momento de generación
    detalles: list[DetalleAvance]


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
    empresa_nombre: str | None = "Empresa"
    sede_nombre: str | None = "Matriz"
    mes: str          # Ej. "Julio 2025" — formateado para visualización directa
    generado_en: str  # ISO datetime del momento de generación
    detalles: list[DetalleBalanceMasas]


# ---------------------------------------------------------------------------
# HistorialDespachos — DTO de renderizado para el listado impreso del
# historial de despachos (rol Despacho), filtrado por rango de fechas.
# ---------------------------------------------------------------------------

class DetalleDespachoResumen(BaseModel):
    """Una fila del reporte de historial de despachos."""
    id: int
    fecha_despacho: str  # ya formateada por Django, dd/mm/YYYY HH:MM
    usuario_nombre: str | None = None
    pedidos: str  # guías/clientes concatenados para mostrar en una sola columna
    total_bultos: int
    total_peso: float


class HistorialDespachosRequest(BaseModel):
    """DTO de entrada para el reporte impreso del historial de despachos."""
    empresa_nombre: str | None = "Empresa"
    sede_nombre: str | None = "Matriz"
    fecha_desde: str | None = None
    fecha_hasta: str | None = None
    generado_en: str
    despachos: list[DetalleDespachoResumen]


# ---------------------------------------------------------------------------
# ProduccionPorProducto — DTO de renderizado para el listado impreso de
# producción agrupada por producto (rol Ejecutivo), filtrado por rango de
# fechas.
# ---------------------------------------------------------------------------

class DetalleProduccionProducto(BaseModel):
    """Una fila del reporte de producción por producto (totales del rango)."""
    producto_codigo: str
    producto_nombre: str
    kg_total: float
    num_lotes: int


class ProduccionPorProductoRequest(BaseModel):
    """DTO de entrada para el reporte impreso de producción por producto."""
    empresa_nombre: str | None = "Empresa"
    sede_nombre: str | None = "Matriz"
    fecha_inicio: str | None = None
    fecha_fin: str | None = None
    generado_en: str
    productos: list[DetalleProduccionProducto]


# ---------------------------------------------------------------------------
# GuiaRemisionRequest — documento INFORMATIVO de acompañamiento de mercadería
# (no es un comprobante electrónico autorizado por el SRI: la facturación
# electrónica la maneja software externo — ver
# gestion/tests/test_anticipos_pagos_parciales_p1.py). Incluye los campos que
# exige el SRI para que el conductor lo lleve físicamente en el transporte.
# ---------------------------------------------------------------------------

class DetalleMercaderiaGuia(BaseModel):
    """Un renglón de mercadería transportada."""
    codigo: str | None = None
    descripcion: str
    cantidad: float
    unidad: str | None = "kg"


class DestinatarioGuia(BaseModel):
    """Un destinatario de la guía — puede haber varios en un mismo traslado."""
    identificacion: str | None = None
    razon_social: str
    direccion: str | None = None
    documento_sustento: str | None = None  # ej. nº de pedido/guía interna relacionada


class GuiaRemisionRequest(BaseModel):
    """DTO de entrada para la Guía de Remisión (PDF informativo)."""
    numero: str  # numeración interna, ej. "001-001-000000002"
    fecha_emision: str
    empresa_nombre: str | None = "Empresa"
    empresa_ruc: str | None = None
    punto_partida: str
    motivo_traslado: str
    fecha_inicio_transporte: str
    fecha_fin_transporte: str
    transporte_propio: bool = True
    transportista_nombre: str | None = None
    transportista_ruc: str | None = None
    placa_vehiculo: str | None = None
    destinatarios: list[DestinatarioGuia]
    detalles: list[DetalleMercaderiaGuia]


# ---------------------------------------------------------------------------
# EtiquetaRequest — DTO de entrada para etiquetas (sin cambios)
# ---------------------------------------------------------------------------

class EtiquetaRequest(BaseModel):
    """DTO de entrada para generación de etiqueta ZPL."""
    empresa: str | None = "TexCore Industrial"
    producto_desc: str
    lote_codigo: str
    peso_neto: float
    tara: float | None = 0.0
    peso_bruto: float | None = 0.0
    cantidad_metros: float | None = None
    unidad: str | None = "kg"
    qr_data: str
    # F2: gobernanza de reimpresión/reetiquetado — sello visual y auditoría.
    tipo_evento: str | None = "ORIGINAL"  # ORIGINAL | REIMPRESION | REETIQUETADO
    version: int | None = 1
    motivo: str | None = None
    usuario: str | None = None
    reimpreso: bool | None = False
    # F6: lotes que representan varias piezas físicas (ej. 12 rollos por caja,
    # LoteProduccion.unidades_empaque) — cada pieza imprime su propia etiqueta
    # física, numerada "PIEZA i/N", compartiendo el mismo lote_codigo/QR.
    pieza: int | None = None
    piezas_totales: int | None = None


class EtiquetaContexto(EtiquetaRequest):
    """
    Contexto enriquecido para el template PDF de etiqueta, generado por
    LabelService a partir de un EtiquetaRequest.
    ISP: agrega solo lo que el PDF necesita para pintar el código de barras y
    el QR como imágenes (WeasyPrint no dibuja símbolos de barcode/QR por sí
    mismo — solo <img>). None si la generación de la imagen falló, para que
    el template pueda degradar con gracia en vez de romper el PDF completo.
    """
    barcode_image: str | None = None  # PNG Code128 en base64 (sin prefijo data:)
    qr_image: str | None = None       # PNG QR en base64 (sin prefijo data:)
