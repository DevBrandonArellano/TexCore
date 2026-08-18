"""
Vistas de generación de PDFs de producción para internal_api.

Arquitectura:
  - POST /api/internal/v1/reports/produccion/reporte-avance/
  - POST /api/internal/v1/reports/produccion/reporte-balance/

DIP: httpx.Client se inyecta desde settings → fácil de sustituir en tests.
SRP: cada view orquesta solo su caso de uso:
  1. Consultar ORM / SP vía Django
  2. Armar payload coincidente con el schema del printing_service
  3. Proxiar el stream PDF al cliente React
ISO 27001 A.12.4: auditoría de la acción antes de llamar al servicio externo.
"""
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from django.conf import settings
from django.db.models import F
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from django.http import StreamingHttpResponse


from gestion.models import LoteProduccion
from rest_framework.permissions import BasePermission
from rest_framework_simplejwt.authentication import JWTAuthentication

from gestion.auth_backends import CookieJWTAuthentication
from internal_api.audit import AuditLogger
from internal_api.authentication import JWTServiceAuthentication, ServicePrincipal
from inventory.models import MovimientoInventario, StockBodega

logger = logging.getLogger(__name__)


def _resolve_sede_scope(request, requested_sede_id):
    """
    Impone aislamiento por sede (OWASP A01) para llamadas de usuarios humanos.

    Retorna (sede_id, error_response | None):
      - ServicePrincipal (canal servicio-a-servicio, ya acotado por scope):
        conserva el sede_id solicitado sin restricción.
      - Usuario global (superuser / admin_sistemas / ejecutivo): puede pedir
        cualquier sede o ninguna.
      - Resto (jefe_planta / jefe_area / admin_sede): forzado a SU sede; un
        sede_id ajeno explícito → 403.
    """
    user = request.user
    if isinstance(user, ServicePrincipal):
        return requested_sede_id, None

    is_global = user.is_superuser or user.groups.filter(
        name__in=['admin_sistemas', 'ejecutivo']
    ).exists()
    if is_global:
        return requested_sede_id, None

    user_sede_id = getattr(user, 'sede_id', None)
    if not user_sede_id:
        return None, Response(
            {"detail": "No tienes una sede asignada para generar este reporte."},
            status=403,
        )
    if requested_sede_id and str(requested_sede_id) != str(user_sede_id):
        logger.warning(
            "Intento de generar reporte PDF de otra sede",
            extra={"sd": {
                "entity": "PdfProduccion",
                "user": getattr(user, "username", "?"),
                "sede_usuario": user_sede_id,
                "sede_solicitada": requested_sede_id,
            }},
        )
        return None, Response(
            {"detail": "No tienes permiso para generar reportes de otra sede."},
            status=403,
        )
    return user_sede_id, None


class IsInternalServiceOrUser(BasePermission):
    """
    ISO 27001 A.9.4 / COBIT DSS06:
    Permite acceso tanto a microservicios autorizados (JWT RS256 con scope 'reports:read')
    como a usuarios autenticados con roles de gestión/producción.
    """
    message = "Acceso no autorizado a reportes de producción."

    def has_permission(self, request, view) -> bool:
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        # ServicePrincipal (service-to-service)
        if isinstance(user, ServicePrincipal):
            return "reports:read" in getattr(user, "scopes", [])

        # Regular user (CustomUser)
        return user.is_superuser or user.groups.filter(
            name__in=["jefe_planta", "jefe_area", "admin_sistemas", "admin_sede", "ejecutivo"]
        ).exists()


_AUTH = [JWTServiceAuthentication, CookieJWTAuthentication, JWTAuthentication]
_PERMS = [IsInternalServiceOrUser]

# URL base del microservicio de impresión.
# Configurable por variable de entorno PRINTING_SERVICE_URL en settings.
_PRINTING_URL: str = getattr(settings, "PRINTING_SERVICE_URL", "http://printing_service:8003")

# Timeout en segundos para la llamada al printing_service.
# WeasyPrint puede tardar para documentos grandes.
_PDF_TIMEOUT: float = getattr(settings, "PRINTING_PDF_TIMEOUT", 60.0)


def _get_printing_url() -> str:
    return getattr(settings, "PRINTING_SERVICE_URL", "http://printing_service:8001")


def _now_iso() -> str:
    """Retorna el instante actual en ISO 8601 UTC."""
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _audit(request: Request, action: str) -> None:
    service_identifier = (
        getattr(request.user, "service_name", None)
        or getattr(request.user, "username", "usuario_desconocido")
    )
    AuditLogger.log(
        service=service_identifier,
        action=action,
        resource="reports/produccion",
    )


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de construcción de payload
# ─────────────────────────────────────────────────────────────────────────────

