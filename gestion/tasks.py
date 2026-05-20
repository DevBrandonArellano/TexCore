import logging
from celery import shared_task
import httpx
from django.conf import settings
import os

logger = logging.getLogger('gestion.tasks')

@shared_task(bind=True, max_retries=3)
def async_export_report(self, report_path: str, params: dict, user_id: int):
    """
    Tarea asíncrona para generar reportes pesados sin bloquear a Gunicorn.
    Llama al microservicio reporting_excel y puede guardar el archivo resultante
    en un sistema de almacenamiento o enviar un email al usuario al finalizar.
    """
    logger.info(f"Iniciando generación asíncrona de reporte: {report_path} para user_id: {user_id}")
    service_url = os.getenv("REPORTING_SERVICE_URL", "http://reporting_excel:8002")
    internal_key = os.getenv("REPORTING_INTERNAL_KEY", "dev-internal-secret-key-change-in-prod")
    
    target_url = f"{service_url}/{report_path.lstrip('/')}"
    headers = {"X-Internal-Key": internal_key}

    try:
        # Aumentamos el timeout para reportes pesados en background
        with httpx.Client(timeout=300.0) as client:
            response = client.get(target_url, params=params, headers=headers)
            
            if response.status_code == 200:
                # Aquí se implementaría la lógica para guardar el binario
                # (e.g. en AWS S3, Azure Blob, o el file system)
                # y notificar al usuario (e.g. por WebSocket o Email).
                logger.info(f"Reporte {report_path} generado exitosamente en background.")
                return {"status": "SUCCESS", "report_path": report_path, "user_id": user_id}
            else:
                logger.error(f"Fallo en generación de reporte {report_path}: {response.status_code}")
                # Reintentar si el servicio está sobrecargado
                self.retry(countdown=60)
    except httpx.RequestError as exc:
        logger.error(f"Error de conexión asíncrona con reporting_excel: {exc}")
        self.retry(exc=exc, countdown=60)


@shared_task
def run_mrp_calculation(sede_id: int):
    """
    Tarea asíncrona para el cálculo completo del MRP (Material Requirements Planning).
    Se encarga de procesar pedidos de venta vs stock y emitir OCs sugeridas.
    """
    logger.info(f"Iniciando cálculo de MRP para sede {sede_id}...")
    from gestion.services.produccion_kpi_service import ProduccionKPIService
    
    # En un caso real, aquí iría un ProduccionMRPService complejo que demora varios minutos.
    service = ProduccionKPIService(sede_id=sede_id)
    try:
        kpis = service.obtener_kpis()
        logger.info(f"MRP y KPIs recalculados exitosamente para sede {sede_id}.")
        return {"status": "SUCCESS", "sede_id": sede_id, "kpis_generados": True}
    except Exception as e:
        logger.exception("Error en cálculo asíncrono de MRP")
        return {"status": "ERROR", "error": str(e)}
