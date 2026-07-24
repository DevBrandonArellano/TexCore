from rest_framework import viewsets
import logging
from rest_framework.permissions import IsAuthenticated
from gestion.permissions import IsSystemAdmin, IsAdminSistemasOrSede
from gestion.models import Producto, Proveedor
from gestion.serializers import ProductoSerializer, ProveedorSerializer

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


class ChemicalViewSet(viewsets.ModelViewSet):
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

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()


class ProductoViewSet(viewsets.ModelViewSet):
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


class ProveedorViewSet(viewsets.ModelViewSet):
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
