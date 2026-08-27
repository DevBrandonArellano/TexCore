"""
RUP - Capa de Servicio: ProduccionKPIService
============================================
Artefacto   : Diseño de Componentes
Módulo      : Producción / KPIs Ejecutivos
Patrón      : Service Layer + Facade (agrega múltiples fuentes de datos en un único contrato)
Principios  : SOLID — Responsabilidad única (S), Abierto/Cerrado (O), Inversión de dependencias (D)

Responsabilidad: Centralizar todos los cálculos de KPIs de producción para la vista
ejecutiva. Ninguna vista debe computar datos de producción directamente.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from django.db.models import (
    Avg,
    Count,
    DurationField,
    ExpressionWrapper,
    F,
    Sum,
)
from django.utils import timezone

from gestion.models import LoteProduccion, OrdenProduccion

# RFC 5424: logger bajo el namespace 'gestion' — capturado por el handler de settings.py
logger = logging.getLogger("gestion.services.produccion_kpi")


# ---------------------------------------------------------------------------
# Value Objects (inmutables, sin lógica de negocio)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TendenciaDia:
    """Un punto de la serie temporal de producción diaria."""
    fecha: str          # ISO date "YYYY-MM-DD"
    kg: Decimal


@dataclass(frozen=True)
class OpsEstado:
    """Distribución de Órdenes de Producción por estado."""
    pendiente: int = 0
    en_proceso: int = 0
    finalizada: int = 0


@dataclass(frozen=True)
class ProduccionProductoItem:
    """Un producto con su producción total agregada en un rango de fechas."""
    producto_id: int
    producto_codigo: str
    producto_nombre: str
    kg_total: Decimal
    num_lotes: int


@dataclass(frozen=True)
class ProduccionKPIs:
    """
    Contrato de salida del servicio. Inmutable para garantizar consistencia
    entre capa de servicio y capa de presentación (OCP).
    """
    ops_estado: OpsEstado
    kg_hoy: Decimal
    kg_semana: Decimal
    kg_mes: Decimal
    tiempo_promedio_lote_min: float
    tendencia_30d: list[TendenciaDia] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Servicio
# ---------------------------------------------------------------------------

class ProduccionKPIService:
    """
    Calcula KPIs de producción filtrados opcionalmente por sede.

    Uso:
        service = ProduccionKPIService(sede_id=3)
        kpis = service.obtener_kpis()

    Principio de Inversión de Dependencias: el servicio depende de
    abstracciones (QuerySets de Django ORM), no de implementaciones concretas.
    """

    def __init__(self, sede_id: Optional[int] = None) -> None:
        self._sede_id = sede_id

    # ------------------------------------------------------------------
    # Interfaz pública
    # ------------------------------------------------------------------

    def obtener_kpis(self, skip_tendencia: bool = False) -> ProduccionKPIs:
        """Punto de entrada único — Fachada sobre los métodos privados."""
        hoy = timezone.localdate()
        logger.info(
            "Calculando KPIs de producción",
            extra={'sd': {'sede_id': str(self._sede_id or 'all'), 'fecha': hoy.isoformat()}},
        )
        try:
            result = ProduccionKPIs(
                ops_estado=self._ops_por_estado(),
                kg_hoy=self._kg_lotes(hoy, hoy),
                kg_semana=self._kg_lotes(hoy - timedelta(days=6), hoy),
                kg_mes=self._kg_lotes(hoy.replace(day=1), hoy),
                tiempo_promedio_lote_min=self._tiempo_promedio_lote(),
                tendencia_30d=[] if skip_tendencia else self._tendencia_diaria(hoy - timedelta(days=29), hoy),
            )
        except Exception as exc:
            logger.error(
                "Error calculando KPIs de producción: %s", exc,
                extra={'sd': {'sede_id': str(self._sede_id or 'all'), 'error': type(exc).__name__}},
                exc_info=True,
            )
            raise
        logger.info(
            "KPIs de producción calculados — kg_mes=%s ops_pendiente=%s",
            result.kg_mes,
            result.ops_estado.pendiente,
            extra={
                'sd': {
                    'sede_id': str(self._sede_id or 'all'),
                    'kg_mes': str(result.kg_mes),
                    'ops_pendiente': str(result.ops_estado.pendiente),
                    'ops_en_proceso': str(result.ops_estado.en_proceso),
                }
            },
        )
        return result

    def obtener_tendencia(self) -> list[TendenciaDia]:
        """Endpoint dedicado para la tendencia de 30 días (usado independientemente)."""
        hoy = timezone.localdate()
        return self._tendencia_diaria(hoy - timedelta(days=29), hoy)

    def obtener_produccion_por_producto(
        self, fecha_inicio: date, fecha_fin: date
    ) -> list[ProduccionProductoItem]:
        """Producción agregada por producto en el rango — drill-down ejecutivo (CU-EJ-08)."""
        return self._produccion_por_producto(fecha_inicio, fecha_fin)

    def obtener_historial_producto(
        self, producto_id: int, fecha_inicio: date, fecha_fin: date
    ) -> list[TendenciaDia]:
        """Serie diaria de kg producidos de UN producto — gráfica de drill-down (CU-EJ-09)."""
        return self._historial_producto(producto_id, fecha_inicio, fecha_fin)

    # ------------------------------------------------------------------
    # Métodos privados — un método = una responsabilidad (SRP)
    # ------------------------------------------------------------------

    def _base_ops_qs(self):
        qs = OrdenProduccion.objects.all()
        if self._sede_id:
            qs = qs.filter(sede_id=self._sede_id)
        return qs

    def _base_lotes_qs(self):
        qs = LoteProduccion.objects.all()
        if self._sede_id:
            qs = qs.filter(orden_produccion__sede_id=self._sede_id)
        return qs

    def _ops_por_estado(self) -> OpsEstado:
        counts = (
            self._base_ops_qs()
            .values("estado")
            .annotate(total=Count("id"))
        )
        mapping = {row["estado"]: row["total"] for row in counts}
        return OpsEstado(
            pendiente=mapping.get("pendiente", 0),
            en_proceso=mapping.get("en_proceso", 0),
            finalizada=mapping.get("finalizada", 0),
        )

    def _kg_lotes(self, fecha_inicio: date, fecha_fin: date) -> Decimal:
        result = (
            self._base_lotes_qs()
            .filter(
                hora_inicio__date__gte=fecha_inicio,
                hora_inicio__date__lte=fecha_fin,
            )
            .aggregate(total=Sum("peso_neto_producido"))["total"]
        )
        return result or Decimal("0")

    def _tiempo_promedio_lote(self) -> float:
        avg = (
            self._base_lotes_qs()
            .filter(hora_final__isnull=False)
            .annotate(
                duracion=ExpressionWrapper(
                    F("hora_final") - F("hora_inicio"),
                    output_field=DurationField(),
                )
            )
            .aggregate(promedio=Avg("duracion"))["promedio"]
        )
        if avg is None:
            return 0.0
        return round(avg.total_seconds() / 60, 2)

    def _tendencia_diaria(
        self, fecha_inicio: date, fecha_fin: date
    ) -> list[TendenciaDia]:
        """
        Genera la serie temporal completa (incluyendo días sin producción = 0)
        para evitar huecos en el gráfico de línea del front-end.
        """
        rows = (
            self._base_lotes_qs()
            .filter(
                hora_inicio__date__gte=fecha_inicio,
                hora_inicio__date__lte=fecha_fin,
            )
            .values(fecha=F("hora_inicio__date"))
            .annotate(kg=Sum("peso_neto_producido"))
            .order_by("fecha")
        )
        return self._rellenar_serie_diaria(rows, fecha_inicio, fecha_fin)

    def _produccion_por_producto(
        self, fecha_inicio: date, fecha_fin: date
    ) -> list[ProduccionProductoItem]:
        """Agrupa los lotes del rango por producto de salida de su OP."""
        rows = (
            self._base_lotes_qs()
            .filter(
                hora_inicio__date__gte=fecha_inicio,
                hora_inicio__date__lte=fecha_fin,
                orden_produccion__producto_salida__isnull=False,
            )
            .values(
                "orden_produccion__producto_salida_id",
                "orden_produccion__producto_salida__codigo",
                "orden_produccion__producto_salida__descripcion",
            )
            .annotate(kg_total=Sum("peso_neto_producido"), num_lotes=Count("id"))
            .order_by("-kg_total")
        )
        return [
            ProduccionProductoItem(
                producto_id=row["orden_produccion__producto_salida_id"],
                producto_codigo=row["orden_produccion__producto_salida__codigo"] or "",
                producto_nombre=row["orden_produccion__producto_salida__descripcion"] or "",
                kg_total=row["kg_total"] or Decimal("0"),
                num_lotes=row["num_lotes"],
            )
            for row in rows
        ]

    def _historial_producto(
        self, producto_id: int, fecha_inicio: date, fecha_fin: date
    ) -> list[TendenciaDia]:
        """Serie diaria de kg producidos, acotada a un único producto de salida."""
        rows = (
            self._base_lotes_qs()
            .filter(
                hora_inicio__date__gte=fecha_inicio,
                hora_inicio__date__lte=fecha_fin,
                orden_produccion__producto_salida_id=producto_id,
            )
            .values(fecha=F("hora_inicio__date"))
            .annotate(kg=Sum("peso_neto_producido"))
            .order_by("fecha")
        )
        return self._rellenar_serie_diaria(rows, fecha_inicio, fecha_fin)

    @staticmethod
    def _rellenar_serie_diaria(rows, fecha_inicio: date, fecha_fin: date) -> list[TendenciaDia]:
        """Indexa `rows` por fecha y rellena los días sin producción con kg=0."""
        datos = {row["fecha"]: row["kg"] or Decimal("0") for row in rows}

        serie: list[TendenciaDia] = []
        cursor = fecha_inicio
        while cursor <= fecha_fin:
            serie.append(
                TendenciaDia(
                    fecha=cursor.isoformat(),
                    kg=datos.get(cursor, Decimal("0")),
                )
            )
            cursor += timedelta(days=1)

        return serie
