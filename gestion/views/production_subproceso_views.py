from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from gestion.models import EtapaProduccion, OrdenProduccion, TransferenciaInterarea
from gestion.permissions import (
    IsJefeAreaOrAdmin, IsTransferenciaInterareaReader, IsTransferenciaInterareaWriter, areas_gestionables,
    filtrar_por_sede, validar_misma_sede, validar_visible,
)
from gestion.serializers import EtapaProduccionSerializer, TransferenciaInterareaSerializer


class EtapaProduccionViewSet(viewsets.ModelViewSet):
    """Etapas del flujo de producción de un área. OWASP A01: el Jefe de Área ve
    y escribe solo su área; Jefe de Planta y admins, las áreas de su sede. La
    máquina y las bodegas de la etapa son de la sede de su área."""
    serializer_class = EtapaProduccionSerializer
    permission_classes = [IsAuthenticated, IsJefeAreaOrAdmin]
    filterset_fields = ['area', 'maquina']
    search_fields = ['nombre', 'area__nombre']
    ordering_fields = ['orden', 'area']
    ordering = ['area', 'orden']

    def get_queryset(self):
        return EtapaProduccion.objects.select_related(
            'area', 'maquina', 'bodega_entrada', 'bodega_salida'
        ).filter(area__in=areas_gestionables(self.request.user))

    def _validar_alcance(self, serializer):
        campos = ('area', 'maquina', 'bodega_entrada', 'bodega_salida')
        actual = {c: getattr(serializer.instance, c) for c in campos} if serializer.instance else {}
        datos = {**actual, **{c: serializer.validated_data[c] for c in campos if c in serializer.validated_data}}
        area = datos.get('area')
        validar_visible(areas_gestionables(self.request.user), area, 'area')
        validar_misma_sede(
            area.sede_id, maquina=datos.get('maquina'),
            bodega_entrada=datos.get('bodega_entrada'), bodega_salida=datos.get('bodega_salida'),
        )

    def perform_create(self, serializer):
        self._validar_alcance(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validar_alcance(serializer)
        serializer.save()


class TransferenciaInterareaViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Transferencia de producto de un área a la siguiente. Es un eslabón de la
    cadena de trazabilidad (services/trazabilidad.py) y del KPI de área, así
    que no se edita ni se borra."""
    serializer_class = TransferenciaInterareaSerializer
    filterset_fields = ['orden_area_origen', 'orden_area_destino']
    search_fields = ['orden_area_origen__codigo', 'orden_area_destino__codigo']
    ordering_fields = ['fecha_transferencia', 'cantidad_transferida']
    ordering = ['-fecha_transferencia']

    def get_permissions(self):
        # Las transferencias entre áreas son responsabilidad del Jefe de Planta; el
        # Jefe de Área consulta las de su área y el Admin de Sede las monitorea.
        if self.action == 'create':
            return [IsAuthenticated(), IsTransferenciaInterareaWriter()]
        return [IsAuthenticated(), IsTransferenciaInterareaReader()]

    def get_queryset(self):
        user = self.request.user
        qs = TransferenciaInterarea.objects.select_related(
            'orden_area_origen', 'orden_area_destino',
            'bodega_origen', 'bodega_destino', 'usuario_responsable'
        )
        qs = filtrar_por_sede(qs, user, 'orden_area_origen__sede')
        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'jefe_planta', 'admin_sede']).exists():
            return qs
        if user.area_id:
            return qs.filter(orden_area_origen__area_id=user.area_id) | qs.filter(
                orden_area_destino__area_id=user.area_id)
        return qs.none()

    def perform_create(self, serializer):
        datos = serializer.validated_data
        origen, destino = datos['orden_area_origen'], datos['orden_area_destino']
        ordenes = filtrar_por_sede(OrdenProduccion.objects.all(), self.request.user)
        validar_visible(ordenes, origen, 'orden_area_origen')
        validar_visible(ordenes, destino, 'orden_area_destino')
        if origen.pk == destino.pk:
            raise ValidationError({'orden_area_destino': 'La orden de destino debe ser distinta de la de origen.'})
        validar_misma_sede(
            origen.sede_id, orden_area_destino=destino,
            bodega_origen=datos['bodega_origen'], bodega_destino=datos['bodega_destino'],
        )
        serializer.save(usuario_responsable=self.request.user)
