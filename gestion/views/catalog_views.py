from rest_framework import viewsets
import logging
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from gestion.permissions import IsSystemAdmin, IsCatalogManager
from gestion.models import Producto, Proveedor
from gestion.serializers import ProductoSerializer, ProveedorSerializer
from ._common import SedeAutoAssignMixin, AuditedDestroyMixin

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


def _is_global_catalog_reader(user):
    return user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists()


def _scope_catalog_queryset_by_sede(queryset, user, action):
    if _is_global_catalog_reader(user):
        return queryset
    if action in ["list", "retrieve"]:
        return queryset.filter(Q(sede=user.sede) | Q(sede__isnull=True))
    return queryset.filter(sede=user.sede)


class ChemicalViewSet(SedeAutoAssignMixin, viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    pagination_class = None

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsCatalogManager()]

    def get_queryset(self):
        user = self.request.user
        queryset = Producto.objects.filter(tipo__in=['quimico', 'insumo'])
        queryset = _scope_catalog_queryset_by_sede(queryset, user, self.action)

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
        return [IsAuthenticated(), IsCatalogManager()]

    def get_queryset(self):
        user = self.request.user
        queryset = Producto.objects.all()

        queryset = _scope_catalog_queryset_by_sede(queryset, user, self.action)

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
            qs = qs.filter(Q(sede=user.sede) | Q(sede__isnull=True))
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        return qs
