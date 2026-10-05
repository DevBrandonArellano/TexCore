import logging

from rest_framework import mixins, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from gestion.models import ComponenteMezclaOP, ConsumoLoteDetalle, LoteProduccion, OrdenProduccion
from gestion.permissions import (
    IsJefeAreaOrAdmin,
    filtrar_lotes_por_sede,
    filtrar_por_sede,
    validar_misma_sede,
    validar_visible,
)
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
        return filtrar_por_sede(qs, self.request.user, 'orden__sede')

    def _validar_alcance(self, serializer):
        """OWASP A01: la orden es de la sede del usuario; la bodega, de la sede de la
        orden; el producto, global o de esa sede."""
        datos = serializer.validated_data
        orden = datos.get('orden', getattr(serializer.instance, 'orden', None))
        validar_visible(filtrar_por_sede(OrdenProduccion.objects.all(), self.request.user), orden, 'orden')
        validar_misma_sede(orden.sede_id, bodega=datos.get('bodega'))
        producto = datos.get('producto')
        if producto is not None and producto.sede_id not in (None, orden.sede_id):
            raise ValidationError({'producto': 'No encontrado.'})

    def perform_create(self, serializer):
        self._validar_alcance(serializer)
        serializer.save()

    def perform_update(self, serializer):
        self._validar_alcance(serializer)
        serializer.save()

    def perform_destroy(self, instance):
        justificacion = str(self.request.data.get('justificacion') or '').strip()
        if not justificacion:
            raise ValidationError({'justificacion': 'Justificación requerida para eliminar un componente.'})
        instance.validar_orden_editable()
        instance._justificacion_auditoria = justificacion
        instance.delete()


class ConsumoLoteDetalleViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """
    ISO 27001 A.12.4: ConsumoLoteDetalle es inmutable — solo lectura.
    La eliminación ocurre únicamente vía endpoint rechazar/ del lote.
    OWASP A01: solo consumos de lotes de la sede del usuario.
    """
    serializer_class = ConsumoLoteDetalleSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        lotes = filtrar_lotes_por_sede(LoteProduccion.objects.all(), self.request.user)
        qs = ConsumoLoteDetalle.objects.select_related(
            'lote_produccion', 'lote_origen'
        ).filter(lote_produccion__in=lotes)
        lote_id = parse_int_param(self.request.query_params.get('lote_produccion'), 'lote_produccion')
        if lote_id:
            qs = qs.filter(lote_produccion_id=lote_id)
        return qs
