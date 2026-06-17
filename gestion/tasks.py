import logging
import os

import httpx
from celery import shared_task

from internal_api.authentication import JWTServiceAuthentication

logger = logging.getLogger('gestion.tasks')


@shared_task(bind=True, max_retries=3)
def async_export_report(self, report_path: str, params: dict, user_id: int):
    """
    Tarea asíncrona para generar reportes pesados sin bloquear a Gunicorn.
    Llama al microservicio reporting_excel con JWT RS256 (igual que el proxy síncrono).
    """
    logger.info(
        "Iniciando generación asíncrona de reporte: %s para user_id: %s",
        report_path, user_id,
    )
    service_url = os.getenv("REPORTING_SERVICE_URL", "http://reporting_excel:8002")
    service_token = JWTServiceAuthentication.generate_token(
        service_name="backend-proxy",
        scopes=["reports:read"],
    )

    target_url = f"{service_url}/{report_path.lstrip('/')}"
    headers = {"Authorization": f"Bearer {service_token}"}

    try:
        with httpx.Client(timeout=300.0) as client:
            response = client.get(target_url, params=params, headers=headers)

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
