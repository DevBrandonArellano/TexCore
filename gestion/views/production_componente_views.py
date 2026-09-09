import logging

from rest_framework import viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from gestion.models import ComponenteMezclaOP, ConsumoLoteDetalle
from gestion.permissions import IsJefeAreaOrAdmin
from gestion.serializers import ComponenteMezclaOPSerializer, ConsumoLoteDetalleSerializer

from ._common import parse_int_param

logger = logging.getLogger('gestion.views')


class ComponenteMezclaOPViewSet(viewsets.ModelViewSet):
    """
    CRUD de componentes de mezcla.
    ISO 27001 A.9.4: solo jefe_area o admin pueden modificar.
    """
    serializer_class = ComponenteMezclaOPSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsJefeAreaOrAdmin()]

    def get_queryset(self):
        qs = ComponenteMezclaOP.objects.select_related(
            'producto', 'bodega', 'orden'
        )
        orden_id = parse_int_param(self.request.query_params.get('orden'), 'orden')
        if orden_id:
            qs = qs.filter(orden_id=orden_id)
        sede = getattr(self.request.user, 'sede', None)
        if sede:
            qs = qs.filter(orden__sede=sede)
        return qs

    def perform_destroy(self, instance):
        justificacion = self.request.data.get('justificacion', '')
        if not justificacion:
            raise ValidationError({'justificacion': 'Justificación requerida para eliminar un componente.'})
        instance._justificacion_auditoria = justificacion
        instance.delete()


class ConsumoLoteDetalleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ISO 27001 A.12.4: ConsumoLoteDetalle es inmutable — solo lectura.
    La eliminación ocurre únicamente vía endpoint rechazar/ del lote.
    """
    serializer_class = ConsumoLoteDetalleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ConsumoLoteDetalle.objects.select_related(
            'lote_produccion', 'lote_origen'
        )
        lote_id = parse_int_param(self.request.query_params.get('lote_produccion'), 'lote_produccion')
        if lote_id:
            qs = qs.filter(lote_produccion_id=lote_id)
        return qs
