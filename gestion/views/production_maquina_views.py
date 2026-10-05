import logging
from decimal import Decimal

from django.db.models import Count, IntegerField, OuterRef, Prefetch, Subquery
from django.db.models.functions import Coalesce
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gestion.models import LineaProduccion, LoteProduccion, Maquina, ParoMaquina, ProcesoTintoreria
from gestion.permissions import (
    IsJefeAreaOrAdmin,
    IsJefeAreaOrOperarioOrAdmin,
    IsLectorProcesosTintoreria,
    areas_gestionables,
    filtrar_por_sede,
    validar_misma_sede,
    validar_visible,
    ve_todas_las_sedes,
)
from gestion.serializers import (
    LineaProduccionSerializer,
    MaquinaSerializer,
    ParoMaquinaSerializer,
    ProcesoTintoreriaSerializer,
)
from gestion.services.procesos_maquina import ProcesosMaquinaService

from ._common import parse_int_param

logger = logging.getLogger('gestion.views')


def _acotar_por_area_y_sede(qs, user, campo_area):
    """OWASP A01: el Jefe de Área ve solo su área; el resto, su sede (helper único)."""
    if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
        if not user.area_id:
            return qs.none()
        qs = qs.filter(**{f'{campo_area}_id': user.area_id})
    return filtrar_por_sede(qs, user, f'{campo_area}__sede')


def maquinas_visibles(user):
    return _acotar_por_area_y_sede(Maquina.objects.all(), user, 'area')


class MaquinaViewSet(viewsets.ModelViewSet):
    queryset = Maquina.objects.all()
    serializer_class = MaquinaSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        if self.action == 'procesos':
            if self.request.method == 'PUT':
                return [IsAuthenticated(), IsJefeAreaOrAdmin()]
            return [IsAuthenticated(), IsLectorProcesosTintoreria()]
        if self.request.user.groups.filter(name__in=['jefe_area', 'jefe_planta', 'admin_sistemas']).exists():
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsJefeAreaOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        # MaquinaSerializer lee estas FK y el M2M operarios (dos veces) por fila.
        queryset = Maquina.objects.select_related(
            'area', 'bodega_entrada', 'bodega_salida', 'bodega_merma', 'producto_merma',
        ).prefetch_related('operarios').all()

        queryset = _acotar_por_area_y_sede(queryset, user, 'area')

        area_id = parse_int_param(self.request.query_params.get('area', None), 'area')
        if area_id:
            queryset = queryset.filter(area_id=area_id)

        return queryset

    def _validar_alcance(self, serializer):
        """OWASP A01: el área es gestionable por el usuario, y bodegas y
        operarios son de la sede de esa área."""
        user = self.request.user
        datos = serializer.validated_data
        instancia = serializer.instance
        area = datos['area'] if 'area' in datos else getattr(instancia, 'area', None)
        if area is None:
            if not ve_todas_las_sedes(user):
                raise ValidationError({'area': 'Este campo es requerido.'})
            return
        validar_visible(areas_gestionables(user), area, 'area')
        campos = ('bodega_entrada', 'bodega_salida', 'bodega_merma')
        referencias = {c: datos[c] if c in datos else getattr(instancia, c, None) for c in campos}
        operarios = datos['operarios'] if 'operarios' in datos else (
            list(instancia.operarios.all()) if instancia else [])
        validar_misma_sede(area.sede_id, operarios=operarios, **referencias)

    def perform_create(self, serializer):
        self._validar_alcance(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validar_alcance(serializer)
        serializer.save()

    @action(detail=True, methods=['get', 'put'], url_path='procesos')
    def procesos(self, request, pk=None):
        """GET /maquinas/{id}/procesos/ — procesos de tintorería que ejecuta la máquina.
        PUT con `{procesos: [ids]}` los reemplaza (Jefe de Área de esa área, Jefe de Planta
        o admin; la máquina de otra área no es visible → 404)."""
        maquina = self.get_object()
        if request.method == 'PUT':
            ids = request.data.get('procesos') if isinstance(request.data, dict) else None
            if not isinstance(ids, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in ids):
                raise ValidationError({'procesos': 'Envía la lista de ids de procesos.'})
            procesos = ProcesosMaquinaService.reemplazar(maquina, ids, request.user)
        else:
            procesos = ProcesoTintoreria.objects.filter(maquinas_asignadas__maquina=maquina).order_by('codigo')
        return Response(ProcesoTintoreriaSerializer(procesos, many=True).data)

    @action(detail=True, methods=['get'], url_path='eficiencia')
    def eficiencia(self, request, pk=None):
        maquina = self.get_object()
        from django.db.models import Sum
        from django.utils import timezone

        produccion = LoteProduccion.objects.filter(
            maquina=maquina,
            hora_final__date=timezone.localdate()
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


class ParoMaquinaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Paros de máquina (downtime) con reason code = Seis Grandes Pérdidas
    (OEE for Operators). El Operario registra sus propios paros; el Jefe de Área
    supervisa los de su área; aislamiento por área/sede idéntico a MaquinaViewSet.
    Un paro es histórico (alimenta el OEE): no se edita ni se borra.
    """
    queryset = ParoMaquina.objects.all()
    serializer_class = ParoMaquinaSerializer
    pagination_class = None
    permission_classes = [IsAuthenticated, IsJefeAreaOrOperarioOrAdmin]

    def get_queryset(self):
        user = self.request.user
        queryset = ParoMaquina.objects.select_related('maquina', 'maquina__area', 'usuario').all()
        queryset = _acotar_por_area_y_sede(queryset, user, 'maquina__area')

        maquina_id = parse_int_param(self.request.query_params.get('maquina', None), 'maquina')
        if maquina_id:
            queryset = queryset.filter(maquina_id=maquina_id)

        return queryset

    def perform_create(self, serializer):
        validar_visible(maquinas_visibles(self.request.user), serializer.validated_data['maquina'], 'maquina')
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
        queryset = _acotar_por_area_y_sede(self._base_queryset(), user, 'area')

        area_id = parse_int_param(self.request.query_params.get('area', None), 'area')
        if area_id:
            queryset = queryset.filter(area_id=area_id)

        return queryset

    def _validar_area(self, serializer):
        # El serializer ya exige que las máquinas sean del área de la línea.
        area = serializer.validated_data.get('area', getattr(serializer.instance, 'area', None))
        validar_visible(areas_gestionables(self.request.user), area, 'area')

    def perform_create(self, serializer):
        self._validar_area(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validar_area(serializer)
        serializer.save()