def _build_reporte_avance_payload(
    ordenes_qs,
    empresa_nombre: str,
    sede_nombre: str,
    fecha_desde: Optional[str],
    fecha_hasta: Optional[str],
    maquina_filtro: Optional[str],
    operario_filtro: Optional[str],
) -> dict:
    """
    Traduce los registros del ORM al schema ReporteAvanceRequest del
    printing_service. Cero lógica de negocio: solo mapeo de campos.
    """
    detalles = []
    for lote in ordenes_qs:
        peso_requerido = float(lote.get("orden_peso_requerido") or 0)
        kilos = float(lote.get("peso_neto_producido") or 0)
        porcentaje = round((kilos / peso_requerido * 100), 2) if peso_requerido > 0 else 0.0

        detalles.append({
            "orden": str(lote.get("op_codigo") or "—"),
            "producto": str(lote.get("producto_descripcion") or "—"),
            "lote": str(lote.get("codigo_lote") or "—"),
            "maquina": str(lote.get("maquina_nombre") or "—"),
            "operario": str(lote.get("operario_nombre") or "—"),
            "kilos": kilos,
            "porcentaje_avance": porcentaje,
            "estado": str(lote.get("op_estado") or "—"),
        })

    return {
        "empresa_nombre": empresa_nombre,
        "sede_nombre": sede_nombre,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "maquina_filtro": maquina_filtro,
        "operario_filtro": operario_filtro,
        "generado_en": _now_iso(),
        "detalles": detalles,
    }


def _build_balance_masas_payload(
    stock_qs,
    movimientos_qs,
    empresa_nombre: str,
    sede_nombre: str,
    mes_label: str,
) -> dict:
    """
    Traduce stock actual + movimientos del mes al schema BalanceMasasRequest
    del printing_service.
    Algoritmo:
      inventario_inicial = stock_actual - (produccion - egresos)
      is_negativo        = stock_actual < 0
    """
    # Indexar movimientos del mes por producto_id para O(1)
    produccion_por_producto: dict[int, float] = {}
    egresos_por_producto: dict[int, float] = {}
    for mov in movimientos_qs:
        pid = mov.get("producto_id")
        cant = float(mov.get("cantidad") or 0)
        tipo = str(mov.get("tipo_movimiento") or "")
        if tipo in ("entrada", "produccion", "ENTRADA", "PRODUCCION"):
            produccion_por_producto[pid] = produccion_por_producto.get(pid, 0) + cant
        else:
            egresos_por_producto[pid] = egresos_por_producto.get(pid, 0) + cant

    detalles = []
    for row in stock_qs:
        pid = row.get("producto_id") or row.get("id")
        stock_actual = float(row.get("cantidad") or 0)
        produccion = produccion_por_producto.get(pid, 0.0)
        egresos = egresos_por_producto.get(pid, 0.0)
        inv_inicial = round(stock_actual - (produccion - egresos), 4)

        detalles.append({
            "codigo": str(row.get("producto_codigo") or "—"),
            "descripcion": str(row.get("producto_descripcion") or "—"),
            "inventario_inicial": inv_inicial,
            "produccion": round(produccion, 4),
            "egresos": round(egresos, 4),
            "stock_actual": round(stock_actual, 4),
            "is_negativo": stock_actual < 0,
        })

    return {
        "empresa_nombre": empresa_nombre,
        "sede_nombre": sede_nombre,
        "mes": mes_label,
        "generado_en": _now_iso(),
        "detalles": detalles,
    }


def _proxy_pdf(payload: dict, endpoint: str, filename_base: str) -> StreamingHttpResponse:
    """
    Envía el payload al printing_service y proxia el stream PDF al cliente.
    DIP: _get_printing_url() proviene de settings, no hardcodeado aquí.
    """
    url = f"{_get_printing_url()}{endpoint}"

    try:
        with httpx.Client(timeout=_PDF_TIMEOUT) as client:
            upstream = client.post(url, json=payload)
            upstream.raise_for_status()
    except httpx.HTTPStatusError as exc:
        logger.error(
            "printing_service retornó error HTTP",
            extra={"sd": {
                "rfc5424_severity": 3,
                "endpoint": endpoint,
                "status_code": str(exc.response.status_code),
                "detail": exc.response.text[:200],
            }},
        )
        return Response(
            {"detail": f"Error del servicio de impresión: {exc.response.status_code}"},
            status=502,
        )
    except httpx.RequestError as exc:
        logger.error(
            "No se pudo conectar al printing_service",
            extra={"sd": {
                "rfc5424_severity": 3,
                "endpoint": endpoint,
                "error": str(exc)[:200],
            }},
        )
        return Response(
            {"detail": "Servicio de impresión no disponible."},
            status=503,
        )

    response = StreamingHttpResponse(
        streaming_content=iter([upstream.content]),
        content_type="application/pdf",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="{filename_base}_{_now_iso()[:10]}.pdf"'
    )
    return response


# ─────────────────────────────────────────────────────────────────────────────
# Vistas
# ─────────────────────────────────────────────────────────────────────────────

