from datetime import date

from inventory.services.executive_kpi_service import ExecutiveKPIService
from gestion.services.produccion_kpi_service import ProduccionKPIService
from gestion.services.oee_service import OeeService
from gestion.utils import PrintingService
from rest_framework import status
import logging
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from gestion.models import (
    Area, LoteProduccion, Maquina, OrdenProduccion, TransferenciaInterarea
)
from gestion.permissions import IsJefePlantaOrAdmin
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum, F, Avg, DurationField, ExpressionWrapper, Q

# Vistas refactorizadas usando Django ORM y ModelViewSet

logger = logging.getLogger('gestion.views')


class KPIAreaView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        is_admin = user.is_superuser or user.groups.filter(
            name__in=['admin_sistemas', 'ejecutivo', 'jefe_planta']).exists()

        area_id = request.query_params.get('area')

        if not is_admin:
            # Non-admins (Jefe de Área) strictly see their own area
            if hasattr(user, 'area') and user.area:
                area = user.area
            else:
                return Response({"error": "No tienes un área asignada para ver KPIs."},
                                status=status.HTTP_403_FORBIDDEN)
        else:
            # Admins can specify an area or use their own if available
            if area_id:
                area = get_object_or_404(Area, id=area_id)
            elif hasattr(user, 'area') and user.area:
                area = user.area
            else:
                return Response({"error": "Área no especificada o el usuario no tiene un área asignada."},
                                status=status.HTTP_400_BAD_REQUEST)

        # KPIs
        # 1. Output (Producción Total)
        # Filter Lotes by Maquinas in this Area
        maquinas_area = Maquina.objects.filter(area=area)
        lotes_area = LoteProduccion.objects.filter(maquina__in=maquinas_area)

        # 1-2. Producción, merma y calidad — un solo aggregate por eficiencia.
        # Rendimiento (Yield) = salida buena / entrada = neto / (neto + merma).
        # First Pass Yield (FPY) = neto de primera calidad / neto total
        # (componente "Calidad" de OEE). La segunda/saldo implican retrabajo o
        # degradación de valor, por eso se separan del FPY.
        agregados = lotes_area.aggregate(
            total_neto=Sum('peso_neto_producido'),
            total_merma=Sum('peso_merma'),
            neto_primera=Sum('peso_neto_producido', filter=Q(clasificacion_calidad='primera')),
            neto_segunda=Sum('peso_neto_producido', filter=Q(clasificacion_calidad='segunda')),
            neto_saldo=Sum('peso_neto_producido', filter=Q(clasificacion_calidad='saldo')),
        )

        total_output = agregados['total_neto'] or 0
        total_merma = agregados['total_merma'] or 0
        neto_primera = agregados['neto_primera'] or 0
        neto_segunda = agregados['neto_segunda'] or 0
        neto_saldo = agregados['neto_saldo'] or 0

        entrada = float(total_output) + float(total_merma)
        rendimiento_yield = (float(total_output) / entrada) if entrada > 0 else 0.0
        first_pass_yield = (float(neto_primera) / float(total_output)) if total_output else 0.0

        # 3. Avg Time per Operator
        # time = hora_final - hora_inicio
        avg_duration = lotes_area.annotate(
            duration=ExpressionWrapper(F('hora_final') - F('hora_inicio'), output_field=DurationField())
        ).aggregate(Avg('duration'))['duration__avg']

        # Format duration to hours/minutes
        avg_minutes = 0
        if avg_duration:
            avg_minutes = avg_duration.total_seconds() / 60

        # OEE (R4): Disponibilidad x Rendimiento x Calidad (OEE for Operators).
        # Sin acotar por fecha — igual que el resto de este endpoint (histórico
        # completo del área, no una ventana de tiempo).
        oee = OeeService.calcular_oee_area(area)

        return Response({
            "area": area.nombre,
            "total_produccion_kg": total_output,
            "total_merma_kg": total_merma,
            "rendimiento_yield": round(rendimiento_yield, 4),
            "first_pass_yield": round(first_pass_yield, 4),
            "distribucion_calidad": {
                "primera": neto_primera,
                "segunda": neto_segunda,
                "saldo": neto_saldo,
            },
            "tiempo_promedio_lote_min": round(avg_minutes, 2),
            "oee": oee,
        })


