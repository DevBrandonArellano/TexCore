import logging

from django.utils import timezone

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from gestion.models import (
    AreaProcessStep, OrdenProduccionSubproceso, EtapaProduccion, TransferenciaInterarea,
)
from gestion.permissions import IsJefeAreaOrAdmin, IsJefePlantaOrAdmin
from gestion.serializers import (
    AreaProcessStepSerializer, OrdenProduccionSubprocesoSerializer,
    EtapaProduccionSerializer, TransferenciaInterareaSerializer,
)

logger = logging.getLogger('gestion.views')


class AreaProcessStepViewSet(viewsets.ModelViewSet):
    queryset = AreaProcessStep.objects.select_related('area', 'proceso')
    serializer_class = AreaProcessStepSerializer
    permission_classes = [IsAuthenticated, IsJefeAreaOrAdmin]
    filterset_fields = ['area', 'tipo_flujo']
    ordering_fields = ['orden']
    ordering = ['area', 'orden']

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'jefe_planta']).exists():
            return AreaProcessStep.objects.select_related('area', 'proceso')
        if hasattr(user, 'area') and user.area:
            return AreaProcessStep.objects.filter(area=user.area).select_related('area', 'proceso')
        return AreaProcessStep.objects.none()


class OrdenProduccionSubprocesoViewSet(viewsets.ModelViewSet):
    queryset = OrdenProduccionSubproceso.objects.select_related(
        'orden_produccion', 'area_proceso', 'area_proceso__area',
        'area_proceso__proceso', 'usuario_responsable'
    )
    serializer_class = OrdenProduccionSubprocesoSerializer
    permission_classes = [IsAuthenticated, IsJefeAreaOrAdmin]
    filterset_fields = ['orden_produccion', 'estado', 'usuario_responsable', 'area_proceso__area']
    search_fields = ['orden_produccion__codigo', 'area_proceso__proceso__name']
    ordering_fields = ['fecha_inicio_real', 'fecha_fin_real', 'estado']
    ordering = ['area_proceso__orden']

    def get_queryset(self):
        user = self.request.user
        qs = OrdenProduccionSubproceso.objects.select_related(
            'orden_produccion', 'area_proceso', 'area_proceso__area',
            'area_proceso__proceso', 'usuario_responsable'
        )

        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'jefe_planta']).exists():
            return qs

        if hasattr(user, 'area') and user.area:
            return qs.filter(area_proceso__area=user.area)

        return qs.none()

    @action(detail=True, methods=['patch'])
    def iniciar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        if subproceso.estado != 'pendiente':
            return Response(
                {'detail': 'Solo se pueden iniciar subprocesos en estado pendiente.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subproceso.estado = 'en_progreso'
        subproceso.fecha_inicio_real = timezone.now()
        subproceso.usuario_responsable = request.user
        subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def completar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        if subproceso.estado not in ['en_progreso', 'pausado']:
            return Response(
                {'detail': 'El subproceso debe estar en progreso o pausado para completarse.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subproceso.estado = 'completado'
        subproceso.fecha_fin_real = timezone.now()
        subproceso.observaciones = request.data.get('observaciones', subproceso.observaciones)
        subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def rechazar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        if subproceso.estado == 'completado':
            return Response(
                {'detail': 'No se puede rechazar un subproceso completado.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subproceso.estado = 'rechazado'
        subproceso.motivo_rechazo = request.data.get('motivo_rechazo', '')
        subproceso.observaciones = request.data.get('observaciones', subproceso.observaciones)
        subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def pausar_subproceso(self, request, pk=None):
        subproceso = self.get_object()
        if subproceso.estado != 'en_progreso':
            return Response(
                {'detail': 'Solo se pueden pausar subprocesos en progreso.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        subproceso.estado = 'pausado'
        subproceso.observaciones = request.data.get('observaciones', subproceso.observaciones)
        subproceso.save()

        return Response(
            OrdenProduccionSubprocesoSerializer(subproceso).data,
            status=status.HTTP_200_OK
        )


class EtapaProduccionViewSet(viewsets.ModelViewSet):
    queryset = EtapaProduccion.objects.select_related(
        'area', 'maquina', 'bodega_entrada', 'bodega_salida'
    )
    serializer_class = EtapaProduccionSerializer
    permission_classes = [IsAuthenticated, IsJefeAreaOrAdmin]
    filterset_fields = ['area', 'maquina']
    search_fields = ['nombre', 'area__nombre']
    ordering_fields = ['orden', 'area']
    ordering = ['area', 'orden']

    def get_queryset(self):
        user = self.request.user
        qs = EtapaProduccion.objects.select_related(
            'area', 'maquina', 'bodega_entrada', 'bodega_salida'
        )

        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'jefe_planta']).exists():
            return qs

        if hasattr(user, 'area') and user.area:
            return qs.filter(area=user.area)

        return qs.none()


class TransferenciaInterareaViewSet(viewsets.ModelViewSet):
    queryset = TransferenciaInterarea.objects.select_related(
        'orden_area_origen', 'orden_area_destino',
        'bodega_origen', 'bodega_destino', 'usuario_responsable'
    )
    serializer_class = TransferenciaInterareaSerializer
    filterset_fields = ['orden_area_origen', 'orden_area_destino']
    search_fields = ['orden_area_origen__codigo', 'orden_area_destino__codigo']
    ordering_fields = ['fecha_transferencia', 'cantidad_transferida']
    ordering = ['-fecha_transferencia']

    def get_permissions(self):
        # Crear/modificar/eliminar: solo Jefe de Planta y admins.
        # El Jefe de Área solo crea órdenes de producción; las transferencias
        # entre áreas son responsabilidad del Jefe de Planta.
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsJefePlantaOrAdmin()]
        # Listar/recuperar: Jefe de Área puede ver las de su área
        return [IsAuthenticated(), IsJefeAreaOrAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = TransferenciaInterarea.objects.select_related(
            'orden_area_origen', 'orden_area_destino',
            'bodega_origen', 'bodega_destino', 'usuario_responsable'
        )

        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'jefe_planta', 'admin_sede']).exists():
            return qs

        if hasattr(user, 'area') and user.area:
            return qs.filter(
                orden_area_origen__area=user.area
            ) | qs.filter(
                orden_area_destino__area=user.area
            )

        return qs.none()

    def perform_create(self, serializer):
        serializer.save(usuario_responsable=self.request.user)
