"""
Reportes de Producción para descarga ejecutiva.
DIP: get_audit_repo crea la dependencia; el router no construye el repositorio.
ISO 27001 A.12.4: cada exportación genera un registro de auditoría persistido en SQLite.
COBIT MEA01: trazabilidad de reportes de producción para evaluación del desempeño.
"""
import json
import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from src.database.repository import AuditRepository, build_report_record, get_audit_repo
from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger("reporting.produccion")


@router.get("/ordenes", summary="Reporte de Órdenes de Producción")
async def export_ordenes_produccion(
    request: Request,
    background_tasks: BackgroundTasks,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        logger.info("Exportando órdenes producción", extra={"sd": {"sede_id": sede_id}})
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetOrdenesProduccionGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"ordenes_produccion_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Órdenes de Producción", extra={"sd": {"error": str(exc)}})
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="ordenes_produccion",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error interno del servidor")
    return result


@router.get("/lotes", summary="Reporte de Lotes de Producción")
async def export_lotes_produccion(
    request: Request,
    background_tasks: BackgroundTasks,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        logger.info("Exportando lotes producción", extra={"sd": {"sede_id": sede_id}})
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetLotesProduccionGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"lotes_produccion_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Lotes de Producción", extra={"sd": {"error": str(exc)}})
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="lotes_produccion",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error interno del servidor")
    return result


@router.get("/tendencia", summary="Reporte de Tendencia de Producción")
async def export_tendencia_produccion(
    request: Request,
    background_tasks: BackgroundTasks,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        logger.info("Exportando tendencia producción", extra={"sd": {"sede_id": sede_id}})
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetTendenciaProduccionGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"tendencia_produccion_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Tendencia de Producción", extra={"sd": {"error": str(exc)}})
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="tendencia_produccion",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error interno del servidor")
    return result