class ReporteAvancePdfView(APIView):
    """
    POST /api/internal/v1/reports/produccion/reporte-avance/

    Query params opcionales:
      fecha_desde, fecha_hasta  — ISO date string
      sede_id                   — int
      maquina_id                — int  (filtro sobre el lote)
      operario_id               — int  (filtro sobre el lote)

    Retorna: StreamingHttpResponse con content-type application/pdf
    """

    authentication_classes = _AUTH
    permission_classes = _PERMS
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request: Request) -> StreamingHttpResponse:
        _audit(request, "pdf_reporte_avance")

        # ── Parámetros de filtro ──────────────────────────────────────────
        fecha_desde = request.data.get("fecha_desde")
        fecha_hasta = request.data.get("fecha_hasta")
        sede_id = request.data.get("sede_id")
        maquina_id = request.data.get("maquina_id")
        operario_id = request.data.get("operario_id")
        empresa_nombre = request.data.get("empresa_nombre", "TexCore Industrial")

        # Aislamiento por sede: un usuario no-global queda acotado a su sede.
        sede_id, sede_error = _resolve_sede_scope(request, sede_id)
        if sede_error is not None:
            return sede_error

        # ── Consulta ORM (equivalente a sp_GetOrdenesProduccionGerencial) ─
        # Se usa select_related + prefetch para prevenir N+1 (AGENTS.md regla).
        qs = LoteProduccion.objects.select_related(
            "orden_produccion__producto_salida",
            "orden_produccion__sede",
            "maquina",
            "operario",
        )

        if fecha_desde:
            qs = qs.filter(hora_inicio__date__gte=fecha_desde)
        if fecha_hasta:
            qs = qs.filter(hora_inicio__date__lte=fecha_hasta)
        if sede_id:
            qs = qs.filter(orden_produccion__sede_id=sede_id)
        if maquina_id:
            qs = qs.filter(maquina_id=maquina_id)
        if operario_id:
            qs = qs.filter(operario_id=operario_id)

        registros = list(
            qs.values(
                "codigo_lote",
                "peso_neto_producido",
                "hora_inicio",
                op_codigo=F("orden_produccion__codigo"),
                op_estado=F("orden_produccion__estado"),
                op_peso_requerido=F("orden_produccion__peso_neto_requerido"),
                orden_peso_requerido=F("orden_produccion__peso_neto_requerido"),
                producto_descripcion=F("orden_produccion__producto_salida__descripcion"),
                sede_nombre_qs=F("orden_produccion__sede__nombre"),
                maquina_nombre=F("maquina__nombre"),
                operario_nombre=F("operario__username"),
            )
        )

        sede_nombre = (
            registros[0].get("sede_nombre_qs", "Sede")
            if registros
            else request.data.get("sede_nombre", "Sede")
        )

        maquina_label = None
        operario_label = None
        if registros and maquina_id:
            maquina_label = registros[0].get("maquina_nombre")
        if registros and operario_id:
            operario_label = registros[0].get("operario_nombre")

        payload = _build_reporte_avance_payload(
            ordenes_qs=registros,
            empresa_nombre=empresa_nombre,
            sede_nombre=sede_nombre,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            maquina_filtro=maquina_label,
            operario_filtro=operario_label,
        )

        return _proxy_pdf(payload, "/pdf/reporte-avance", "reporte_avance")


class BalanceMasasPdfView(APIView):
    """
    POST /api/internal/v1/reports/produccion/reporte-balance/

    Body JSON:
      mes_label     — str  (ej. "Julio 2025")
      sede_id       — int  (requerido)
      empresa_nombre — str (opcional)

    Retorna: StreamingHttpResponse con content-type application/pdf
    """

    authentication_classes = _AUTH
    permission_classes = _PERMS
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request: Request) -> StreamingHttpResponse:
        _audit(request, "pdf_balance_masas")

        sede_id = request.data.get("sede_id")
        mes_label = request.data.get("mes_label", "")
        empresa_nombre = request.data.get("empresa_nombre", "TexCore Industrial")

        # Aislamiento por sede: para un usuario no-global se deriva de su
        # identidad (el cliente ya no envía sede_id). Un global debe indicarla.
        sede_id, sede_error = _resolve_sede_scope(request, sede_id)
        if sede_error is not None:
            return sede_error

        if not sede_id:
            return Response({"detail": "sede_id es requerido."}, status=400)

        from gestion.models import Bodega
        bodega_qs = Bodega.objects.filter(sede_id=sede_id).values_list("id", flat=True)
        bodega_ids = list(bodega_qs)

        stock_qs = list(
            StockBodega.objects.filter(bodega_id__in=bodega_ids)
            .values(
                "cantidad",
                "producto_id",
                producto_codigo=F("producto__codigo"),
                producto_descripcion=F("producto__descripcion"),
            )
        )

        mov_qs = list(
            MovimientoInventario.objects
            .filter(bodega_origen_id__in=bodega_ids)
            .values("tipo_movimiento", "cantidad", "producto_id")
        )

        sede_nombre = request.data.get("sede_nombre", f"Sede {sede_id}")

        payload = _build_balance_masas_payload(
            stock_qs=stock_qs,
            movimientos_qs=mov_qs,
            empresa_nombre=empresa_nombre,
            sede_nombre=sede_nombre,
            mes_label=mes_label,
        )

        return _proxy_pdf(payload, "/pdf/reporte-balance", "balance_masas")
