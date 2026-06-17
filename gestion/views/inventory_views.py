from rest_framework import viewsets
import logging
from rest_framework.permissions import IsAuthenticated
from gestion.permissions import IsAdminSistemasOrSede
from gestion.models import (
    Bodega
)
from gestion.serializers import (
    BodegaSerializer,
)

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


class BodegaViewSet(viewsets.ModelViewSet):
    serializer_class = BodegaSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    def get_queryset(self):
        user = self.request.user
        base = Bodega.objects.prefetch_related('usuarios_asignados')
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']).exists():
            if sede_id:
                return base.filter(sede_id=sede_id)
            return base
        # Bodegueros y otros: solo bodegas asignadas
        qs = base.filter(id__in=user.bodegas_asignadas.values_list('id', flat=True))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)

        # Opcional: Asegurar que si es una bodega global asignada también se vea (ya cubierto por id__in)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()

    def perform_destroy(self, instance):
        from gestion.middleware import set_cascade_justification, clear_cascade_justification
        justificacion = self.request.query_params.get('_justificacion_auditoria') or \
            self.request.headers.get('X-Justificacion-Auditoria') or \
            self.request.data.get('_justificacion_auditoria')
        if not justificacion:
            justificacion = "Eliminación desde panel de administración"
        instance._justificacion_auditoria = justificacion
        set_cascade_justification(justificacion)
        try:
            instance.delete()
        finally:
            clear_cascade_justification()
