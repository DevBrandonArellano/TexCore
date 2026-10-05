import logging

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from gestion.models import Producto, Proveedor
from gestion.permissions import (
    IsCatalogManager,
    IsSystemAdmin,
    filtrar_catalogo_por_sede,
    filtrar_por_sede,
)
from gestion.serializers import ProductoSerializer, ProveedorSerializer

from ._common import AuditedDestroyMixin, SedeAutoAssignMixin

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


def _scope_catalog_queryset_by_sede(queryset, user, action):
    if action in ["list", "retrieve"]:
        return filtrar_catalogo_por_sede(queryset, user)
    return filtrar_por_sede(queryset, user)


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
        qs = filtrar_catalogo_por_sede(qs, user)
        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        return qs
