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


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all()
    serializer_class = GroupSerializer



class SedeViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        # Optimización: usando Subqueries en lugar de Count con JOINs (más eficiente para grandes volúmenes)
        return Sede.objects.annotate(
            num_areas=Coalesce(
                Subquery(Area.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            ),
            num_users=Coalesce(
                Subquery(CustomUser.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            ),
            num_bodegas=Coalesce(
                Subquery(Bodega.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            ),
            num_ordenes=Coalesce(
                Subquery(OrdenProduccion.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            ),
            num_pedidos=Coalesce(
                Subquery(PedidoVenta.objects.filter(sede=OuterRef('pk')).values('sede').annotate(c=Count('id')).values('c')),
                Value(0), output_field=IntegerField()
            )
        ).all()



    serializer_class = SedeSerializer

    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        return [IsSystemAdmin()]


class AreaViewSet(viewsets.ModelViewSet):
    serializer_class = AreaSerializer
    
    def get_queryset(self):
        queryset = Area.objects.all()
        sede_id = self.request.query_params.get('sede_id')
        if sede_id:
            queryset = queryset.filter(sede_id=sede_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'reporte_eficiencia']:
            return [IsAuthenticated()]
        return [IsSystemAdmin()]

    @action(detail=True, methods=['get'], url_path='reporte-eficiencia')
    def reporte_eficiencia(self, request, pk=None):
        from django.db.models import Sum, Count, Min, Max, FloatField
        from django.db.models.functions import Cast
        from datetime import date
        area = self.get_object()
        hoy = date.today()

        # 1. Métricas de Máquinas — una sola query con anotaciones (resuelve N+1)
        maquinas = area.maquina_set.annotate(
            produccion_hoy=Sum(
                'lotes_producidos__peso_neto_producido',
                filter=Q(lotes_producidos__hora_final__date=hoy),
            )
        ).values('id', 'nombre', 'capacidad_maxima', 'produccion_hoy')

        maquinas_data = []
        for m in maquinas:
            produccion = m['produccion_hoy'] or 0
            cap = m['capacidad_maxima'] or 0
            eficiencia = (Decimal(str(produccion)) / cap * 100) if cap > 0 else 0
            maquinas_data.append({
                "maquina_id": m['id'],
                "maquina_nombre": m['nombre'],
                "capacidad_maxima": cap,
                "produccion_total": produccion,
                "eficiencia": round(eficiencia, 2),
            })

        # 2. Métricas de Operarios — una sola query con anotaciones (resuelve N+1)
        operarios = CustomUser.objects.filter(
            area=area, groups__name='operario'
        ).annotate(
            total_lotes=Count(
                'loteproduccion',
                filter=Q(loteproduccion__hora_final__date=hoy),
                distinct=True,
            ),
            produccion_total_kg=Sum(
                'loteproduccion__peso_neto_producido',
                filter=Q(loteproduccion__hora_final__date=hoy),
            ),
            hora_inicio_min=Min(
                'loteproduccion__hora_inicio',
                filter=Q(loteproduccion__hora_final__date=hoy),
            ),
            hora_final_max=Max(
                'loteproduccion__hora_final',
                filter=Q(loteproduccion__hora_final__date=hoy),
            ),
        ).values('id', 'username', 'total_lotes', 'produccion_total_kg', 'hora_inicio_min', 'hora_final_max')

        operarios_data = []
        for op in operarios:
            total_kg = op['produccion_total_kg'] or 0
            count = op['total_lotes'] or 0
            horas = 0
            if op['hora_final_max'] and op['hora_inicio_min']:
                duration = op['hora_final_max'] - op['hora_inicio_min']
                horas = duration.total_seconds() / 3600
            operarios_data.append({
                "operario_id": op['id'],
                "username": op['username'],
                "total_lotes": count,
                "produccion_total_kg": total_kg,
                "promedio_kg_por_lote": round(total_kg / count, 2) if count > 0 else 0,
                "horas_trabajadas_aprox": round(horas, 2),
                "productividad_kg_hora": round(float(total_kg) / horas, 2) if horas > 0 else 0,
            })

        total_area = sum(m['produccion_total'] for m in maquinas_data)
        ef_promedio = sum(m['eficiencia'] for m in maquinas_data) / len(maquinas_data) if maquinas_data else 0

        return Response({
            "area_id": area.id,
            "area_nombre": area.nombre,
            "fecha_reporte": hoy,
            "maquinas": maquinas_data,
            "operarios": operarios_data,
            "produccion_total_area": total_area,
            "eficiencia_promedio_area": round(ef_promedio, 2),
        })


class CustomUserViewSet(viewsets.ModelViewSet):
    serializer_class = CustomUserSerializer
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve', 'desempeno', 'vendedores']:
            return [IsAuthenticated()]
        return [IsSystemAdmin()]

    def get_queryset(self):
        user = self.request.user
        queryset = CustomUser.objects.select_related('sede', 'area').prefetch_related('groups').all()
        
        # Security: Jefe de Área only sees their area members by default
        if user.groups.filter(name='jefe_area').exists() and not user.is_superuser:
            if hasattr(user, 'area') and user.area:
                queryset = queryset.filter(area=user.area)
            else:
                return CustomUser.objects.none()

        # Multi-tenancy: Superusers, admin_sistemas y ejecutivos pueden ver todas las sedes
        if not user.is_superuser and not user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists():
            queryset = queryset.filter(sede=user.sede)

        sede_id = self.request.query_params.get('sede_id', self.request.query_params.get('sede', None))
        if sede_id is not None:
            queryset = queryset.filter(sede_id=sede_id)
        
        area_id = self.request.query_params.get('area', None)
        if area_id is not None:
            queryset = queryset.filter(area_id=area_id)
            
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not serializer.validated_data.get('sede') and hasattr(user, 'sede') and user.sede:
            serializer.save(sede=user.sede)
        else:
            serializer.save()

    @action(detail=False, methods=['get'], url_path='vendedores')
    def vendedores(self, request):
        """
        Lista vendedores para filtros en dashboards (ejecutivo/admin).
        """
        user = request.user
        if not (user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists()):
            return Response({"detail": "No autorizado."}, status=status.HTTP_403_FORBIDDEN)

        qs = CustomUser.objects.filter(groups__name='vendedor').distinct()

        # Para roles gerenciales, permitir ver vendedores de todas las sedes.
        # Para otros roles, mantener el ámbito por sede.
        if not (user.is_superuser or user.groups.filter(name__in=["admin_sistemas", "ejecutivo"]).exists()):
            qs = qs.filter(sede=user.sede)

        data = list(
            qs.order_by('username').values('id', 'username', 'first_name', 'last_name')
        )
        return Response(data)

    @action(detail=True, methods=['get'], url_path='desempeno')
    def desempeno(self, request, pk=None):
        operario = self.get_object()
        from django.db.models import Sum, Count
        from datetime import date
        
        lotes = LoteProduccion.objects.filter(operario=operario).order_by('-hora_final')[:50]
        summary = LoteProduccion.objects.filter(operario=operario, hora_final__date=date.today()).aggregate(
            total_kg=Sum('peso_neto_producido'),
            count=Count('id')
        )
        
        return Response({
            "operario": operario.username,
            "produccion_hoy_kg": summary['total_kg'] or 0,
            "lotes_hoy": summary['count'] or 0,
            "ultimos_lotes": LoteProduccionSerializer(lotes, many=True).data
        })

