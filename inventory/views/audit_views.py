import logging
from datetime import timedelta
from django.utils import timezone

from rest_framework import viewsets, permissions
from rest_framework.pagination import PageNumberPagination

from inventory.serializers import AuditLogSerializer
from gestion.models import AuditLog

logger = logging.getLogger('inventory.views')


class AuditLogPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.select_related('usuario', 'content_type').all().order_by('-fecha_hora')
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = AuditLogPagination

    def get_queryset(self):
        from django.db.models import Q
        user = self.request.user
        qs = self.queryset

        # Solo admins pueden ver auditoría
        if not (user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'admin_sede']).exists()):
            return qs.none()

        # Solo mostrar cambios del último mes (en BD se guardan todos)
        umbral = timezone.now() - timedelta(days=30)
        qs = qs.filter(fecha_hora__gte=umbral)

        # Scope por rol:
        # - admin_sede: siempre restringido a su sede asignada.
        # - admin_sistemas/superuser: puede filtrar por sede_id opcional.
        is_admin_sistemas = user.groups.filter(name='admin_sistemas').exists()
        is_admin_sede = user.groups.filter(name='admin_sede').exists()
        sede_id = self.request.query_params.get('sede_id')

        if is_admin_sede and not (user.is_superuser or is_admin_sistemas):
            user_sede_id = getattr(user, 'sede_id', None)
            if not user_sede_id:
                return qs.none()
            qs = qs.filter(
                Q(usuario__sede_id=user_sede_id)
                | Q(object_sede_id=user_sede_id)
            )
        elif sede_id:
            qs = qs.filter(
                Q(usuario__sede_id=sede_id)
                | Q(object_sede_id=sede_id)
            )

        return qs
