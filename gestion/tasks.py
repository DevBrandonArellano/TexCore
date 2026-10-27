import logging
import os
import re
import time
import uuid
from pathlib import Path

import httpx
from celery import shared_task
from django.conf import settings

from internal_api.authentication import JWTServiceAuthentication

logger = logging.getLogger("gestion.tasks")

_NOMBRE_EN_DISPOSITION = re.compile(r'filename="?([^";]+)"?')


def _limpiar_vencidos(directorio: Path) -> None:
    """Borra los archivos más viejos que REPORTES_ASYNC_TTL_SEGUNDOS (no hace falta Celery Beat)."""
    limite = time.time() - settings.REPORTES_ASYNC_TTL_SEGUNDOS
    for archivo in directorio.iterdir():
        try:
            if archivo.is_file() and archivo.stat().st_mtime < limite:
                archivo.unlink()
        except FileNotFoundError:  # otro worker lo borró primero
            pass


def _guardar_archivo(task_id: str, report_format: str, filename: str, response) -> dict:
    """Escribe el archivo generado en el directorio compartido con el backend y describe la descarga."""
    directorio = Path(settings.REPORTES_ASYNC_DIR)
    directorio.mkdir(parents=True, exist_ok=True)
    _limpiar_vencidos(directorio)

    extension = "csv" if report_format == "csv" else "xlsx"
    archivo = directorio / f"{task_id}.{extension}"
    temporal = archivo.with_suffix(".tmp")
    temporal.write_bytes(response.content)
    temporal.replace(archivo)  # atómico: el backend nunca ve un archivo a medias

    coincidencia = _NOMBRE_EN_DISPOSITION.search(response.headers.get("Content-Disposition", ""))
    return {
        "archivo": archivo.name,
        "nombre": coincidencia.group(1) if coincidencia else f"{filename}.{extension}",
        "content_type": response.headers.get("Content-Type", "application/octet-stream"),
        "vacio": response.headers.get("X-Report-Empty") == "true",
    }


@shared_task(bind=True, max_retries=3)
def async_export_report(self, report_path: str, params: dict, user_id: int, report_format: str = "xlsx"):
    """
    Tarea asíncrona para generar reportes pesados sin bloquear a Gunicorn.

    El archivo queda en REPORTES_ASYNC_DIR con el id de la tarea como nombre; el
    backend lo entrega en /api/reporting/tareas/<token>/descarga/
    (inventory/reportes_async.py).

    Igual que el proxy síncrono (inventory/reporting_proxy.py, ver auditoría de
    performance 2026-08-31): consulta los datos EN PROCESO vía
    internal_api/services/report_dispatch.py (el worker de Celery carga el
    mismo proyecto Django, así que tiene el ORM disponible) y solo le pide a
    reporting_excel que formatee el archivo — sin el salto redundante que
    volvía a llamar al backend por HTTP.
    """
    from internal_api.services.report_dispatch import resolve_report
    from inventory.reporting_proxy import _json_safe

    logger.info(
        "Iniciando generación asíncrona de reporte: %s para user_id: %s",
        report_path,
        user_id,
    )
    try:
        rows, filename = resolve_report(report_path.lstrip("/"), params)
    except Exception as exc:
        logger.exception("Error consultando datos para el reporte asíncrono %s: %s", report_path, exc)
        return {"status": "FAILURE", "report_path": report_path, "user_id": user_id}

    service_url = os.getenv("REPORTING_SERVICE_URL", "http://reporting_excel:8002")
    service_token = JWTServiceAuthentication.generate_token(
        service_name="backend-proxy",
        scopes=["reports:read"],
    )
    headers = {"Authorization": f"Bearer {service_token}"}
    body = {
        "format": report_format,
        "filename": filename,
        "report_type": report_path.lstrip("/").replace("/", "_"),
        "rows": _json_safe(rows),
    }

    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(f"{service_url}/generate", json=body, headers=headers)

            if response.status_code == 200:
                descarga = _guardar_archivo(self.request.id or str(uuid.uuid4()), report_format, filename, response)
                logger.info("Reporte %s generado exitosamente en background.", report_path)
                return {"status": "SUCCESS", "report_path": report_path, "user_id": user_id, **descarga}
            logger.error(
                "Fallo en generación de reporte %s: HTTP %s",
                report_path,
                response.status_code,
            )
            self.retry(countdown=60)
    except httpx.RequestError as exc:
        logger.exception("Error de conexión asíncrona con reporting_excel: %s", exc)
        self.retry(exc=exc, countdown=60)
