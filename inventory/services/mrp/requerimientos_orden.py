"""
Materiales que necesita una orden de producción para completarse (TEX-27, TEX-28).

Fuente única para el motor MRP y para la consulta de requisitos de una orden:
- producto de entrada: lo que falta producir, en relación 1:1 con el peso de salida;
- químicos y colorantes de su fórmula, con la misma dosificación que la descarga
  automática (`calcular_dosificacion_de_orden`). Si ya se descargaron al crear la orden,
  se informan como descontados y el MRP no los vuelve a pedir.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from django.db.models import Sum

from gestion.models import DescargaQuimicoOP, Producto
from gestion.services_formula import calcular_dosificacion_de_orden

from .reglas import CERO, UNIDAD_MRP, pendiente_de_orden

logger = logging.getLogger("inventory.mrp")

_KG = Decimal("0.001")


@dataclass(frozen=True)
class RequerimientoOrden:
    producto: Producto
    cantidad_kg: Decimal
    es_base: bool  # producto de entrada (True) o químico/colorante de la fórmula (False)
    ya_descontado: bool = False  # químico descargado al crear la orden: no se vuelve a pedir


@dataclass
class AnalisisOrden:
    requerimientos: list[RequerimientoOrden] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)


def requerimientos_de_orden(orden) -> AnalisisOrden:
    """Requerimientos de la orden y las advertencias de lo que no se pudo calcular.

    Usa `producido_kg` y `quimicos_descargados` si vienen anotados (ver
    `reglas.ordenes_abiertas`); si no, los consulta.
    """
    analisis = AnalisisOrden()
    producido = getattr(orden, "producido_kg", None)
    if producido is None:
        producido = orden.lotes.aggregate(total=Sum("peso_neto_producido"))["total"] or CERO
    pendiente = pendiente_de_orden(orden, producido)
    if pendiente is None:
        analisis.advertencias.append(
            f"OP {orden.codigo}: sin peso requerido (producción continua); no se calculan sus materiales."
        )
        return analisis

    base = orden.producto_entrada
    if base is not None and pendiente > CERO:
        if base.unidad_medida != UNIDAD_MRP:
            analisis.advertencias.append(_aviso_unidad(base, orden))
        else:
            analisis.requerimientos.append(
                RequerimientoOrden(producto=base, cantidad_kg=pendiente.quantize(_KG), es_base=True)
            )

    if orden.formula_color_id:
        _agregar_quimicos(orden, analisis)
    return analisis


def _agregar_quimicos(orden, analisis):
    try:
        resultado = calcular_dosificacion_de_orden(orden)
    except (ValueError, ArithmeticError):
        logger.warning("No se pudo calcular la dosificación de la OP %s", orden.codigo, exc_info=True)
        analisis.advertencias.append(f"OP {orden.codigo}: no se pudo calcular la dosificación de su fórmula.")
        return

    # Un mismo químico puede repetirse en varias fases: se suma por producto.
    por_producto = defaultdict(lambda: CERO)
    for insumo in resultado.insumos:
        if insumo.producto_id:
            por_producto[insumo.producto_id] += insumo.cantidad_kg
    productos = Producto.objects.in_bulk(por_producto)

    descargados = getattr(orden, "quimicos_descargados", None)
    if descargados is None:
        descargados = DescargaQuimicoOP.objects.filter(orden_produccion=orden, estado="aplicada").exists()

    for producto_id, cantidad in por_producto.items():
        producto = productos.get(producto_id)
        if producto is None or cantidad <= CERO:
            continue
        if producto.unidad_medida != UNIDAD_MRP:
            analisis.advertencias.append(_aviso_unidad(producto, orden))
            continue
        analisis.requerimientos.append(
            RequerimientoOrden(
                producto=producto, cantidad_kg=cantidad.quantize(_KG), es_base=False, ya_descontado=descargados
            )
        )


def _aviso_unidad(producto, orden) -> str:
    return (
        f"{producto.codigo}: se mide en {producto.unidad_medida}, no en {UNIDAD_MRP}; "
        f"no se incluye en el cálculo (OP {orden.codigo})."
    )
