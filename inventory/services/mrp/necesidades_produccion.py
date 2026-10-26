"""
Necesidad de producción de los productos fabricados de una sede (ADR-012). Alimenta
«Crear Plan desde Déficits» del Plan Maestro (MTS):

    necesidad = demanda de pedidos + demanda interna + stock mínimo
                − disponible − en producción

- Demanda de pedidos: lo pendiente de los pedidos abiertos, por pedido y producto:
  peso pedido − max(despachado, reservado). Al despachar se libera el stock
  comprometido pero no `cantidad_fabricada`; el máximo evita restar dos veces lo
  reservado y luego despachado (regla conservadora).
- Demanda interna: lo que les falta a las órdenes abiertas cuyo producto de entrada se
  fabrica en la planta.
- En producción: lo que les falta a las órdenes abiertas que fabrican el producto.

Se calcula en vivo con un número fijo de consultas, sin importar cuántos pedidos u
órdenes haya.
"""

from collections import defaultdict
from decimal import Decimal

from django.db.models import Q, Sum

from gestion.models import DetallePedido, Producto, Sede
from inventory.models import DetalleHistorialDespacho

from .reglas import (
    CERO,
    ESTADOS_PEDIDO_ABIERTO,
    TIPOS_FABRICADOS,
    ordenes_abiertas,
    pendiente_de_orden,
    stock_disponible_por_producto,
)

_Q4 = Decimal("0.0001")


def necesidades_produccion(sede_id) -> list[dict]:
    demanda_pedidos = _demanda_de_pedidos(sede_id)
    demanda_interna: defaultdict[int, Decimal] = defaultdict(lambda: CERO)
    en_produccion: defaultdict[int, Decimal] = defaultdict(lambda: CERO)
    for orden in ordenes_abiertas(sede_id):
        pendiente = pendiente_de_orden(orden, orden.producido_kg)
        if pendiente is None:
            continue
        if orden.producto_entrada_id and orden.producto_entrada.tipo in TIPOS_FABRICADOS:
            demanda_interna[orden.producto_entrada_id] += pendiente
        if orden.producto_salida_id:
            en_produccion[orden.producto_salida_id] += pendiente

    con_minimo = Producto.objects.filter(
        Q(sede_id=sede_id) | Q(sede__isnull=True),
        tipo__in=TIPOS_FABRICADOS,
        stock_minimo__gt=0,
    ).values_list("id", flat=True)
    candidatos = set(demanda_pedidos) | set(demanda_interna) | set(con_minimo)
    if not candidatos:
        return []

    productos = Producto.objects.in_bulk(candidatos)
    disponible = stock_disponible_por_producto(sede_id)
    sede_nombre = Sede.objects.filter(pk=sede_id).values_list("nombre", flat=True).first()

    resultado = []
    for producto_id in candidatos:
        producto = productos[producto_id]
        if producto.tipo not in TIPOS_FABRICADOS:
            continue
        stock_minimo = producto.stock_minimo or CERO
        deficit = (
            demanda_pedidos.get(producto_id, CERO)
            + demanda_interna[producto_id]
            + stock_minimo
            - disponible.get(producto_id, CERO)
            - en_produccion[producto_id]
        )
        if deficit <= CERO:
            continue
        resultado.append(
            {
                "sede_id": sede_id,
                "sede_nombre": sede_nombre,
                "producto_id": producto_id,
                "producto_codigo": producto.codigo,
                "producto_descripcion": producto.descripcion,
                "tipo": producto.tipo,
                "unidad_medida": producto.unidad_medida,
                "stock_actual": disponible.get(producto_id, CERO).quantize(_Q4),
                "stock_minimo": stock_minimo.quantize(_Q4),
                "demanda_pedidos": demanda_pedidos.get(producto_id, CERO).quantize(_Q4),
                "demanda_interna": demanda_interna[producto_id].quantize(_Q4),
                "en_produccion": en_produccion[producto_id].quantize(_Q4),
                "deficit": deficit.quantize(_Q4),
            }
        )
    resultado.sort(key=lambda n: (n["producto_descripcion"], n["producto_id"]))
    return resultado


def _demanda_de_pedidos(sede_id) -> dict[int, Decimal]:
    abiertos = {"pedido_venta__sede_id": sede_id, "pedido_venta__estado__in": ESTADOS_PEDIDO_ABIERTO}
    lineas = (
        DetallePedido.objects.filter(producto__tipo__in=TIPOS_FABRICADOS, **abiertos)
        .values("pedido_venta_id", "producto_id")
        .annotate(pedido=Sum("peso"), reservado=Sum("cantidad_fabricada"))
    )
    despachado = {
        (fila["pedido_id"], fila["producto_id"]): fila["total"] or CERO
        for fila in DetalleHistorialDespacho.objects.filter(
            pedido__sede_id=sede_id,
            pedido__estado__in=ESTADOS_PEDIDO_ABIERTO,
            es_devolucion=False,
        )
        .values("pedido_id", "producto_id")
        .annotate(total=Sum("peso"))
    }
    demanda: defaultdict[int, Decimal] = defaultdict(lambda: CERO)
    for linea in lineas:
        cubierto = max(
            despachado.get((linea["pedido_venta_id"], linea["producto_id"]), CERO), linea["reservado"] or CERO
        )
        demanda[linea["producto_id"]] += max((linea["pedido"] or CERO) - cubierto, CERO)
    return dict(demanda)
