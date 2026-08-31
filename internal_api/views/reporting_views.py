"""
18 endpoints de datos para reporting_excel.
SRP: cada view retorna exactamente los datos de un SP.
DIP: Django ORM en lugar de pyodbc directo.
ISO 27001 A.9: sin acceso directo a BD desde reporting_excel.
Scope requerido: reports:read
"""
import logging
from datetime import timedelta

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_date
from rest_framework.response import Response
from rest_framework.views import APIView

from gestion.models import (
    Cliente,
    CustomUser,
    LoteProduccion,
    OrdenProduccion,
    PedidoVenta,
    Producto,
)
from internal_api.audit import AuditLogger
from internal_api.authentication import JWTServiceAuthentication
from internal_api.permissions import HasScope, IsInternalService
from inventory.models import MovimientoInventario, StockBodega

logger = logging.getLogger(__name__)

_AUTH = [JWTServiceAuthentication]
_PERMS = [IsInternalService, HasScope("reports:read")]


def _fecha_hasta_exclusiva(fecha_hasta: str):
    """
    Convierte 'YYYY-MM-DD' en el límite exclusivo del día siguiente, para
    filtrar con '__lt' (sargable) en vez de '__date__lte'. '__date__lte'
    compila a CAST(columna AS DATE) &lt;= ... en SQL Server, lo que anula
    cualquier seek de índice sobre la columna de fecha (fuerza scan).
    """
    parsed = parse_date(fecha_hasta)
    return parsed + timedelta(days=1) if parsed else None


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
        clásico de reporting_excel), se respeta el `sede_id` de la query
        (comportamiento retrocompatible).

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

        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        producto_id = request.query_params.get("producto_id")
        lote_codigo = request.query_params.get("lote_codigo")

        qs = MovimientoInventario.objects.select_related(
            "producto", "bodega_origen", "bodega_destino", "lote", "usuario"
        ).filter(Q(bodega_origen_id=bodega_id) | Q(bodega_destino_id=bodega_id))

        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lt=_fecha_hasta_exclusiva(fecha_hasta))
        if producto_id:
            qs = qs.filter(producto_id=producto_id)
        if lote_codigo:
            qs = qs.filter(lote__codigo_lote=lote_codigo)

        data = list(
            qs.values(
                "id",
                "fecha",
                "tipo_movimiento",
                "cantidad",
                "saldo_resultante",
                "documento_ref",
                producto_descripcion=F("producto__descripcion"),
                bodega_origen_nombre=F("bodega_origen__nombre"),
            )
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
        qs = Producto.objects.all()
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(
            qs.values(
                "id",
                "codigo",
                "descripcion",
                "tipo",
                "unidad_medida",
                "precio_base",
                "stock_minimo",
            )
        )
        return Response(data)


class UsuariosView(APIView):
    """GET /api/internal/v1/reports/usuarios/?sede_id="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_usuarios")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        qs = CustomUser.objects.all()
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(
            qs.values(
                "id",
                "username",
                "first_name",
                "last_name",
                "email",
                sede_nombre=F("sede__nombre"),
            )
        )
        return Response(data)


class StockActualView(APIView):
    """GET /api/internal/v1/reports/stock-actual/?bodega_id="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_stock_actual")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        producto_id = request.query_params.get("producto_id")
        qs = StockBodega.objects.select_related("producto", "bodega", "lote").filter(
            bodega_id=bodega_id, cantidad__gt=0
        )
        if producto_id:
            qs = qs.filter(producto_id=producto_id)
        data = list(
            qs.values(
                "id",
                "cantidad",
                producto_descripcion=F("producto__descripcion"),
                producto_codigo=F("producto__codigo"),
                bodega_nombre=F("bodega__nombre"),
                lote_codigo=F("lote__codigo_lote"),
            )
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
        qs = StockBodega.objects.select_related("producto").filter(
            bodega_id=bodega_id, cantidad__gt=0
        )
        data = list(
            qs.annotate(valor_total=F("cantidad") * F("producto__precio_base")).values(
                "id",
                "cantidad",
                "valor_total",
                producto_descripcion=F("producto__descripcion"),
                precio_base=F("producto__precio_base"),
            )
        )
        return Response(data)


class AgingView(APIView):
    """GET /api/internal/v1/reports/aging/?bodega_id=&dias_minimos="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_aging")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        from datetime import timedelta

        from django.utils import timezone

        dias = int(request.query_params.get("dias_minimos", 30))
        corte = timezone.now() - timedelta(days=dias)
        productos_con_movimiento_reciente = MovimientoInventario.objects.filter(
            Q(bodega_origen_id=bodega_id) | Q(bodega_destino_id=bodega_id), fecha__gte=corte
        ).values_list("producto_id", flat=True)
        qs = StockBodega.objects.select_related("producto").filter(
            bodega_id=bodega_id, cantidad__gt=0
        ).exclude(producto_id__in=productos_con_movimiento_reciente)
        data = list(
            qs.values(
                "id",
                "cantidad",
                producto_descripcion=F("producto__descripcion"),
            )
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
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        # NOTA: solo bodega_origen_id (a diferencia de Kardex/Resumen) es
        # intencional aquí — "total_salidas" debe sumar únicamente
        # movimientos de salida (VENTA/CONSUMO/MERMA/TRANSFERENCIA saliente),
        # y solo esos tipos setean bodega_origen (ver
        # MovimientoInventarioViewSet.create() en inventory/views/movimiento_views.py).
        # Un OR con bodega_destino_id mezclaría entradas dentro de "salidas".
        qs = MovimientoInventario.objects.filter(bodega_origen_id=bodega_id)
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lt=_fecha_hasta_exclusiva(fecha_hasta))
        data = list(
            # HALLAZGO QA: MovimientoInventario.Meta.ordering = ['-fecha'] se
            # aplica implícitamente a cualquier queryset del modelo. SQL Server
            # rechaza un ORDER BY sobre una columna no agregada/agrupada en una
            # consulta GROUP BY (values().annotate()) -> 500. order_by() vacío
            # limpia el ordering por defecto antes de agrupar.
            qs.order_by().values(producto_descripcion=F("producto__descripcion")).annotate(
                total_salidas=Sum("cantidad")
            )
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
        qs = StockBodega.objects.select_related("producto").filter(
            bodega_id=bodega_id, cantidad=0
        )
        data = list(
            qs.values("id", "cantidad", producto_descripcion=F("producto__descripcion"))
        )
        return Response(data)


class ResumenMovimientosView(APIView):
    """GET /api/internal/v1/reports/resumen-movimientos/?bodega_id=&fecha_desde=&fecha_hasta="""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_resumen_movimientos")
        bodega_id = request.query_params.get("bodega_id")
        if not bodega_id:
            return Response({"detail": "bodega_id requerido."}, status=400)
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        qs = MovimientoInventario.objects.filter(bodega_origen_id=bodega_id)
        if fecha_desde:
            qs = qs.filter(fecha__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha__lt=_fecha_hasta_exclusiva(fecha_hasta))
        # HALLAZGO QA: mismo problema que RotacionView — limpiar el ordering
        # por defecto del modelo antes de agrupar (ver comentario ahí).
        data = list(qs.order_by().values("tipo_movimiento").annotate(total=Sum("cantidad")))
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
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        qs = PedidoVenta.objects.filter(
            vendedor_asignado_id=vendedor_id, anulado=False
        ).select_related("cliente")
        if fecha_desde:
            qs = qs.filter(fecha_pedido__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_pedido__lt=_fecha_hasta_exclusiva(fecha_hasta))
        data = list(
            qs.values(
                "id",
                "guia_remision",
                "fecha_pedido",
                "estado",
                "esta_pagado",
                cliente_nombre=F("cliente__nombre_razon_social"),
            )
        )
        return Response(data)


class TopClientesVendedorView(APIView):
    """GET /api/internal/v1/vendedores/{vendedor_id}/top-clientes/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request, vendedor_id: int):
        _audit(request, "get_top_clientes_vendedor", f"vendedor/{vendedor_id}")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        qs = PedidoVenta.objects.filter(
            vendedor_asignado_id=vendedor_id, anulado=False
        )
        if fecha_desde:
            qs = qs.filter(fecha_pedido__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_pedido__lt=_fecha_hasta_exclusiva(fecha_hasta))
        data = list(
            # HALLAZGO QA: aliasear una annotation como `cliente_id` choca con
            # el atributo `cliente_id` que Django genera para el FK `cliente`
            # -> ValueError en cualquier request (antes de tocar la BD). Se usa
            # el nombre real del campo (sin alias) para incluirlo sin
            # colisión; la clave de salida sigue siendo `cliente_id`.
            # `total_pedidos` debía ser un conteo de pedidos, no Sum(id).
            qs.values(
                "cliente_id",
                cliente_nombre=F("cliente__nombre_razon_social"),
            )
            .annotate(total_pedidos=Count("id"))
            .order_by("-total_pedidos")[:10]
        )
        return Response(data)


