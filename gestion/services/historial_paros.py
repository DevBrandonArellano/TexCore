"""
Historial de mantenimiento y paros de máquina (pedido del Jefe de Área, 14-oct-2026).

Fuente única del resumen por máquina y del detalle paro por paro que consumen la pantalla
(`GET /api/paros-maquina/historial/`) y el PDF (`POST /api/paros-maquina/imprimir-historial/`),
para que lo impreso sea exactamente lo que se ve.

Reglas:
- El rango filtra por **solape**, no por la fecha de inicio: un paro que empezó antes del rango y
  sigue abierto son justamente días detenidos dentro del rango.
- Las horas de cada paro se **acotan al rango**: lo que se suma es el tiempo detenido dentro de las
  fechas consultadas, de modo que dos rangos contiguos suman el total y ninguno lo cuenta dos veces.
- Un paro sin `fin` está en curso y cuenta hasta ahora (o hasta el fin del rango, si ya pasó).
- El rango máximo es de un año y un día (`RANGO_MAXIMO_DIAS`): el resumen necesita todas las filas
  del rango, así que se acota la consulta en lugar de traer años de historia (RNF-03).
"""

from datetime import datetime, time, timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from gestion.models import ParoMaquina
from gestion.params import parse_int_param, parse_rango_fechas

DIAS_POR_OMISION = 30
RANGO_MAXIMO_DIAS = 366

CATEGORIAS = dict(ParoMaquina.CATEGORIA_CHOICES)

# Las dos categorías que son «mantenimiento» en sentido estricto: alimentan la columna
# «último mantenimiento» del resumen y el atajo de la pantalla.
CATEGORIAS_MANTENIMIENTO = ("MANTENIMIENTO_PLANIFICADO", "AVERIA")


def _booleano(params, nombre):
    """Query param booleano (`true`/`false`): None si viene vacío, 400 si no es ninguno."""
    crudo = params.get(nombre)
    if crudo in (None, ""):
        return None
    if isinstance(crudo, bool):
        return crudo
    valor = str(crudo).strip().lower()
    if valor in ("true", "1"):
        return True
    if valor in ("false", "0"):
        return False
    raise ValidationError({nombre: "Usar true o false."})


class FiltrosHistorial:
    """Filtros validados del historial, iguales para la pantalla (query params) y el PDF (body)."""

    def __init__(self, params):
        fecha_desde, fecha_hasta = parse_rango_fechas(params, "fecha_desde", "fecha_hasta")
        hoy = timezone.localdate()
        self.fecha_hasta = fecha_hasta or hoy
        self.fecha_desde = fecha_desde or (self.fecha_hasta - timedelta(days=DIAS_POR_OMISION))
        if (self.fecha_hasta - self.fecha_desde).days > RANGO_MAXIMO_DIAS:
            raise ValidationError(
                {"fecha_desde": f"El rango no puede superar {RANGO_MAXIMO_DIAS} días. Acota las fechas."}
            )

        self.maquina_id = parse_int_param(params.get("maquina"), "maquina")

        categoria = params.get("categoria") or None
        if categoria and categoria not in CATEGORIAS:
            raise ValidationError({"categoria": f"'{categoria}' no es una categoría de paro válida."})
        self.categoria = categoria

        self.planificado = _booleano(params, "planificado")

    @property
    def inicio_rango(self):
        return timezone.make_aware(datetime.combine(self.fecha_desde, time.min), timezone.get_current_timezone())

    @property
    def fin_rango(self):
        return timezone.make_aware(datetime.combine(self.fecha_hasta, time.max), timezone.get_current_timezone())

    def como_texto(self):
        """Los filtros aplicados, para el pie del PDF."""
        return {
            "fecha_desde": self.fecha_desde.isoformat(),
            "fecha_hasta": self.fecha_hasta.isoformat(),
            # Lo que se imprime; las ISO de arriba nombran el archivo y ordenan bien.
            "fecha_desde_texto": self.fecha_desde.strftime("%d/%m/%Y"),
            "fecha_hasta_texto": self.fecha_hasta.strftime("%d/%m/%Y"),
            "categoria": CATEGORIAS.get(self.categoria) if self.categoria else "Todas",
            "planificado": {True: "Solo planificados", False: "Solo no planificados"}.get(self.planificado, "Todos"),
        }


