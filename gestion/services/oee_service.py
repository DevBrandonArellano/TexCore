"""
OeeService: calcula el Overall Equipment Effectiveness (OEE) por máquina o área.

Fundamento: *OEE for Operators* (Productivity Press) — OEE = Disponibilidad ×
Rendimiento × Calidad. Benchmark clase mundial ≈ 85% (90% × 95% × 99%).

Supuestos explícitos (documentados aquí porque no hay una única forma "correcta"
de derivarlos de los datos existentes de TexCore):

- **run_time**: Σ(hora_final − hora_inicio) de los `LoteProduccion` de la máquina
  dentro del rango [desde, hasta). Es el tiempo que la máquina estuvo produciendo.
- **downtime**: Σ duración de `ParoMaquina` con `planificado=False` en el rango.
  Los paros planificados (mantenimiento programado) no penalizan Disponibilidad
  — están fuera del "tiempo de producción planificado" de la fórmula OEE clásica.
- **Disponibilidad** = run_time / (run_time + downtime). 0 si el denominador es 0
  (sin producción ni paros registrados en el rango).
- **Rendimiento** = min(1, producción_real_kg / producción_teórica_kg), con
  producción_teórica = capacidad_maxima (kg/turno) × (run_time_horas / DURACION_TURNO_HORAS).
  `DURACION_TURNO_HORAS = 8` es un supuesto de turno estándar — `Maquina.capacidad_maxima`
  se documenta como "capacidad por turno" pero el modelo no registra la duración del turno.
- **Calidad** = First Pass Yield = neto de primera calidad / neto total (mismo cálculo
  que `KPIAreaView`).
- **OEE** = Disponibilidad × Rendimiento × Calidad.
"""
from decimal import Decimal

from django.db.models import Sum, F, DurationField, ExpressionWrapper, Q

from gestion.models import LoteProduccion, ParoMaquina, Maquina

DURACION_TURNO_HORAS = 8


class OeeService:

    @staticmethod
    def _run_time_horas(lotes_qs) -> float:
        agregado = lotes_qs.annotate(
            duracion=ExpressionWrapper(F('hora_final') - F('hora_inicio'), output_field=DurationField())
        ).aggregate(total=Sum('duracion'))
        total = agregado['total']
        return total.total_seconds() / 3600 if total else 0.0

    @staticmethod
    def _downtime_horas(paros_qs) -> float:
        minutos = 0.0
        for paro in paros_qs.filter(planificado=False, fin__isnull=False):
            minutos += paro.duracion_minutos or 0.0
        return minutos / 60

    @staticmethod
    def _calcular(lotes_qs, paros_qs, capacidad_maxima: Decimal) -> dict:
        run_time_h = OeeService._run_time_horas(lotes_qs)
        downtime_h = OeeService._downtime_horas(paros_qs)

        denom_disponibilidad = run_time_h + downtime_h
        disponibilidad = (run_time_h / denom_disponibilidad) if denom_disponibilidad > 0 else 0.0

        agregados_calidad = lotes_qs.aggregate(
            total_neto=Sum('peso_neto_producido'),
            neto_primera=Sum('peso_neto_producido', filter=Q(clasificacion_calidad='primera')),
        )
        total_neto = float(agregados_calidad['total_neto'] or 0)
        neto_primera = float(agregados_calidad['neto_primera'] or 0)
        calidad = (neto_primera / total_neto) if total_neto > 0 else 0.0

        capacidad = float(capacidad_maxima or 0)
        produccion_teorica = capacidad * (run_time_h / DURACION_TURNO_HORAS) if capacidad > 0 else 0.0
        rendimiento = min(1.0, total_neto / produccion_teorica) if produccion_teorica > 0 else 0.0

        oee = disponibilidad * rendimiento * calidad

        return {
            'disponibilidad': round(disponibilidad, 4),
            'rendimiento': round(rendimiento, 4),
            'calidad': round(calidad, 4),
            'oee': round(oee, 4),
            'downtime_min': round(downtime_h * 60, 2),
        }

    @staticmethod
    def _filtrar_rango(queryset, campo_desde, campo_hasta, desde, hasta):
        # desde/hasta=None => sin acotar (mismo comportamiento "histórico completo"
        # que el resto de KPIAreaView, que hoy no filtra por fecha).
        if desde is not None:
            queryset = queryset.filter(**{f'{campo_desde}__gte': desde})
        if hasta is not None:
            queryset = queryset.filter(**{f'{campo_hasta}__lte': hasta})
        return queryset

    @staticmethod
    def calcular_oee_maquina(maquina: Maquina, desde=None, hasta=None) -> dict:
        lotes_qs = OeeService._filtrar_rango(
            LoteProduccion.objects.filter(maquina=maquina), 'hora_inicio', 'hora_final', desde, hasta)
        paros_qs = OeeService._filtrar_rango(
            ParoMaquina.objects.filter(maquina=maquina), 'inicio', 'inicio', desde, hasta)
        return OeeService._calcular(lotes_qs, paros_qs, maquina.capacidad_maxima)

    @staticmethod
    def calcular_oee_area(area, desde=None, hasta=None) -> dict:
        maquinas = Maquina.objects.filter(area=area)
        lotes_qs = OeeService._filtrar_rango(
            LoteProduccion.objects.filter(maquina__in=maquinas), 'hora_inicio', 'hora_final', desde, hasta)
        paros_qs = OeeService._filtrar_rango(
            ParoMaquina.objects.filter(maquina__in=maquinas), 'inicio', 'inicio', desde, hasta)
        capacidad_total = maquinas.aggregate(total=Sum('capacidad_maxima'))['total'] or Decimal('0')
        return OeeService._calcular(lotes_qs, paros_qs, capacidad_total)
