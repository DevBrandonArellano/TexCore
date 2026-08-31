"""
Endpoint genérico de generación de reportes.

Reemplaza, para el tráfico real del backend, a los routers por-reporte
(exports.py, gerencial.py, produccion.py, vendedores.py): el backend Django
(inventory/reporting_proxy.py) ya consulta sus propios datos en proceso (sin
red) y solo necesita que este servicio formatee esos datos a Excel/CSV — no
que vuelva a pedírselos por HTTP. Esto elimina el salto redundante
backend->reporting_excel->backend identificado en la auditoría de
performance 2026-08-31 (timeout interno de 30s, primer punto de falla bajo
alta concurrencia).

Los routers por-reporte se mantienen (no se eliminaron) por compatibilidad
con sus tests existentes, pero ya no los usa el flujo de producción.
"""
import json
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Depends
from pydantic import BaseModel

from src.database.repository import AuditRepository, build_report_record, get_audit_repo
from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger("reporting.generate")


class GenerateRequest(BaseModel):
    format: str = "xlsx"
    filename: str
    report_type: str
    rows: list[dict[str, Any]] = []


@router.post("/generate")
async def generate_report(
    body: GenerateRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    audit: AuditRepository = Depends(get_audit_repo),
):
    if body.format not in ("xlsx", "csv"):
        raise HTTPException(
            status_code=400,
            detail=f"Formato no soportado: '{body.format}'. Use 'xlsx' o 'csv'.",
        )
    success, error_detail, result = True, None, None
    try:
        service = ReportFactory.create(body.format)
        result = await service.generate_from_rows(body.rows, body.filename)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error generando reporte '%s': %s", body.report_type, exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type=body.report_type,
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps({"report_type": body.report_type, "rows": len(body.rows)}),
            format=body.format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error interno del servidor")
    return result