class DeudoresVendedorView(APIView):
    """GET /api/internal/v1/vendedores/{vendedor_id}/deudores/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request, vendedor_id: int):
        _audit(request, "get_deudores_vendedor", f"vendedor/{vendedor_id}")
        qs = Cliente.objects.filter(
            vendedor_asignado_id=vendedor_id, is_active=True
        ).annotate(
            total_pagado=Coalesce(
                Sum("pagos__monto"), Value(0), output_field=DecimalField()
            ),
        )
        data = list(
            qs.values(
                "id",
                "nombre_razon_social",
                "limite_credito",
                "plazo_credito_dias",
                "total_pagado",
            )
        )
        return Response(data)


# ──────────────────────────────────────────────────────────
# GERENCIAL
# ──────────────────────────────────────────────────────────


class VentasGerencialView(APIView):
    """GET /api/internal/v1/gerencial/ventas/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_ventas_gerencial")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        qs = PedidoVenta.objects.filter(anulado=False).select_related(
            "cliente__sede"
        )
        if fecha_desde:
            qs = qs.filter(fecha_pedido__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_pedido__lt=_fecha_hasta_exclusiva(fecha_hasta))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(
            qs.values(
                "id",
                "guia_remision",
                "fecha_pedido",
                "estado",
                "esta_pagado",
                cliente_nombre=F("cliente__nombre_razon_social"),
                sede_nombre=F("sede__nombre"),
            )
        )
        return Response(data)


