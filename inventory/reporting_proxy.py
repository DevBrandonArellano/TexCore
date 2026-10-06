import datetime
import decimal
import logging
import os
import re

import httpx
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from rest_framework.negotiation import DefaultContentNegotiation
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from gestion.models import Bodega
from gestion.permissions import ve_todas_las_sedes
from internal_api.authentication import JWTServiceAuthentication
from inventory.services.kardex_service import FiltroKardexInvalido

logger = logging.getLogger(__name__)


class _ProxyContentNegotiation(DefaultContentNegotiation):
    """
    Desactiva la negociación de contenido de DRF vía `?format=`.

    ReportingProxyView reenvía `format=xlsx`/`format=csv` tal cual al
    microservicio (es un parámetro de negocio, no de renderizado) y responde
    siempre con HttpResponse/JsonResponse crudos, nunca con `Response` de
    DRF — el renderer negociado no se usa para renderizar nada. Sin este
    override, `DefaultContentNegotiation.select_renderer` intercepta
    `?format=xlsx` como si fuera su propio parámetro de negociación
    (`URL_FORMAT_OVERRIDE`), no encuentra un renderer DRF para 'xlsx' y
    lanza `Http404` antes de que `get()` llegue a ejecutarse.
    """

    def select_renderer(self, request, renderers, format_suffix=None):
        return renderers[0], renderers[0].media_type


# Patrón de rutas permitidas — whitelist explícita para prevenir Path Traversal
_ALLOWED_REPORT_PATH = re.compile(
    r'^(export|vendedores|gerencial|produccion)'
    r'(/[a-zA-Z0-9_-]+)*'
    r'$'
)


def _json_safe(value):
    """
    Convierte recursivamente los tipos que QuerySet.values() puede producir
    (Decimal, date, datetime) y que el codec JSON de httpx no serializa por
    sí solo, a tipos nativos de JSON — necesario ahora que reporting_proxy
    envía los datos ya resueltos a reporting_excel en vez de que él los
    vuelva a consultar.
    """
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, (datetime.datetime, datetime.date)):
        return value.isoformat()
    return value


def _validate_report_path(report_path: str) -> bool:
    """
    Valida que el path del reporte sea seguro.
    Previene Path Traversal y acceso a rutas no autorizadas.
    """
    clean = report_path.lstrip('/')
    if '..' in clean or '//' in clean or '\\' in clean:
        return False
    return bool(_ALLOWED_REPORT_PATH.match(clean))


# Reportes que exigen bodega_id (los generales, como el catálogo de productos, no).
_REPORTES_POR_BODEGA = (
    'kardex', 'stock-actual', 'stock-cero', 'stock-bajo', 'valorizacion',
    'aging', 'rotacion', 'resumen-movimientos',
)

_RESPUESTA_ASYNC_NO_DISPONIBLE = {
    "detail": "La exportación asíncrona no está disponible en este entorno. "
              "Solicite el reporte sin el parámetro async."
}


def _tiene_acceso_a_bodega(user, bodega):
    # 1. Asignación explícita (M2M); bodega.id (int) asegura consistencia con el ORM.
    if user.bodegas_asignadas.filter(id=bodega.id).exists():
        return True
    # 2. Fallback: misma sede que la bodega. Cubre al administrador que asignó la sede
    #    pero no individualmente las bodegas.
    user_sede_id = getattr(user, 'sede_id', None)
    return bool(user_sede_id) and bodega.sede_id == user_sede_id


