import logging
from decimal import Decimal

from django.db.models import Count, IntegerField, OuterRef, Prefetch, Subquery
from django.db.models.functions import Coalesce

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gestion.models import Maquina, LineaProduccion, ParoMaquina, LoteProduccion
from gestion.permissions import IsJefeAreaOrAdmin, IsJefeAreaOrOperarioOrAdmin
from gestion.serializers import MaquinaSerializer, ParoMaquinaSerializer, LineaProduccionSerializer

from ._common import parse_int_param

logger = logging.getLogger('gestion.views')


class MaquinaViewSet(viewsets.ModelViewSet):
    queryset = Maquina.objects.all()
    serializer_class = MaquinaSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        if self.request.user.groups.filter(name__in=['jefe_area', 'jefe_planta', 'admin_sistemas']).exists():
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsJefeAreaOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        queryset = Maquina.objects.select_related('area').all()

        # Security: Jefe de Área only sees their area machines
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(area=user.area)
            else:
                # If no area assigned, return none for safety
                return Maquina.objects.none()

        # Multi-tenancy: filter by sede if not global admin
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            queryset = queryset.filter(area__sede=user.sede)

        area_id = parse_int_param(self.request.query_params.get('area', None), 'area')
        if area_id:
            queryset = queryset.filter(area_id=area_id)

        return queryset

    @action(detail=True, methods=['get'], url_path='eficiencia')
    def eficiencia(self, request, pk=None):
        maquina = self.get_object()
        from django.db.models import Sum
        from datetime import date

        produccion = LoteProduccion.objects.filter(
            maquina=maquina,
            hora_final__date=date.today()
        ).aggregate(total=Sum('peso_neto_producido'))['total'] or 0

        eficiencia = (Decimal(str(produccion)) / maquina.capacidad_maxima * 100) if maquina.capacidad_maxima > 0 else 0

        return Response({
            "maquina": maquina.nombre,
            "capacidad_maxima": maquina.capacidad_maxima,
            "produccion_hoy": produccion,
            "eficiencia_porcentaje": round(eficiencia, 2)
        })

    @action(detail=True, methods=['get'], url_path='oee')
    def oee(self, request, pk=None):
        """GET /maquinas/{id}/oee/ — OEE = Disponibilidad x Rendimiento x Calidad
        de esta máquina (histórico completo, sin acotar por fecha; ver OeeService)."""
        from gestion.services.oee_service import OeeService

        maquina = self.get_object()
        return Response(OeeService.calcular_oee_maquina(maquina))


class ParoMaquinaViewSet(viewsets.ModelViewSet):
    """
    CRUD de paros de máquina (downtime) con reason code = Seis Grandes Pérdidas
    (OEE for Operators). El Operario registra sus propios paros; el Jefe de Área
    supervisa los de su área; aislamiento por área/sede idéntico a MaquinaViewSet.
    """
    queryset = ParoMaquina.objects.all()
    serializer_class = ParoMaquinaSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated, IsJefeAreaOrOperarioOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = ParoMaquina.objects.select_related('maquina', 'maquina__area', 'usuario').all()

        # Security: Jefe de Área only sees paros of machines in their area
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(maquina__area=user.area)
            else:
                return ParoMaquina.objects.none()

        # Multi-tenancy: filter by sede if not global admin
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            queryset = queryset.filter(maquina__area__sede=user.sede)

        maquina_id = parse_int_param(self.request.query_params.get('maquina', None), 'maquina')
        if maquina_id:
            queryset = queryset.filter(maquina_id=maquina_id)

        return queryset

    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)


class LineaProduccionViewSet(viewsets.ModelViewSet):
    """Células de Manufactura Flexibles: la línea agrupa flujo, NO asigna
    carga — colas y OPs se calculan a nivel de ÁREA (ver LineaProduccion)."""
    queryset = LineaProduccion.objects.select_related('area')
    serializer_class = LineaProduccionSerializer
    pagination_class = None

    @staticmethod
    def _base_queryset():
        # Anota por máquina cuántas líneas ACTIVAS la contienen → alimenta el
        # flag 'compartida' del serializer sin N+1 (una sola query de prefetch).
        #
        # OJO: se usa Subquery/OuterRef (no Count(...) directo sobre la misma
        # M2M) porque Prefetch('maquinas', ...) YA hace un join sobre
        # 'lineas_produccion' para repartir resultados entre las líneas padre.
        # Si la anotación reutiliza esa misma relación con Count(), Django
        # agrupa el GROUP BY por (línea, máquina) en vez de solo por máquina
        # (el join del propio Prefetch se cuela en el GROUP BY), y el conteo
        # queda acotado a la fila de cada línea individual (siempre da 1 en
        # vez del total real de líneas activas que comparten la máquina).
        # La Subquery corre independiente del join externo del Prefetch y
        # evita el conflicto.
        conteo_activas = LineaProduccion.objects.filter(
            maquinas=OuterRef('pk'), estado='activa'
        ).order_by().values('maquinas').annotate(c=Count('id')).values('c')
        maquinas_anotadas = Maquina.objects.annotate(
            num_lineas_activas=Coalesce(
                Subquery(conteo_activas, output_field=IntegerField()), 0))
        return LineaProduccion.objects.select_related('area').prefetch_related(
            Prefetch('maquinas', queryset=maquinas_anotadas))

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsJefeAreaOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        queryset = self._base_queryset()

        # Security: Jefe de Área only sees their area lines
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(area=user.area)
            else:
                return LineaProduccion.objects.none()

        # Multi-tenancy: filter by sede if not global admin
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            queryset = queryset.filter(area__sede=user.sede)

        area_id = parse_int_param(self.request.query_params.get('area', None), 'area')
        if area_id:
            queryset = queryset.filter(area_id=area_id)

        return queryset
