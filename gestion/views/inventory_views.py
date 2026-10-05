import logging

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from gestion.models import Bodega
from gestion.permissions import IsAdminSistemasOrSede
from gestion.serializers import (
    BodegaSerializer,
)
from inventory.permissions import bodegas_visibles

from ._common import AuditedDestroyMixin, SedeAutoAssignMixin

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


class BodegaViewSet(SedeAutoAssignMixin, AuditedDestroyMixin, viewsets.ModelViewSet):
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
        visibles = bodegas_visibles(user)
        qs = base if visibles is None else base.filter(id__in=visibles.values('id'))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        return qs