def _denegar_por_bodega(user, report_path, bodega_id, is_admin):
    """Valida bodega_id en los reportes que la exigen. Devuelve la respuesta de error o None."""
    if not any(reporte in report_path for reporte in _REPORTES_POR_BODEGA):
        return None
    if not bodega_id:
        return JsonResponse({"detail": "bodega_id es requerido para este reporte"}, status=400)
    try:
        bodega = Bodega.objects.get(id=bodega_id)
    except Bodega.DoesNotExist:
        return JsonResponse({"detail": "Bodega no encontrada"}, status=404)
    if is_admin or _tiene_acceso_a_bodega(user, bodega):
        return None
    logger.warning(
        "Acceso denegado a reporte para usuario %s: bodega_id=%s (Sede Usuario: %s, Sede Bodega: %s)",
        user.username, bodega.id, getattr(user, 'sede_id', 'N/A'), bodega.sede_id
    )
    return JsonResponse({"detail": "No tiene permiso para acceder a esta bodega"}, status=403)


def _params_reenviados(query_params, user, is_admin):
    """Parámetros para el reporte y su formato.

    Aislamiento por sede (OWASP A01 — Broken Access Control / IDOR): para un usuario NO
    global NUNCA se confía en el `sede_id` que envía el cliente. Se DESCARTA siempre y solo
    se re-deriva de la identidad:
      - con sede → se fuerza su propia sede (no puede consultar otra);
      - sin sede → queda ausente: el cliente NO puede elegir una sede ajena (fail-safe).
    No se bloquea con 403 porque el modelo de acceso del bodeguero es por BODEGA
    (`bodegas_asignadas`), no por sede, y esa restricción ya la impone la whitelist de
    bodega; los reportes generales (catálogo) no tienen dimensión de sede.
    (Antes se enviaba un 'user_sede_id' que ningún servicio leía — dead code.)
    """
    params = query_params.dict()
    report_format = params.pop('format', 'xlsx')
    if not is_admin:
        params.pop('sede_id', None)  # nunca confiar en el valor del cliente
        user_sede_id = getattr(user, 'sede_id', None)
        if user_sede_id:
            params['sede_id'] = str(user_sede_id)
    return params, report_format


def _encolar_exportacion(clean_path, params, report_format, user):
    # En producción no se despliega Redis (las exportaciones síncronas miden p95 < 250 ms).
    # Con el broker caído, .delay() tarda 20-70 s en fallar (reintentos de kombu y del
    # result backend) y bloquea un worker síncrono de gunicorn: si el entorno no habilita
    # la exportación asíncrona se responde 503 al instante, sin encolar.
    if not getattr(settings, 'REPORTES_ASYNC_HABILITADO', False):
        return JsonResponse(_RESPUESTA_ASYNC_NO_DISPONIBLE, status=503)

    from kombu.exceptions import OperationalError

    from gestion.tasks import async_export_report
    # Segunda defensa: el flag está activo pero el broker se cae en tiempo de
    # ejecución → 503 explícito en vez de un 500.
    try:
        task = async_export_report.delay(
            report_path=clean_path,
            params=params,
            report_format=report_format,
            user_id=user.id
        )
    except OperationalError as exc:
        logger.warning(
            "Exportación asíncrona no disponible (broker caído) para '%s': %s",
            clean_path, exc,
        )
        return JsonResponse(_RESPUESTA_ASYNC_NO_DISPONIBLE, status=503)
    return JsonResponse({
        "detail": "Reporte encolado para generación en background.",
        "task_id": task.id
    }, status=202)


def _respuesta_de_error_del_servicio(response, report_path):
    logger.warning(
        "Report service returned status %s for path '%s'",
        response.status_code, report_path,
        extra={'sd': {'report_path': report_path, 'status': response.status_code}}
    )
    try:
        error_detail = response.json()
    except ValueError:  # cuerpo no JSON
        error_detail = {"detail": f"Error {response.status_code} en el microservicio de reportes"}
    return JsonResponse(error_detail, status=response.status_code)


