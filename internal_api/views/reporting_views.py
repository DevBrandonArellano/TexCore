"""
18 endpoints de datos para reportes.
SRP: cada view valida/adapta HTTP y delega la consulta a internal_api/services/reporting_data.py.
DIP: Django ORM en lugar de pyodbc directo.
ISO 27001 A.9: sin acceso directo a BD desde reporting_excel.
Scope requerido: reports:read

Nota (auditoría de performance 2026-08-31): estos endpoints ya no los llama
reporting_excel por HTTP — inventory/reporting_proxy.py invoca las funciones de
internal_api/services/reporting_data.py directamente (mismo proceso), y le pasa
los datos ya resueltos a reporting_excel solo para el formateo a Excel/CSV. Se
mantienen como endpoints HTTP por compatibilidad y para poder probarlos/usarlos
de forma independiente.
"""
import logging

from rest_framework.response import Response
from rest_framework.views import APIView

from internal_api.services import reporting_data
from internal_api.audit import AuditLogger
from internal_api.authentication import JWTServiceAuthentication
from internal_api.permissions import HasScope, IsInternalService

logger = logging.getLogger(__name__)

_AUTH = [JWTServiceAuthentication]
_PERMS = [IsInternalService, HasScope("reports:read")]


def _audit(request, action: str, resource: str = "reports") -> None:
    AuditLogger.log(
        service=request.user.service_name,
        action=action,
        resource=resource,
    )


def resolve_sede_scope(request):
    """
    Resuelve la sede a aplicar en un reporte interno como DEFENSA EN PROFUNDIDAD.

    El aislamiento primario por sede lo impone la capa que conoce al usuario
    humano (`inventory/reporting_proxy.py`, que fuerza `sede_id` = sede del
    usuario para roles no globales). Aquí, adicionalmente:
      - Si el ServicePrincipal trae un claim de sede firmado y NO es admin, se
        FUERZA esa sede; un `sede_id` de query distinto → 403.
      - Si trae `is_admin`, o no trae claim de sede (token servicio-a-servicio
        clásico), se respeta el `sede_id` de la query (comportamiento
        retrocompatible).

    Retorna (sede_id | None, error_response | None).
    """
    claim_sede = getattr(request.user, "sede_id", None)
    is_admin = getattr(request.user, "is_admin", False)
    query_sede = request.query_params.get("sede_id")

    if claim_sede is not None and not is_admin:
        if query_sede and str(query_sede) != str(claim_sede):
            return None, Response(
                {"detail": "El token de servicio no autoriza consultar otra sede."},
                status=403,
            )
        return claim_sede, None
    return query_sede, None


# ──────────────────────────────────────────────────────────
# INVENTARIO
# ──────────────────────────────────────────────────────────


class KardexView(APIView):
    """GET /api/internal/v1/reports/kardex/?bodega_id=&fecha_desde=&fecha_hasta="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_kardex")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        data = reporting_data.get_kardex(
            bodega_id,
            producto_id=request.query_params.get("producto_id"),
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
            lote_codigo=request.query_params.get("lote_codigo"),
        )
        return Response(data)


class ProductosView(APIView):
    """GET /api/internal/v1/reports/productos/?sede_id="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_productos")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        return Response(reporting_data.get_productos(sede_id))


class UsuariosView(APIView):
    """GET /api/internal/v1/reports/usuarios/?sede_id="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_usuarios")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        return Response(reporting_data.get_usuarios(sede_id))


class StockActualView(APIView):
    """GET /api/internal/v1/reports/stock-actual/?bodega_id="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_stock_actual")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        data = reporting_data.get_stock_actual(
            bodega_id, producto_id=request.query_params.get("producto_id")
        )
        return Response(data)


class ValorizacionView(APIView):
    """GET /api/internal/v1/reports/valorizacion/?bodega_id="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_valorizacion")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        return Response(reporting_data.get_valorizacion(bodega_id))


class AgingView(APIView):
    """GET /api/internal/v1/reports/aging/?bodega_id=&dias_minimos="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_aging")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        data = reporting_data.get_aging(
            bodega_id, dias_minimos=request.query_params.get("dias_minimos", 30)
        )
        return Response(data)


class RotacionView(APIView):
    """GET /api/internal/v1/reports/rotacion/?bodega_id=&fecha_desde=&fecha_hasta="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_rotacion")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        data = reporting_data.get_rotacion(
            bodega_id,
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
        )
        return Response(data)


class StockCeroView(APIView):
    """GET /api/internal/v1/reports/stock-cero/?bodega_id="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_stock_cero")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        return Response(reporting_data.get_stock_cero(bodega_id))