class HistorialParosService:
    @staticmethod
    def filtrar(queryset, filtros):
        """Paros que solapan con el rango, con los filtros opcionales aplicados."""
        # Solape con el rango: empezó antes de que acabe y (terminó después de que empiece o sigue abierto).
        queryset = queryset.filter(inicio__lte=filtros.fin_rango).filter(
            Q(fin__gte=filtros.inicio_rango) | Q(fin__isnull=True)
        )
        if filtros.maquina_id:
            queryset = queryset.filter(maquina_id=filtros.maquina_id)
        if filtros.categoria:
            queryset = queryset.filter(categoria=filtros.categoria)
        if filtros.planificado is not None:
            queryset = queryset.filter(planificado=filtros.planificado)
        return queryset

    @staticmethod
    def horas_en_rango(inicio, fin, filtros, ahora=None):
        """Horas del paro dentro del rango: el tramo común entre [inicio, fin] y el rango."""
        ahora = ahora or timezone.now()
        fin_efectivo = min(fin or ahora, filtros.fin_rango, ahora)
        inicio_efectivo = max(inicio, filtros.inicio_rango)
        segundos = (fin_efectivo - inicio_efectivo).total_seconds()
        return max(segundos, 0) / 3600

    @classmethod
    def resumen(cls, queryset, filtros):
        """Una fila por máquina con sus paros, horas detenidas y último mantenimiento.

        Se agrega en Python sobre una única consulta `values()`: el tramo de cada paro dentro del
        rango no se puede sumar en SQL de forma portable entre SQL Server y SQLite, y el rango
        está acotado a un año, así que el número de filas es pequeño y conocido.
        """
        ahora = timezone.now()
        filas = queryset.values(
            "maquina_id",
            "maquina__nombre",
            "maquina__area__nombre",
            "inicio",
            "fin",
            "categoria",
            "planificado",
        )

        por_maquina = {}
        for fila in filas:
            acumulado = por_maquina.setdefault(
                fila["maquina_id"],
                {
                    "maquina_id": fila["maquina_id"],
                    "maquina_nombre": fila["maquina__nombre"],
                    "area_nombre": fila["maquina__area__nombre"],
                    "paros": 0,
                    "horas_total": 0.0,
                    "horas_planificadas": 0.0,
                    "paros_en_curso": 0,
                    "ultimo_mantenimiento": None,
                },
            )
            horas = cls.horas_en_rango(fila["inicio"], fila["fin"], filtros, ahora)
            acumulado["paros"] += 1
            acumulado["horas_total"] += horas
            if fila["planificado"]:
                acumulado["horas_planificadas"] += horas
            if fila["fin"] is None:
                acumulado["paros_en_curso"] += 1
            if fila["categoria"] in CATEGORIAS_MANTENIMIENTO:
                anterior = acumulado["ultimo_mantenimiento"]
                if anterior is None or fila["inicio"] > anterior:
                    acumulado["ultimo_mantenimiento"] = fila["inicio"]

        resumen = sorted(por_maquina.values(), key=lambda fila: (-fila["horas_total"], fila["maquina_nombre"]))
        for fila in resumen:
            fila["horas_total"] = round(fila["horas_total"], 2)
            fila["horas_planificadas"] = round(fila["horas_planificadas"], 2)
            # Texto ISO, no `datetime`: el mismo resumen viaja a printing_service, y
            # `requests(json=...)` usa el json de la biblioteca estándar, que no serializa fechas.
            if fila["ultimo_mantenimiento"] is not None:
                fila["ultimo_mantenimiento"] = fila["ultimo_mantenimiento"].isoformat()
        return resumen

    @staticmethod
    def totales(resumen):
        return {
            "maquinas": len(resumen),
            "paros": sum(fila["paros"] for fila in resumen),
            "horas_total": round(sum(fila["horas_total"] for fila in resumen), 2),
            "horas_planificadas": round(sum(fila["horas_planificadas"] for fila in resumen), 2),
            "paros_en_curso": sum(fila["paros_en_curso"] for fila in resumen),
        }