class PlantaPulsoDiarioView(APIView):
    """
    GET /produccion/pulso-diario/

    "Torre de Control" del Jefe de Planta — métricas del día en curso:
    kg planificados, producidos, merma y WIP estancado entre áreas.

    Servida desde el backend humano (CookieJWT), NO desde internal_api:
    internal_api solo autentica microservicios (ServicePrincipal, sin sede),
    por lo que no puede imponer aislamiento por sede del usuario final.

    Aislamiento por sede (OWASP A01):
      - admin_sistemas / ejecutivo / superuser → pueden consultar cualquier
        sede vía ?sede_id, o todas si se omite (vista gerencial global).
      - jefe_planta / admin_sede → forzados a SU sede; un sede_id ajeno → 403.
    """
    permission_classes = [IsAuthenticated, IsJefePlantaOrAdmin]

    def _resolver_sede(self, request):
        """
        Resuelve la sede a consultar respetando el aislamiento.
        Retorna (sede_id | None, error_response | None).
        sede_id None + is_global == True significa "todas las sedes".
        """
        user = request.user
        is_global = user.is_superuser or user.groups.filter(
            name__in=['admin_sistemas', 'ejecutivo']
        ).exists()
        sede_param = request.query_params.get('sede_id')

        if is_global:
            # Puede filtrar por una sede específica o ver todas (None).
            if sede_param:
                try:
                    return int(sede_param), None
                except (TypeError, ValueError):
                    return None, Response(
                        {"detail": "sede_id debe ser un entero válido."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
            return None, None

        # No-global (jefe_planta / admin_sede): forzado a su propia sede.
        user_sede_id = getattr(user, 'sede_id', None)
        if not user_sede_id:
            return None, Response(
                {"detail": "No tienes una sede asignada para ver el pulso de planta."},
                status=status.HTTP_403_FORBIDDEN,
            )
        # Rechazar intento explícito de consultar una sede ajena.
        if sede_param and str(sede_param) != str(user_sede_id):
            logger.warning(
                "Intento de acceso a pulso de otra sede",
                extra={"sd": {
                    "entity": "PlantaPulsoDiario",
                    "user": user.username,
                    "sede_usuario": user_sede_id,
                    "sede_solicitada": sede_param,
                }},
            )
            return None, Response(
                {"detail": "No tienes permiso para ver el pulso de otra sede."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return user_sede_id, None

    def get(self, request):
        sede_id, error = self._resolver_sede(request)
        if error is not None:
            return error

        hoy = timezone.now().date()

        # 1. kg planificados hoy (órdenes cuya fecha fin planificada es hoy)
        qs_ordenes = OrdenProduccion.objects.filter(fecha_fin_planificada=hoy)
        if sede_id:
            qs_ordenes = qs_ordenes.filter(area__sede_id=sede_id)
        kg_planificados_hoy = qs_ordenes.aggregate(
            total=Sum("peso_neto_requerido"))["total"] or 0.0

        # 2-3. kg producidos y merma hoy (lotes cerrados hoy)
        qs_lotes = LoteProduccion.objects.filter(hora_final__date=hoy)
        if sede_id:
            qs_lotes = qs_lotes.filter(orden_produccion__area__sede_id=sede_id)
        aggs = qs_lotes.aggregate(
            prod=Sum("peso_neto_producido"),
            merma=Sum("peso_merma"),
        )
        kg_producidos_hoy = aggs["prod"] or 0.0
        kg_merma_hoy = aggs["merma"] or 0.0

        # 4. WIP estancado: kilos transferidos cuyo destino sigue pendiente de
        # recibir. Se mide por la sede de DESTINO (donde el material está
        # esperando ser procesado), no por la de origen.
        qs_transferencias = TransferenciaInterarea.objects.filter(
            orden_area_destino__estado="pendiente")
        if sede_id:
            qs_transferencias = qs_transferencias.filter(
                bodega_destino__sede_id=sede_id)
        wip_estancado = qs_transferencias.aggregate(
            total=Sum("cantidad_transferida"))["total"] or 0.0

        return Response({
            "kg_planificados_hoy": round(float(kg_planificados_hoy), 2),
            "kg_producidos_hoy": round(float(kg_producidos_hoy), 2),
            "kg_merma_hoy": round(float(kg_merma_hoy), 2),
            "wip_estancado": round(float(wip_estancado), 2),
        })


# =============================================================================
# VISTAS EJECUTIVAS — KPIs Consolidados
# =============================================================================
# RUP Artefacto: Diseño de Clases / Capa de Presentación
# Patrón: Fachada — cada vista delega el cálculo al Service Layer.
#         Las vistas solo se encargan de: autenticación, parseo de parámetros
#         y serialización de la respuesta (HTTP). Sin lógica de negocio aquí.
# =============================================================================


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


def _parsear_rango_fechas(request):
    """
    Parsea fecha_inicio/fecha_fin de query params (formato YYYY-MM-DD).
    Si se omiten, ambos defaultean a HOY — el caso base del drill-down
    ejecutivo es "qué se produjo hoy" antes de ampliar el rango.

    Retorna (fecha_inicio, fecha_fin, error_response | None).
    """
    hoy = timezone.localdate()
    raw_inicio = request.query_params.get("fecha_inicio")
    raw_fin = request.query_params.get("fecha_fin")
    try:
        fecha_inicio = date.fromisoformat(raw_inicio) if raw_inicio else hoy
        fecha_fin = date.fromisoformat(raw_fin) if raw_fin else hoy
    except ValueError:
        return None, None, Response(
            {"detail": "fecha_inicio/fecha_fin deben tener formato YYYY-MM-DD."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if fecha_inicio > fecha_fin:
        return None, None, Response(
            {"detail": "fecha_inicio no puede ser posterior a fecha_fin."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return fecha_inicio, fecha_fin, None


class ProduccionPorProductoView(APIView):
    """
    GET /produccion/por-producto/?fecha_inicio=&fecha_fin=&sede_id=<int>

    Producción agregada por producto en un rango de fechas (por defecto: hoy).
    Usado para la tabla de drill-down "Producción por Producto" del ejecutivo.

    RUP — Caso de Uso: CU-EJ-08 Ver Producción por Producto
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        fecha_inicio, fecha_fin, error = _parsear_rango_fechas(request)
        if error is not None:
            return error

        sede_id = KpiEjecutivoView._parsear_sede(request)
        service = ProduccionKPIService(sede_id=sede_id)
        items = service.obtener_produccion_por_producto(fecha_inicio, fecha_fin)

        return Response([
            {
                "producto_id": item.producto_id,
                "producto_codigo": item.producto_codigo,
                "producto_nombre": item.producto_nombre,
                "kg_total": item.kg_total,
                "num_lotes": item.num_lotes,
            }
            for item in items
        ])


class ProduccionHistorialProductoView(APIView):
    """
    GET /produccion/historial-producto/?producto_id=<int>&fecha_inicio=&fecha_fin=&sede_id=<int>

    Serie diaria de kg producidos de UN producto — gráfica de drill-down ejecutivo.

    RUP — Caso de Uso: CU-EJ-09 Ver Historial de Producción de un Producto
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            producto_id = int(request.query_params.get("producto_id"))
        except (TypeError, ValueError):
            return Response(
                {"detail": "producto_id es requerido y debe ser un entero válido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        fecha_inicio, fecha_fin, error = _parsear_rango_fechas(request)
        if error is not None:
            return error

        sede_id = KpiEjecutivoView._parsear_sede(request)
        service = ProduccionKPIService(sede_id=sede_id)
        historial = service.obtener_historial_producto(producto_id, fecha_inicio, fecha_fin)

        return Response([
            {"fecha": punto.fecha, "kg": punto.kg}
            for punto in historial
        ])


class ProduccionPorProductoImprimirView(APIView):
    """
    GET /produccion/por-producto/imprimir/?fecha_inicio=&fecha_fin=&sede_id=<int>

    PDF del listado de producción por producto — mismos filtros que
    ProduccionPorProductoView.

    RUP — Caso de Uso: CU-EJ-08 Ver Producción por Producto (impresión)
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        fecha_inicio, fecha_fin, error = _parsear_rango_fechas(request)
        if error is not None:
            return error

        sede_id = KpiEjecutivoView._parsear_sede(request)
        service = ProduccionKPIService(sede_id=sede_id)
        items = service.obtener_produccion_por_producto(fecha_inicio, fecha_fin)

        sede_usuario = getattr(request.user, 'sede', None)
        data = {
            "empresa_nombre": sede_usuario.nombre if sede_usuario else "TexCore",
            "sede_nombre": sede_usuario.nombre if sede_usuario else "Todas las sedes",
            "fecha_inicio": fecha_inicio.isoformat(),
            "fecha_fin": fecha_fin.isoformat(),
            "generado_en": timezone.now().isoformat(),
            "productos": [
                {
                    "producto_codigo": item.producto_codigo,
                    "producto_nombre": item.producto_nombre,
                    "kg_total": float(item.kg_total),
                    "num_lotes": item.num_lotes,
                }
                for item in items
            ],
        }

        pdf_content = PrintingService.generate_produccion_por_producto_pdf(data)
        if not pdf_content:
            return Response(
                {"detail": "El servicio de impresión no está disponible temporalmente."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        response = HttpResponse(pdf_content, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="produccion_por_producto.pdf"'
        return response