class TopClientesGerencialView(APIView):
    """GET /api/internal/v1/gerencial/top-clientes/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_top_clientes_gerencial")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        qs = PedidoVenta.objects.filter(anulado=False)
        if fecha_desde:
            qs = qs.filter(fecha_pedido__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_pedido__lt=_fecha_hasta_exclusiva(fecha_hasta))
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(
            # HALLAZGO QA: mismo problema que TopClientesVendedorView — ver
            # comentario ahí (colisión de alias `cliente_id` + Sum(id) en vez
            # de Count(id)).
            qs.values(
                "cliente_id",
                cliente_nombre=F("cliente__nombre_razon_social"),
            )
            .annotate(total_pedidos=Count("id"))
            .order_by("-total_pedidos")[:20]
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
        qs = Cliente.objects.filter(is_active=True).annotate(
            total_pagado=Coalesce(
                Sum("pagos__monto"), Value(0), output_field=DecimalField()
            ),
        )
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(
            qs.values(
                "id",
                "nombre_razon_social",
                "limite_credito",
                "total_pagado",
            )
        )
        return Response(data)


# ──────────────────────────────────────────────────────────
# PRODUCCIÓN
# ──────────────────────────────────────────────────────────


class OrdenesProduccionView(APIView):
    """GET /api/internal/v1/produccion/ordenes/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_ordenes_produccion")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        qs = OrdenProduccion.objects.select_related("producto_salida", "sede")
        if fecha_desde:
            qs = qs.filter(fecha_creacion__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(fecha_creacion__lte=fecha_hasta)
        if sede_id:
            qs = qs.filter(sede_id=sede_id)
        data = list(
            qs.values(
                "id",
                "codigo",
                "estado",
                "prioridad",
                "fecha_creacion",
                "peso_neto_requerido",
                producto_descripcion=F("producto_salida__descripcion"),
                sede_nombre=F("sede__nombre"),
            )
        )
        return Response(data)


class LotesProduccionView(APIView):
    """GET /api/internal/v1/produccion/lotes/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_lotes_produccion")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        qs = LoteProduccion.objects.select_related(
            "orden_produccion__producto_salida", "orden_produccion__sede"
        )
        if fecha_desde:
            qs = qs.filter(hora_inicio__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(hora_inicio__lt=_fecha_hasta_exclusiva(fecha_hasta))
        if sede_id:
            qs = qs.filter(orden_produccion__sede_id=sede_id)
        data = list(
            qs.values(
                "id",
                "codigo_lote",
                "peso_neto_producido",
                "hora_inicio",
                "hora_final",
                "clasificacion_calidad",
                producto_descripcion=F("orden_produccion__producto_salida__descripcion"),
                op_codigo=F("orden_produccion__codigo"),
            )
        )
        return Response(data)


class TendenciaProduccionView(APIView):
    """GET /api/internal/v1/produccion/tendencia/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_tendencia_produccion")
        fecha_desde = request.query_params.get("fecha_desde")
        fecha_hasta = request.query_params.get("fecha_hasta")
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error
        from django.db.models.functions import TruncDate

        qs = LoteProduccion.objects.select_related("orden_produccion__sede")
        if fecha_desde:
            qs = qs.filter(hora_inicio__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(hora_inicio__lt=_fecha_hasta_exclusiva(fecha_hasta))
        if sede_id:
            qs = qs.filter(orden_produccion__sede_id=sede_id)
        data = list(
            qs.annotate(fecha=TruncDate("hora_inicio"))
            .values("fecha")
            .annotate(
                total_peso=Sum("peso_neto_producido"),
                total_lotes=Sum(Value(1)),
            )
            .order_by("fecha")
        )
        return Response(data)


class PlantaPulsoDiarioView(APIView):
    """GET /api/internal/v1/planta/pulso-diario/"""

    authentication_classes = _AUTH
    permission_classes = _PERMS

    def get(self, request):
        _audit(request, "get_pulso_diario")
        from django.utils import timezone
        from gestion.models import TransferenciaInterarea

        hoy = timezone.now().date()
        sede_id, _sede_error = resolve_sede_scope(request)
        if _sede_error is not None:
            return _sede_error

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