def _generar_archivo(clean_path, report_path, report_format, rows, filename):
    """Envía los datos ya resueltos a reporting_excel y devuelve el binario generado."""
    service_url = os.getenv("REPORTING_SERVICE_URL", "http://reporting_excel:8002")
    service_token = JWTServiceAuthentication.generate_token(
        service_name="backend-proxy",
        scopes=["reports:read"],
    )
    headers = {"Authorization": f"Bearer {service_token}"}

    try:
        # Serializar tipos no nativos de JSON (Decimal, datetime) que
        # vienen de QuerySet.values() antes de mandarlos a reporting_excel.
        body = {
            "format": report_format,
            "filename": filename,
            "report_type": clean_path.replace("/", "_"),
            "rows": _json_safe(rows),
        }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{service_url}/generate", json=body, headers=headers)
            if response.status_code != 200:
                return _respuesta_de_error_del_servicio(response, report_path)

            django_response = HttpResponse(
                content=response.content,
                status=response.status_code,
                content_type=response.headers.get("Content-Type")
            )
            # Copiar headers importantes de descarga
            for cabecera in ("Content-Disposition", "X-Report-Empty"):
                if cabecera in response.headers:
                    django_response[cabecera] = response.headers[cabecera]
            return django_response

    except httpx.RequestError as exc:
        logger.exception("Error de conexión con reporting_excel: %s", exc)
        return JsonResponse({"detail": "Error de conexión con el servicio de reportes"}, status=502)
    except Exception:
        logger.exception("Error inesperado en ReportingProxyView para ruta '%s'", report_path)
        return JsonResponse({"detail": "Error interno del servidor"}, status=500)


class ReportingProxyView(APIView):
    permission_classes = [IsAuthenticated]
    content_negotiation_class = _ProxyContentNegotiation

    def get(self, request, report_path):
        user = request.user
        logger.info(
            "Proxying report request: path='%s', user='%s', params=%s",
            report_path, user.username, request.query_params,
            extra={'sd': {'report_path': report_path, 'user': user.username, 'params': request.query_params.dict()}}
        )

        # Rol de acceso: los roles globales pueden consultar cualquier sede; el
        # resto queda acotado a su propia sede (aislamiento OWASP A01). Se calcula
        # una sola vez y se reutiliza en la validación de bodega y de sede.
        is_admin = ve_todas_las_sedes(user)

        denegado = _denegar_por_bodega(user, report_path, request.query_params.get('bodega_id'), is_admin)
        if denegado:
            return denegado

        # Validar el path contra whitelist antes de procesar (previene Path Traversal)
        if not _validate_report_path(report_path):
            logger.warning(
                "Intento de path traversal bloqueado: '%s' por usuario %s (ip: %s)",
                report_path, user.username, request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({"detail": "Ruta de reporte no permitida"}, status=400)

        clean_path = report_path.lstrip('/')
        params, report_format = _params_reenviados(request.query_params, user, is_admin)

        if request.query_params.get('async', 'false').lower() == 'true':
            return _encolar_exportacion(clean_path, params, report_format, user)

        # Consultar los datos EN PROCESO (sin red) en vez de reenviar la
        # petición a reporting_excel para que él vuelva a pedírselos al
        # backend por HTTP. Ese salto redundante (backend -> reporting_excel
        # -> de vuelta al backend) tenía el timeout más corto de toda la
        # cadena (30s) y era el primer punto de falla bajo alta concurrencia
        # — ver auditoría de performance 2026-08-31. reporting_excel ahora
        # solo recibe los datos ya resueltos y los formatea a Excel/CSV.
        from internal_api.services.report_dispatch import resolve_report

        try:
            rows, filename = resolve_report(clean_path, params)
        except FiltroKardexInvalido as exc:
            # Filtro mal formado (p. ej. fecha inválida): el motivo real, no "ruta no permitida".
            return JsonResponse({"detail": str(exc)}, status=400)
        except ValueError:
            logger.warning(
                "Ruta de reporte sin mapeo de datos: '%s' por usuario %s",
                report_path, user.username
            )
            return JsonResponse({"detail": "Ruta de reporte no permitida"}, status=400)
        except Exception:
            logger.exception("Error consultando datos para el reporte '%s'", report_path)
            return JsonResponse({"detail": "Error interno del servidor"}, status=500)

        return _generar_archivo(clean_path, report_path, report_format, rows, filename)
