from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
import logging
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions, IsAdminUser, AllowAny
from gestion.permissions import IsSystemAdmin, IsTintoreroOrAdmin, IsAdminSistemasOrSede, IsJefeAreaOrAdmin
from gestion.services.descarga_quimicos import DescargaQuimicosService
from gestion.services.pago_reversion import PagoReversionService
from django.contrib.auth.models import Group
from django.utils import timezone
from django.db.models import Count
from gestion.models import (
    Sede, Area, CustomUser, Producto, Batch, Bodega, ProcessStep,
    FormulaColor, DetalleFormula, Cliente, PagoCliente,
    OrdenProduccion, LoteProduccion, PedidoVenta, DetallePedido, Maquina,
    Proveedor, FaseReceta
)
from gestion.utils import PrintingService, PaymentReconciler
from gestion.serializers import (
    GroupSerializer, SedeSerializer, AreaSerializer, CustomUserSerializer, ProductoSerializer,
    BatchSerializer, BodegaSerializer, ProcessStepSerializer,
    FormulaColorSerializer, FormulaColorWriteSerializer,
    DetalleFormulaSerializer, DosificacionSerializer,
    ClienteSerializer, ClienteListSerializer, OrdenProduccionSerializer, OrdenProduccionEstadoSerializer,
    LoteProduccionSerializer, PedidoVentaSerializer, DetallePedidoSerializer,
    MaquinaSerializer, RegistrarLoteProduccionSerializer, PagoClienteSerializer,
    ProveedorSerializer, AnulacionPedidoSerializer, ModificacionPedidoSerializer,
)
from rest_framework.views import APIView
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.db.models import Sum, F, Avg, DurationField, ExpressionWrapper, Q
from inventory.models import StockBodega, MovimientoInventario
from inventory.utils import safe_get_or_create_stock

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


from django.db.models import OuterRef, Subquery, IntegerField, Value
from django.db.models.functions import Coalesce


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
        from .middleware import set_cascade_justification, clear_cascade_justification
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

