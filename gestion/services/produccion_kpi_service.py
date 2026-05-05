from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Q, Sum, Count
from django.utils import timezone
from gestion.models import OrdenProduccion, LoteProduccion


class OpsEstado:
    def __init__(self, pendiente=0, en_proceso=0, finalizada=0):
        self.pendiente = pendiente
        self.en_proceso = en_proceso
        self.finalizada = finalizada


class KPIData:
    def __init__(self, ops_estado, kg_hoy=Decimal('0'), kg_semana=Decimal('0')):
        self.ops_estado = ops_estado
        self.kg_hoy = kg_hoy
        self.kg_semana = kg_semana


class TendenciaPoint:
    def __init__(self, fecha, kg):
        self.fecha = fecha
        self.kg = kg


class ProduccionKPIService:
    def __init__(self, sede_id=None):
        self.sede_id = sede_id

    def obtener_kpis(self, skip_tendencia=False):
        queryset = OrdenProduccion.objects.all()
        if self.sede_id:
            queryset = queryset.filter(sede_id=self.sede_id)

        ops_pendiente = queryset.filter(estado='pendiente').count()
        ops_en_proceso = queryset.filter(estado='en_proceso').count()
        ops_finalizada = queryset.filter(estado='finalizada').count()

        hoy = timezone.now().date()
        kg_hoy = Decimal('0')
        kg_semana = Decimal('0')

        lotes_hoy = LoteProduccion.objects.filter(
            hora_inicio__date=hoy
        )
        if self.sede_id:
            lotes_hoy = lotes_hoy.filter(
                orden_produccion__sede_id=self.sede_id
            )

        kg_hoy_result = lotes_hoy.aggregate(
            total=Sum('peso_neto_producido')
        )['total']
        kg_hoy = kg_hoy_result or Decimal('0')

        hace_semana = hoy - timedelta(days=7)
        lotes_semana = LoteProduccion.objects.filter(
            hora_inicio__date__gte=hace_semana,
            hora_inicio__date__lte=hoy
        )
        if self.sede_id:
            lotes_semana = lotes_semana.filter(
                orden_produccion__sede_id=self.sede_id
            )

        kg_semana_result = lotes_semana.aggregate(
            total=Sum('peso_neto_producido')
        )['total']
        kg_semana = kg_semana_result or Decimal('0')

        ops_estado = OpsEstado(
            pendiente=ops_pendiente,
            en_proceso=ops_en_proceso,
            finalizada=ops_finalizada
        )

        return KPIData(
            ops_estado=ops_estado,
            kg_hoy=kg_hoy,
            kg_semana=kg_semana
        )

    def obtener_tendencia(self):
        hace_30_dias = timezone.now().date() - timedelta(days=30)
        hoy = timezone.now().date()

        lotes = LoteProduccion.objects.filter(
            hora_inicio__date__gte=hace_30_dias,
            hora_inicio__date__lte=hoy
        )
        if self.sede_id:
            lotes = lotes.filter(
                orden_produccion__sede_id=self.sede_id
            )

        from django.db.models import Cast
        from django.db.models.functions import TruncDate

        tendencia_data = lotes.annotate(
            fecha=Cast(TruncDate('hora_inicio'), output_field=None)
        ).values('fecha').annotate(
            total_kg=Sum('peso_neto_producido')
        ).order_by('fecha')

        resultado = []
        for item in tendencia_data:
            punto = TendenciaPoint(
                fecha=item['fecha'],
                kg=item['total_kg'] or Decimal('0')
            )
            resultado.append(punto)

        return resultado
