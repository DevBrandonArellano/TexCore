"""
Estado y descarga de las exportaciones encoladas en Celery (?async=true).

Flujo: el proxy de reportes (inventory/reporting_proxy.py) encola
gestion.tasks.async_export_report y responde 202 con un token firmado que lleva
el id de la tarea y el del usuario. El frontend consulta
/api/reporting/tareas/<token>/ hasta que el estado es "listo" y descarga
/api/reporting/tareas/<token>/descarga/. La tarea deja el archivo en
REPORTES_ASYNC_DIR (volumen compartido entre backend y celery_worker).

El token impide que un usuario consulte o descargue la tarea de otro (OWASP A01)
sin guardar nada en la base: la firma usa SECRET_KEY y vence con el archivo.
"""

import logging
import re
from pathlib import Path

from celery.result import AsyncResult
from django.conf import settings
from django.core import signing
from django.http import FileResponse, JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

logger = logging.getLogger(__name__)

_SALT = "inventory.reportes_async"
# Celery usa UUID como id de tarea; se valida aunque venga de un token firmado.
_ID_TAREA = re.compile(r"^[0-9a-f-]{36}$")
_EN_PROCESO = {"estado": "en_proceso"}


def firmar_tarea(task_id: str, user_id: int) -> str:
    return signing.dumps({"t": task_id, "u": user_id}, salt=_SALT, compress=True)


def leer_tarea(token: str, user_id: int) -> str | None:
    """Id de la tarea si el token es válido, no venció y pertenece al usuario; si no, None."""
    try:
        datos = signing.loads(token, salt=_SALT, max_age=settings.REPORTES_ASYNC_TTL_SEGUNDOS)
    except signing.BadSignature:  # incluye SignatureExpired
        return None
    if datos.get("u") != user_id:
        return None
    return datos.get("t")


def url_de_estado(token: str) -> str:
    return f"/api/reporting/tareas/{token}/"


def _resultado(task_id: str) -> tuple[str, dict | None]:
    """("listo", resultado) | ("error", None) | ("en_proceso", None)."""
    tarea = AsyncResult(task_id)
    if tarea.state == "SUCCESS":
        resultado = tarea.result if isinstance(tarea.result, dict) else {}
        if resultado.get("status") == "SUCCESS" and resultado.get("archivo"):
            return "listo", resultado
        return "error", None
    if tarea.state in ("FAILURE", "REVOKED"):
        return "error", None
    return "en_proceso", None  # PENDING, RECEIVED, STARTED, RETRY


def _tarea_del_usuario(token: str, user) -> str | None:
    task_id = leer_tarea(token, user.id)
    if task_id is None or not _ID_TAREA.match(task_id):
        logger.warning("Token de reporte asíncrono inválido o ajeno (usuario %s)", user.username)
        return None
    return task_id


_NO_ENCONTRADA = {"detail": "Tarea de reporte no encontrada."}


class EstadoReporteAsyncView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        task_id = _tarea_del_usuario(token, request.user)
        if task_id is None:
            return JsonResponse(_NO_ENCONTRADA, status=404)

        estado, resultado = _resultado(task_id)
        if estado == "listo":
            return JsonResponse(
                {
                    "estado": "listo",
                    "nombre": resultado["nombre"],
                    "vacio": bool(resultado.get("vacio")),
                    "descarga_url": f"{url_de_estado(token)}descarga/",
                }
            )
        if estado == "error":
            return JsonResponse({"estado": "error", "detail": "No se pudo generar el reporte. Intente de nuevo."})
        return JsonResponse(_EN_PROCESO)


class DescargaReporteAsyncView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        task_id = _tarea_del_usuario(token, request.user)
        if task_id is None:
            return JsonResponse(_NO_ENCONTRADA, status=404)

        estado, resultado = _resultado(task_id)
        if estado != "listo":
            return JsonResponse({"detail": "El reporte todavía no está listo.", "estado": estado}, status=409)

        # La ruta se arma solo con el id de la tarea (del token firmado), nunca con lo que
        # diga el resultado guardado en Redis.
        extension = Path(resultado["archivo"]).suffix if resultado["archivo"].endswith((".xlsx", ".csv")) else ".xlsx"
        archivo = Path(settings.REPORTES_ASYNC_DIR) / f"{task_id}{extension}"
        if not archivo.is_file():
            return JsonResponse({"detail": "El archivo ya no está disponible. Genere el reporte de nuevo."}, status=410)

        respuesta = FileResponse(
            archivo.open("rb"),
            as_attachment=True,
            filename=resultado["nombre"],
            content_type=resultado.get("content_type") or "application/octet-stream",
        )
        respuesta["X-Report-Empty"] = "true" if resultado.get("vacio") else "false"
        return respuesta
