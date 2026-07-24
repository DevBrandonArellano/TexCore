import httpx
import logging
import os
import re

from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse, JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from gestion.models import Bodega
from internal_api.authentication import JWTServiceAuthentication

logger = logging.getLogger(__name__)


def _get_required_env(var_name: str) -> str:
    """Obtiene una variable de entorno requerida. Falla si no existe (Fail-Fast)."""
    value = os.environ.get(var_name)
    if not value:
        raise ImproperlyConfigured(
            f"Variable de entorno requerida no configurada: '{var_name}'"
        )
    return value


# Patrón de rutas permitidas — whitelist explícita para prevenir Path Traversal
_ALLOWED_REPORT_PATH = re.compile(
    r'^(export|vendedores|gerencial|produccion)'
    r'(/[a-zA-Z0-9_-]+)*'
    r'$'
)


def _validate_report_path(report_path: str) -> bool:
    """
    Valida que el path del reporte sea seguro.
    Previene Path Traversal y acceso a rutas no autorizadas.
    """
    clean = report_path.lstrip('/')
    if '..' in clean or '//' in clean or '\\' in clean:
        return False
    return bool(_ALLOWED_REPORT_PATH.match(clean))


class ReportingProxyView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, report_path):
        user = request.user
        logger.info(
            "Proxying report request: path='%s', user='%s', params=%s",
            report_path, user.username, request.query_params,
            extra={'sd': {'report_path': report_path, 'user': user.username, 'params': request.query_params.dict()}}
        )

        # 1. Obtener parámetros
        bodega_id = request.query_params.get('bodega_id')

        # 2. Validación de permisos para reportes que requieren bodega_id
        # Reportes generales que no requieren bodega_id específica (ej: catalogo productos)
        reports_requiring_bodega = [
            'kardex', 'stock-actual', 'stock-cero', 'valorizacion',
            'aging', 'rotacion', 'resumen-movimientos'
        ]

        is_restricted_report = any(req in report_path for req in reports_requiring_bodega)

        if is_restricted_report:
            if not bodega_id:
                return JsonResponse({"detail": "bodega_id es requerido para este reporte"}, status=400)

            try:
                bodega = Bodega.objects.get(id=bodega_id)
            except Bodega.DoesNotExist:
                return JsonResponse({"detail": "Bodega no encontrada"}, status=404)

            # Verificar si el usuario es admin o tiene la bodega asignada
            is_admin = user.is_superuser or user.groups.filter(
                name__in=['admin_sistemas', 'admin_sede', 'ejecutivo']
            ).exists()

            if not is_admin:
                # 1. Verificar asignación explícita (M2M)
                # Usamos bodega.id (int) para asegurar consistencia con el ORM
                has_access = user.bodegas_asignadas.filter(id=bodega.id).exists()

                # 2. Fallback: Verificar si el usuario pertenece a la misma sede de la bodega
                # Esto cubre casos donde el administrador asignó la sede pero no individualmente las bodegas
                if not has_access and hasattr(user, 'sede_id') and user.sede_id:
                    if bodega.sede_id == user.sede_id:
                        has_access = True

                if not has_access:
                    logger.warning(
                        "Acceso denegado a reporte para usuario %s: bodega_id=%s (Sede Usuario: %s, Sede Bodega: %s)",
                        user.username, bodega.id, getattr(user, 'sede_id', 'N/A'), bodega.sede_id
                    )
                    return JsonResponse({"detail": "No tiene permiso para acceder a esta bodega"}, status=403)

        # 3. Preparar llamada al microservicio
        service_url = os.getenv("REPORTING_SERVICE_URL", "http://reporting_excel:8002")

        # Validar el path contra whitelist antes de hacer el proxy (previene Path Traversal)
        if not _validate_report_path(report_path):
            logger.warning(
                "Intento de path traversal bloqueado: '%s' por usuario %s (ip: %s)",
                report_path, user.username, request.META.get('REMOTE_ADDR')
            )
            return JsonResponse({"detail": "Ruta de reporte no permitida"}, status=400)

        # Generar Token de Servicio (JWT RS256) para el proxy
        service_token = JWTServiceAuthentication.generate_token(
            service_name="backend-proxy",
            scopes=["reports:read"]
        )

        clean_path = report_path.lstrip('/')
        target_url = f"{service_url}/{clean_path}"

        # Forwarding params
        params = request.query_params.dict()

        # Agregar sede_id del usuario si existe para filtrar en el SP (opcional para el SP)
        if hasattr(user, 'sede_id') and user.sede_id:
            params['user_sede_id'] = user.sede_id

        headers = {
            "Authorization": f"Bearer {service_token}"
        }

        # Verificar si la petición es asíncrona
        is_async = request.query_params.get('async', 'false').lower() == 'true'

        if is_async:
            from gestion.tasks import async_export_report
            # Enviar la tarea a Celery
            task = async_export_report.delay(
                report_path=clean_path,
                params=params,
                user_id=user.id
            )
            return JsonResponse({
                "detail": "Reporte encolado para generación en background.",
                "task_id": task.id
            }, status=202)

        try:
            # Usar un timeout razonable para generación de Excel
            with httpx.Client(timeout=60.0) as client:
                response = client.get(target_url, params=params, headers=headers)

                if response.status_code != 200:
                    logger.warning(
                        "Report service returned status %s for path '%s'",
                        response.status_code, report_path,
                        extra={'sd': {'report_path': report_path, 'status': response.status_code}}
                    )
                    try:
                        error_detail = response.json()
                    except BaseException:
                        error_detail = {"detail": f"Error {response.status_code} en el microservicio de reportes"}
                    return JsonResponse(error_detail, status=response.status_code)

                # 4. Retornar el binario
                django_response = HttpResponse(
                    content=response.content,
                    status=response.status_code,
                    content_type=response.headers.get("Content-Type")
                )

                # Copiar headers importantes de descarga
                if "Content-Disposition" in response.headers:
                    django_response["Content-Disposition"] = response.headers["Content-Disposition"]

                return django_response

        except httpx.RequestError as exc:
            logger.error("Error de conexión con reporting_excel: %s", exc)
            return JsonResponse({"detail": "Error de conexión con el servicio de reportes"}, status=502)
        except Exception:
            logger.exception("Error inesperado en ReportingProxyView para ruta '%s'", report_path)
            return JsonResponse({"detail": "Error interno del servidor"}, status=500)
