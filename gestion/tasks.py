import logging
import os

import httpx
from celery import shared_task

from internal_api.authentication import JWTServiceAuthentication

logger = logging.getLogger('gestion.tasks')


@shared_task(bind=True, max_retries=3)
def async_export_report(self, report_path: str, params: dict, user_id: int, report_format: str = "xlsx"):
    """
    Tarea asíncrona para generar reportes pesados sin bloquear a Gunicorn.

    Igual que el proxy síncrono (inventory/reporting_proxy.py, ver auditoría de
    performance 2026-08-31): consulta los datos EN PROCESO vía
    internal_api/services/report_dispatch.py (el worker de Celery carga el
    mismo proyecto Django, así que tiene el ORM disponible) y solo le pide a
    reporting_excel que formatee el archivo — sin el salto redundante que
    volvía a llamar al backend por HTTP.
    """
    from inventory.reporting_proxy import _json_safe
    from internal_api.services.report_dispatch import resolve_report

    logger.info(
        "Iniciando generación asíncrona de reporte: %s para user_id: %s",
        report_path, user_id,
    )
    try:
        rows, filename = resolve_report(report_path.lstrip('/'), params)
    except Exception as exc:
        logger.error("Error consultando datos para el reporte asíncrono %s: %s", report_path, exc)
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
        "report_type": report_path.lstrip('/').replace("/", "_"),
        "rows": _json_safe(rows),
    }

    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.post(f"{service_url}/generate", json=body, headers=headers)

            if response.status_code == 200:
                logger.info("Reporte %s generado exitosamente en background.", report_path)
                return {"status": "SUCCESS", "report_path": report_path, "user_id": user_id}
            else:
                logger.error(
                    "Fallo en generación de reporte %s: HTTP %s",
                    report_path, response.status_code,
                )
                self.retry(countdown=60)
    except httpx.RequestError as exc:
        logger.error("Error de conexión asíncrona con reporting_excel: %s", exc)
        self.retry(exc=exc, countdown=60)


@shared_task
def run_mrp_calculation(sede_id: int):
    """
    Tarea asíncrona para el cálculo completo del MRP (Material Requirements Planning).
    """
    logger.info("Iniciando cálculo de MRP para sede %s...", sede_id)
    from gestion.services.produccion_kpi_service import ProduccionKPIService

    service = ProduccionKPIService(sede_id=sede_id)
    try:
        service.obtener_kpis()
        logger.info("MRP y KPIs recalculados exitosamente para sede %s.", sede_id)
        return {"status": "SUCCESS", "sede_id": sede_id, "kpis_generados": True}
    except Exception as e:
        logger.exception("Error en cálculo asíncrono de MRP")
        return {"status": "ERROR", "error": str(e)}
