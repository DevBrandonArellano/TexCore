"""
Motor MRP por sede (TEX-27, ADR-012).

Una ejecución recalcula, para una sede, los requerimientos de material comprado de sus
órdenes abiertas y las sugerencias de compra (informativas):

    sugerido = lo que piden las órdenes + stock mínimo − disponible   (si es > 0)

Corre en una transacción con la fila de la sede bloqueada, así dos ejecuciones de la
misma sede no se pisan; reemplaza solo los resultados de esa sede. Si falla, la
transacción se revierte (quedan los resultados anteriores) y la ejecución se registra
como fallida, con el detalle técnico en el log.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from gestion.models import Producto, Sede
from inventory.models import MRPEjecucion, OrdenCompraSugerida, RequerimientoMaterial

from .necesidades_produccion import necesidades_produccion
from .reglas import CERO, TIPOS_COMPRADOS, es_comprado, ordenes_abiertas, stock_disponible_por_producto
from .requerimientos_orden import requerimientos_de_orden

logger = logging.getLogger("inventory.mrp")

MENSAJE_FALLO = "Error interno al calcular el MRP de la sede. El detalle quedó registrado en el log del servidor."


@dataclass
class _CalculoCompras:
    requerimientos: list[RequerimientoMaterial] = field(default_factory=list)
    sugerencias: list[OrdenCompraSugerida] = field(default_factory=list)
    advertencias: list[str] = field(default_factory=list)


class MRPEngine:
    @classmethod
    def ejecutar(cls, sede, usuario=None) -> MRPEjecucion:
        inicio = timezone.now()
        try:
            with transaction.atomic():
                # Serializa las ejecuciones de la sede (no-op en SQLite).
                Sede.objects.select_for_update().filter(pk=sede.pk).exists()
                RequerimientoMaterial.objects.filter(sede=sede).delete()
                OrdenCompraSugerida.objects.filter(sede=sede).delete()

                calculo = cls._calcular_compras(sede)
                ejecucion = MRPEjecucion.objects.create(
                    sede=sede,
                    iniciada_por=usuario,
                    inicio=inicio,
                    fin=timezone.now(),
                    estado=MRPEjecucion.ESTADO_COMPLETADA,
                    requerimientos=len(calculo.requerimientos),
                    sugerencias_compra=len(calculo.sugerencias),
                    productos_a_producir=len(necesidades_produccion(sede.pk)),
                    advertencias=calculo.advertencias,
                )
                for requerimiento in calculo.requerimientos:
                    requerimiento.ejecucion = ejecucion
                for sugerencia in calculo.sugerencias:
                    sugerencia.ejecucion = ejecucion
                RequerimientoMaterial.objects.bulk_create(calculo.requerimientos, batch_size=500)
                OrdenCompraSugerida.objects.bulk_create(calculo.sugerencias, batch_size=500)
        except Exception:
            logger.exception("Error en la ejecución del MRP", extra={"sd": {"sede_id": sede.pk}})
            return MRPEjecucion.objects.create(
                sede=sede,
                iniciada_por=usuario,
                inicio=inicio,
                fin=timezone.now(),
                estado=MRPEjecucion.ESTADO_FALLIDA,
                mensaje_error=MENSAJE_FALLO,
            )
        logger.info(
            "MRP de la sede %s: %s requerimientos, %s sugerencias, %s advertencias",
            sede.pk,
            ejecucion.requerimientos,
            ejecucion.sugerencias_compra,
            len(ejecucion.advertencias),
        )
        return ejecucion

    @staticmethod
    def _calcular_compras(sede) -> _CalculoCompras:
        calculo = _CalculoCompras()
        requerido: defaultdict[int, Decimal] = defaultdict(lambda: CERO)
        productos = {}
        for orden in ordenes_abiertas(sede.pk):
            analisis = requerimientos_de_orden(orden)
            calculo.advertencias.extend(analisis.advertencias)
            for req in analisis.requerimientos:
                if req.ya_descontado or not es_comprado(req.producto):
                    continue
                requerido[req.producto.pk] += req.cantidad_kg
                productos[req.producto.pk] = req.producto
                calculo.requerimientos.append(
                    RequerimientoMaterial(
                        orden_produccion=orden,
                        producto_requerido=req.producto,
                        cantidad_necesaria=req.cantidad_kg,
                        sede=sede,
                        fecha_requerida=orden.fecha_inicio_planificada,
                    )
                )

        # Stock de seguridad: los comprados de la sede (o globales) con mínimo, aunque
        # ninguna orden los pida.
        for producto in Producto.objects.filter(
            Q(sede=sede) | Q(sede__isnull=True),
            tipo__in=TIPOS_COMPRADOS,
            stock_minimo__gt=0,
        ):
            productos.setdefault(producto.pk, producto)

        disponible = stock_disponible_por_producto(sede.pk)
        for producto_id, producto in productos.items():
            minimo = producto.stock_minimo or CERO
            libre = disponible.get(producto_id, CERO)
            sugerido = requerido[producto_id] + minimo - libre
            if sugerido > CERO:
                calculo.sugerencias.append(
                    OrdenCompraSugerida(
                        producto=producto,
                        sede=sede,
                        requerido=requerido[producto_id],
                        stock_minimo=minimo,
                        stock_disponible=libre,
                        cantidad_sugerida=sugerido,
                    )
                )
        return calculo
