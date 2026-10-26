"""
Reglas compartidas del MRP (ADR-012): qué se compra y qué se fabrica, cuánto hay
disponible en una sede y cuánto le falta a cada orden abierta.
"""

from decimal import Decimal

from django.db.models import DecimalField, Exists, F, OuterRef, Sum, Value
from django.db.models.functions import Coalesce

from gestion.models import DescargaQuimicoOP, OrdenProduccion
from inventory.models import StockBodega

# Clasificación por Producto.tipo. Lo comprado se sugiere comprar; lo fabricado se
# propone producir (Plan MTS). No hay lista de materiales: un producto fabricado no se
# desglosa en compras, salvo a través de las órdenes de producción abiertas.
TIPOS_COMPRADOS = frozenset({"materia_prima", "quimico", "colorante", "insumo"})
TIPOS_FABRICADOS = frozenset({"hilo", "tela", "subproducto"})

ESTADOS_ORDEN_ABIERTA = ("pendiente", "en_proceso")
ESTADOS_PEDIDO_ABIERTO = ("pendiente", "despachado_parcial")

# La dosificación y el stock se manejan en kg; un producto en otra unidad no se mezcla.
UNIDAD_MRP = "kg"

CERO = Decimal("0")
_DECIMAL: DecimalField = DecimalField(max_digits=14, decimal_places=3)


def es_comprado(producto) -> bool:
    return producto.tipo in TIPOS_COMPRADOS


def es_fabricado(producto) -> bool:
    return producto.tipo in TIPOS_FABRICADOS


def stock_disponible_por_producto(sede_id) -> dict[int, Decimal]:
    """Stock libre por producto en las bodegas de la sede: cantidad − comprometido."""
    filas = (
        StockBodega.objects.filter(bodega__sede_id=sede_id)
        .values("producto_id")
        .annotate(disponible=Sum(F("cantidad") - F("stock_comprometido"), output_field=_DECIMAL))
    )
    return {fila["producto_id"]: fila["disponible"] or CERO for fila in filas}


def ordenes_abiertas(sede_id):
    """Órdenes pendientes o en proceso de la sede, con lo producido hasta ahora y si sus
    químicos ya se descargaron (DescargaQuimicoOP aplicada)."""
    descargada = DescargaQuimicoOP.objects.filter(orden_produccion=OuterRef("pk"), estado="aplicada")
    return (
        OrdenProduccion.objects.filter(sede_id=sede_id, estado__in=ESTADOS_ORDEN_ABIERTA)
        .select_related("producto_entrada", "producto_salida", "formula_color", "version_formula")
        .annotate(
            producido_kg=Coalesce(Sum("lotes__peso_neto_producido"), Value(CERO), output_field=_DECIMAL),
            quimicos_descargados=Exists(descargada),
        )
        .order_by("id")
    )


def pendiente_de_orden(orden, producido) -> Decimal | None:
    """Lo que le falta producir a la orden; None si no tiene peso (producción continua)."""
    if orden.peso_neto_requerido is None:
        return None
    return max(orden.peso_neto_requerido - (producido or CERO), CERO)
