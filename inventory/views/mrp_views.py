"""
API del MRP por sede (TEX-27, ADR-012).

El bodeguero y el administrador de sede calculan y consultan solo su sede; el
ejecutivo y el administrador de sistemas, cualquier sede o todas. La ejecución es
síncrona (el cálculo de una sede toma segundos) y responde con el resultado de cada
sede, sus conteos y sus advertencias.
"""
import logging

from django.shortcuts import get_object_or_404
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from gestion.models import Sede
from gestion.permissions import IsMRPRole, filtrar_por_sede, ve_todas_las_sedes
from gestion.views._common import parse_int_param
from inventory.models import MRPEjecucion, OrdenCompraSugerida, RequerimientoMaterial
from inventory.pagination import PaginacionAcotada
from inventory.serializers import (
    MRPEjecucionSerializer,
    OrdenCompraSugeridaSerializer,
    RequerimientoMaterialSerializer,
)
from inventory.services.mrp import MRPEngine, necesidades_produccion

logger = logging.getLogger('inventory.views')


def _acotar_a_sede(queryset, request, campo='sede'):
    """Sede del usuario; quien ve todas puede elegir una con ?sede=."""
    queryset = filtrar_por_sede(queryset, request.user, campo=campo)
    if ve_todas_las_sedes(request.user):
        sede_id = parse_int_param(request.query_params.get('sede'), 'sede')
        if sede_id:
            queryset = queryset.filter(**{f'{campo}_id': sede_id})
    return queryset


class RequerimientoMaterialViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """MRP: material comprado que piden las órdenes abiertas, por orden de origen."""
    serializer_class = RequerimientoMaterialSerializer
    permission_classes = [IsMRPRole]
    pagination_class = PaginacionAcotada

    def get_queryset(self):
        queryset = RequerimientoMaterial.objects.select_related(
            'producto_requerido', 'sede', 'orden_produccion',
        ).order_by('sede__nombre', 'fecha_requerida', 'orden_produccion__codigo', 'id')
        return _acotar_a_sede(queryset, self.request)


class OrdenCompraSugeridaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """MRP: sugerencias de compra informativas. Las genera el motor (`ejecutar-mrp`);
    no se editan a mano."""
    serializer_class = OrdenCompraSugeridaSerializer
    permission_classes = [IsMRPRole]
    pagination_class = PaginacionAcotada

    def get_queryset(self):
        queryset = OrdenCompraSugerida.objects.select_related('producto', 'sede').order_by(
            'sede__nombre', '-cantidad_sugerida', 'id')
        return _acotar_a_sede(queryset, self.request)

    @action(detail=False, methods=['post'], url_path='ejecutar-mrp')
    def ejecutar_mrp(self, request):
        """POST {sede_id} | {todas: true}. Sin cuerpo, la sede del usuario."""
        sedes = self._sedes_a_calcular(request)
        ejecuciones = [MRPEngine.ejecutar(sede, request.user) for sede in sedes]
        hubo_fallo = any(e.estado == MRPEjecucion.ESTADO_FALLIDA for e in ejecuciones)
        return Response(
            {'ejecuciones': MRPEjecucionSerializer(ejecuciones, many=True).data},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR if hubo_fallo else status.HTTP_200_OK,
        )

    @staticmethod
    def _sedes_a_calcular(request):
        usuario = request.user
        global_ = ve_todas_las_sedes(usuario)
        if request.data.get('todas'):
            if not global_:
                raise PermissionDenied('Solo puede calcular el MRP de su sede.')
            return list(Sede.objects.filter(status='activo').order_by('nombre'))

        sede_id = parse_int_param(request.data.get('sede_id'), 'sede_id') or usuario.sede_id
        if sede_id is None:
            raise ValidationError({'sede_id': 'Indique la sede a calcular.'})
        if not global_ and sede_id != usuario.sede_id:
            raise PermissionDenied('Solo puede calcular el MRP de su sede.')
        return [get_object_or_404(Sede, pk=sede_id, status='activo')]

    @action(detail=False, methods=['get'], url_path='ultima-ejecucion')
    def ultima_ejecucion(self, request):
        """Última ejecución de cada sede visible (una sola si se filtra por ?sede=)."""
        ejecuciones = _acotar_a_sede(MRPEjecucion.objects.select_related('sede', 'iniciada_por'), request)
        ultimas = {}
        for ejecucion in ejecuciones.order_by('sede_id', '-inicio', '-id'):
            ultimas.setdefault(ejecucion.sede_id, ejecucion)
        orden = sorted(ultimas.values(), key=lambda e: e.sede.nombre)
        return Response(MRPEjecucionSerializer(orden, many=True).data)

    @action(detail=False, methods=['get'], url_path='necesidades-produccion')
    def necesidades_produccion(self, request):
        """Productos fabricados que hay que producir (lo que alimenta el Plan MTS)."""
        usuario = request.user
        if ve_todas_las_sedes(usuario):
            sede_id = parse_int_param(request.query_params.get('sede'), 'sede')
            sedes = [sede_id] if sede_id else list(
                Sede.objects.filter(status='activo').order_by('nombre').values_list('id', flat=True))
        elif usuario.sede_id:
            sedes = [usuario.sede_id]
        else:
            return Response([])
        resultado = []
        for sede_id in sedes:
            resultado.extend(necesidades_produccion(sede_id))
        return Response(resultado)