class ResumenMovimientosView(APIView):
    """GET /api/internal/v1/reports/resumen-movimientos/?bodega_id=&fecha_desde=&fecha_hasta="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_resumen_movimientos")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        data = reporting_data.get_resumen_movimientos(
            bodega_id,
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
        )
        return Response(data)


# ──────────────────────────────────────────────────────────
# VENDEDORES
# ──────────────────────────────────────────────────────────


class VentasVendedorView(APIView):
    """GET /api/internal/v1/vendedores/{vendedor_id}/ventas/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request, vendedor_id: int):
        _audit(request, "get_ventas_vendedor", f"vendedor/{vendedor_id}")
        data = reporting_data.get_ventas_vendedor(
            vendedor_id,
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
        )
        return Response(data)


class TopClientesVendedorView(APIView):
    """GET /api/internal/v1/vendedores/{vendedor_id}/top-clientes/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request, vendedor_id: int):
        _audit(request, "get_top_clientes_vendedor", f"vendedor/{vendedor_id}")
        data = reporting_data.get_top_clientes_vendedor(
            vendedor_id,
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
        )
        return Response(data)


class DeudoresVendedorView(APIView):
    """GET /api/internal/v1/vendedores/{vendedor_id}/deudores/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request, vendedor_id: int):
        _audit(request, "get_deudores_vendedor", f"vendedor/{vendedor_id}")
        return Response(reporting_data.get_deudores_vendedor(vendedor_id))


# ──────────────────────────────────────────────────────────
# GERENCIAL
# ──────────────────────────────────────────────────────────


class VentasGerencialView(APIView):
    """GET /api/internal/v1/gerencial/ventas/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_ventas_gerencial")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        data = reporting_data.get_ventas_gerencial(
            sede_id=sede_id,
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
        )
        return Response(data)


class TopClientesGerencialView(APIView):
    """GET /api/internal/v1/gerencial/top-clientes/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_top_clientes_gerencial")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        data = reporting_data.get_top_clientes_gerencial(
            sede_id=sede_id,
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
        )
        return Response(data)


class DeudoresGerencialView(APIView):
    """GET /api/internal/v1/gerencial/deudores/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_deudores_gerencial")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        return Response(reporting_data.get_deudores_gerencial(sede_id=sede_id))


# ──────────────────────────────────────────────────────────
# PRODUCCIÓN
# ──────────────────────────────────────────────────────────


class OrdenesProduccionView(APIView):
    """GET /api/internal/v1/produccion/ordenes/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_ordenes_produccion")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        data = reporting_data.get_ordenes_produccion(
            sede_id=sede_id,
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
        )
        return Response(data)


class LotesProduccionView(APIView):
    """GET /api/internal/v1/produccion/lotes/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_lotes_produccion")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        data = reporting_data.get_lotes_produccion(
            sede_id=sede_id,
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
        )
        return Response(data)


class TendenciaProduccionView(APIView):
    """GET /api/internal/v1/produccion/tendencia/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_tendencia_produccion")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        data = reporting_data.get_tendencia_produccion(
            sede_id=sede_id,
            fecha_desde=request.query_params.get("fecha_desde"),
            fecha_hasta=request.query_params.get("fecha_hasta"),
        )
        return Response(data)


class PlantaPulsoDiarioView(APIView):
    """GET /api/internal/v1/planta/pulso-diario/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_pulso_diario")
        from django.db.models import Sum
        from django.utils import timezone

        from gestion.models import TransferenciaInterarea

        hoy = timezone.now().date()
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error

        from gestion.models import LoteProduccion, OrdenProduccion

        # 1. kg_planificados_hoy
        qs_ordenes = OrdenProduccion.objects.filter(fecha_fin_planificada=hoy)
        if sede_id:
            qs_ordenes = qs_ordenes.filter(area__sede_id=sede_id)
        kg_planificados_hoy = qs_ordenes.aggregate(total=Sum("peso_neto_requerido"))["total"] or 0.0

        # 2. kg_producidos_hoy
        # 3. kg_merma_hoy
        qs_lotes = LoteProduccion.objects.filter(hora_final__date=hoy)
        if sede_id:
            qs_lotes = qs_lotes.filter(orden_produccion__area__sede_id=sede_id)

        aggs = qs_lotes.aggregate(
            prod=Sum("peso_neto_producido"),
            merma=Sum("peso_merma")
        )
        kg_producidos_hoy = aggs["prod"] or 0.0
        kg_merma_hoy = aggs["merma"] or 0.0

        # 4. wip_estancado (kilos transferidos pero no recibidos entre áreas)
        # Se asume que no están "recibidos" si la orden_area_destino sigue "pendiente"
        qs_transferencias = TransferenciaInterarea.objects.filter(orden_area_destino__estado="pendiente")
        if sede_id:
            qs_transferencias = qs_transferencias.filter(bodega_destino__sede_id=sede_id)

        wip_estancado = qs_transferencias.aggregate(total=Sum("cantidad_transferida"))["total"] or 0.0

        return Response({
            "kg_planificados_hoy": round(float(kg_planificados_hoy), 2),
            "kg_producidos_hoy": round(float(kg_producidos_hoy), 2),
            "kg_merma_hoy": round(float(kg_merma_hoy), 2),
            "wip_estancado": round(float(wip_estancado), 2),
        })
