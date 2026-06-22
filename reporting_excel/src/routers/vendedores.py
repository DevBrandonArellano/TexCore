"""
Router de reportes por vendedor.
DIP: get_audit_repo crea la dependencia; el router no construye el repositorio.
ISO 27001 A.12.4: cada exportación genera un registro de auditoría persistido en SQLite.
"""
import json
import logging
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from src.database.repository import AuditRepository, build_report_record, get_audit_repo
from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger("reporting.vendedores")


@router.get("/{vendedor_id}/ventas")
async def export_ventas_vendedor(
    request: Request,
    background_tasks: BackgroundTasks,
    vendedor_id: int,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        logger.info("Exportando ventas vendedor", extra={"sd": {"vendedor_id": vendedor_id}})
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetVentasPorVendedor @VendedorID=?, @FechaInicio=?, @FechaFin=?",
            (vendedor_id, fecha_inicio, fecha_fin),
            f"ventas_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Ventas por Vendedor", extra={"sd": {"error": str(exc)}})
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="ventas_vendedor",
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


@router.get("/{vendedor_id}/top-clientes")
async def export_top_clientes(
    request: Request,
    background_tasks: BackgroundTasks,
    vendedor_id: int,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        logger.info("Exportando top-clientes vendedor", extra={"sd": {"vendedor_id": vendedor_id}})
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetTopClientesPorVendedor @VendedorID=?, @FechaInicio=?, @FechaFin=?",
            (vendedor_id, fecha_inicio, fecha_fin),
            f"top_clientes_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Top Clientes", extra={"sd": {"error": str(exc)}})
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="top_clientes_vendedor",
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


@router.get("/{vendedor_id}/deudores")
async def export_deudores(
    request: Request,
    background_tasks: BackgroundTasks,
    vendedor_id: int,
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    success, error_detail, result = True, None, None
    try:
        logger.info("Exportando deudores vendedor", extra={"sd": {"vendedor_id": vendedor_id}})
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetDeudoresPorVendedor @VendedorID=?",
            (vendedor_id,),
            f"clientes_deudores_vendedor_{vendedor_id}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Deudores", extra={"sd": {"error": str(exc)}})
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="deudores_vendedor",
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
