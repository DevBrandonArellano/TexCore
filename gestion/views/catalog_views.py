from rest_framework import viewsets
import logging
from rest_framework.permissions import IsAuthenticated
from gestion.permissions import IsSystemAdmin, IsAdminSistemasOrSede
from gestion.models import Producto, Proveedor
from gestion.serializers import ProductoSerializer, ProveedorSerializer
from ._common import SedeAutoAssignMixin, AuditedDestroyMixin

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


class ChemicalViewSet(SedeAutoAssignMixin, viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    def get_queryset(self):
        queryset = Producto.objects.filter(tipo__in=['quimico', 'insumo'])
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        return queryset


class ProductoViewSet(SedeAutoAssignMixin, AuditedDestroyMixin, viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        # create/update/delete: admin_sistemas y admin_sede (consistente con setup_permissions)
        return [IsAuthenticated(), IsAdminSistemasOrSede()]

    def get_queryset(self):
        user = self.request.user
        queryset = Producto.objects.all()

        # Multi-tenancy: Solo restringir si el usuario no es admin global
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            from django.db.models import Q
            queryset = queryset.filter(Q(sede=user.sede) | Q(sede__isnull=True))

        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)

        # Security Filter: Salesmen strictly cannot see chemicals or inputs
        if user.groups.filter(name='vendedor').exists() and not user.is_superuser:
            queryset = queryset.filter(tipo__in=['hilo', 'tela', 'subproducto'])

        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            tipos = [t.strip() for t in tipo.split(',')]
            queryset = queryset.filter(tipo__in=tipos)

        return queryset


class ProveedorViewSet(SedeAutoAssignMixin, AuditedDestroyMixin, viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    serializer_class = ProveedorSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsSystemAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = Proveedor.objects.all()
        # Multi-tenancy: Superusers, admin_sistemas y ejecutivos pueden ver todas las sedes
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            from django.db.models import Q
            qs = qs.filter(Q(sede=user.sede) | Q(sede__isnull=True))
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        return qs
