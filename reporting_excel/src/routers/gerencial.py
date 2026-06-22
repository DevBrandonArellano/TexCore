"""
Reportes gerenciales consolidados (todos los vendedores) para ejecutivos.
DIP: get_audit_repo crea la dependencia; el router no construye el repositorio.
ISO 27001 A.12.4: cada exportación genera un registro de auditoría persistido en SQLite.
COBIT MEA01: trazabilidad de acceso a información gerencial y ejecutiva.
"""
import json
import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from src.database.repository import AuditRepository, build_report_record, get_audit_repo
from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger("reporting.gerencial")


@router.get("/ventas")
async def export_ventas_gerencial(
    request: Request,
    background_tasks: BackgroundTasks,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        logger.info("Exportando ventas gerencial", extra={"sd": {"sede_id": sede_id}})
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetVentasGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"ventas_gerencial_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Ventas Gerencial", extra={"sd": {"error": str(exc)}})
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="ventas_gerencial",
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


@router.get("/top-clientes")
async def export_top_clientes_gerencial(
    request: Request,
    background_tasks: BackgroundTasks,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        logger.info("Exportando top-clientes gerencial", extra={"sd": {"sede_id": sede_id}})
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetTopClientesGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"top_clientes_gerencial_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Top Clientes Gerencial", extra={"sd": {"error": str(exc)}})
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="top_clientes_gerencial",
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


@router.get("/deudores")
async def export_deudores_gerencial(
    request: Request,
    background_tasks: BackgroundTasks,
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        logger.info("Exportando deudores gerencial", extra={"sd": {"sede_id": sede_id}})
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetDeudoresGerencial @SedeID=?",
            (sede_id,),
            "clientes_deudores_gerencial",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Deudores Gerencial", extra={"sd": {"error": str(exc)}})
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="deudores_gerencial",
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
