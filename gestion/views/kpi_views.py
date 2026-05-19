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


class KPIAreaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        is_admin = user.is_superuser or user.groups.filter(name__in=['admin_sistemas', 'ejecutivo', 'jefe_planta']).exists()
        
        area_id = request.query_params.get('area')
        
        if not is_admin:
            # Non-admins (Jefe de Área) strictly see their own area
            if hasattr(user, 'area') and user.area:
                area = user.area
            else:
                return Response({"error": "No tienes un área asignada para ver KPIs."}, status=status.HTTP_403_FORBIDDEN)
        else:
            # Admins can specify an area or use their own if available
            if area_id:
                area = get_object_or_404(Area, id=area_id)
            elif hasattr(user, 'area') and user.area:
                area = user.area
            else:
                return Response({"error": "Área no especificada o el usuario no tiene un área asignada."}, status=status.HTTP_400_BAD_REQUEST)

        # KPIs
        # 1. Output (Producción Total)
        # Filter Lotes by Maquinas in this Area
        maquinas_area = Maquina.objects.filter(area=area)
        lotes_area = LoteProduccion.objects.filter(maquina__in=maquinas_area)
        
        total_output = lotes_area.aggregate(Sum('peso_neto_producido'))['peso_neto_producido__sum'] or 0

        # 2. Input (Consumo Estimado)
        # We estimate input = output (assuming 1:1 for now as per logic)
        # Or better, we sum the initial requirements of the orders? 
        # Let's say Yield = Output / (Output + Loss). 
        # Since we don't track loss explicitly yet, let's use Capacity Utilization.
        # "Rendimiento (Entrada vs Salida)" -> Typically Output / Input.
        # Input = Raw materials consumed. If we assume 1:1, it's 100%.
        # Let's assume Input = Peso Teórico (e.g. from Order) vs Real (Lote).
        # OR just return the total volumes.
        
        # 3. Avg Time per Operator
        # time = hora_final - hora_inicio
        avg_duration = lotes_area.annotate(
            duration=ExpressionWrapper(F('hora_final') - F('hora_inicio'), output_field=DurationField())
        ).aggregate(Avg('duration'))['duration__avg']
        
        # Format duration to hours/minutes
        avg_minutes = 0
        if avg_duration:
            avg_minutes = avg_duration.total_seconds() / 60

        return Response({
            "area": area.nombre,
            "total_produccion_kg": total_output,
            "rendimiento_yield": 1.0, # Placeholder until better input tracking
            "tiempo_promedio_lote_min": round(avg_minutes, 2)
        })


# =============================================================================
# VISTAS EJECUTIVAS — KPIs Consolidados
# =============================================================================
# RUP Artefacto: Diseño de Clases / Capa de Presentación
# Patrón: Fachada — cada vista delega el cálculo al Service Layer.
#         Las vistas solo se encargan de: autenticación, parseo de parámetros
#         y serialización de la respuesta (HTTP). Sin lógica de negocio aquí.
# =============================================================================

from gestion.services.produccion_kpi_service import ProduccionKPIService
from inventory.services.executive_kpi_service import ExecutiveKPIService



class KpiEjecutivoView(APIView):
    """
    GET /kpi-ejecutivo/?sede_id=<int>

    Retorna el dashboard consolidado de KPIs ejecutivos:
    producción, MRP, stock y cartera. Si sede_id es omitido,
    retorna datos de todas las sedes (vista gerencial global).

    RUP — Caso de Uso: CU-EJ-01 Ver Resumen Ejecutivo
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sede_id = self._parsear_sede(request)

        prod_service = ProduccionKPIService(sede_id=sede_id)
        exec_service = ExecutiveKPIService(sede_id=sede_id)

        kpis_prod = prod_service.obtener_kpis(skip_tendencia=True)

        kpis_exec = exec_service.obtener_kpis()

        return Response({
            "produccion": {
                "ops_pendiente": kpis_prod.ops_estado.pendiente,
                "ops_en_proceso": kpis_prod.ops_estado.en_proceso,
                "ops_finalizada": kpis_prod.ops_estado.finalizada,
                "kg_hoy": kpis_prod.kg_hoy,
                "kg_semana": kpis_prod.kg_semana,
                "kg_mes": kpis_prod.kg_mes,
                "tiempo_promedio_lote_min": kpis_prod.tiempo_promedio_lote_min,
            },
            "mrp": {
                "ocs_pendientes": kpis_exec.mrp.ocs_pendientes,
                "ocs_aprobadas": kpis_exec.mrp.ocs_aprobadas,
                "ocs_rechazadas": kpis_exec.mrp.ocs_rechazadas,
                "productos_en_deficit": kpis_exec.mrp.productos_en_deficit,
            },
            "stock": {
                "productos_bajo_minimo": kpis_exec.stock.productos_bajo_minimo,
            },
            "cartera": {
                "cuentas_por_cobrar": kpis_exec.cartera.cuentas_por_cobrar,
                "cartera_vencida": kpis_exec.cartera.cartera_vencida,
                "pedidos_pendientes": kpis_exec.cartera.pedidos_pendientes,
                "pedidos_despachados": kpis_exec.cartera.pedidos_despachados,
            },
        })

    @staticmethod
    def _parsear_sede(request) -> int | None:
        raw = request.query_params.get("sede_id")
        if raw:
            try:
                return int(raw)
            except (ValueError, TypeError):
                pass
        return None



class ProduccionResumenView(APIView):
    """
    GET /produccion/resumen/?sede_id=<int>

    Retorna KPIs de producción + distribución de OPs por estado.
    Usado para el Tab de Producción en el dashboard ejecutivo.

    RUP — Caso de Uso: CU-EJ-02 Ver Resumen de Producción
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sede_id = KpiEjecutivoView._parsear_sede(request)
        service = ProduccionKPIService(sede_id=sede_id)
        kpis = service.obtener_kpis(skip_tendencia=True)


        ops_grafico = [
            {"estado": "Pendiente", "value": kpis.ops_estado.pendiente, "fill": "#f59e0b"},
            {"estado": "En Proceso", "value": kpis.ops_estado.en_proceso, "fill": "#3b82f6"},
            {"estado": "Finalizada", "value": kpis.ops_estado.finalizada, "fill": "#22c55e"},
        ]

        return Response({
            "ops_por_estado": ops_grafico,
            "kg_hoy": kpis.kg_hoy,
            "kg_semana": kpis.kg_semana,
            "kg_mes": kpis.kg_mes,
            "tiempo_promedio_lote_min": kpis.tiempo_promedio_lote_min,
        })



class ProduccionTendenciaView(APIView):
    """
    GET /produccion/tendencia/?sede_id=<int>

    Serie temporal de kg producidos por día en los últimos 30 días.
    Optimizado para gráfico de línea en el front-end ejecutivo.

    RUP — Caso de Uso: CU-EJ-03 Ver Tendencia de Producción
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        sede_id = KpiEjecutivoView._parsear_sede(request)
        service = ProduccionKPIService(sede_id=sede_id)
        tendencia = service.obtener_tendencia()

        return Response([
            {"fecha": punto.fecha, "kg": punto.kg}
            for punto in tendencia
        ])
