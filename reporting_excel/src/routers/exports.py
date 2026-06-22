"""
Router de exportaciones generales de inventario.
SRP: solo traduce parámetros HTTP a llamadas de ReportService.
DIP: get_audit_repo crea la dependencia; el router no construye el repositorio.
ISO 27001 A.12.4: cada exportación genera un registro de auditoría persistido en SQLite.
Sin lógica de formato: delegada a ReportFactory.
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request

from src.database.repository import AuditRepository, build_report_record, get_audit_repo
from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/kardex")
async def export_kardex(
    request: Request,
    background_tasks: BackgroundTasks,
    bodega_id: int = Query(..., description="ID de la bodega"),
    producto_id: Optional[str] = Query(None),
    proveedor_id: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    lote_codigo: Optional[str] = Query(None),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        service = ReportFactory.create(format)
        query = "EXEC sp_GetKardexBodega @BodegaID=?, @ProductoID=?, @FechaInicio=?, @FechaFin=?, @ProveedorID=?, @LoteCodigo=?"
        params = (
            bodega_id,
            int(producto_id) if producto_id and producto_id not in ("0", "") else None,
            fecha_inicio or None,
            fecha_fin or None,
            int(proveedor_id) if proveedor_id and proveedor_id not in ("all", "") else None,
            lote_codigo or None,
        )
        filename = f"kardex_{bodega_id}_{producto_id}" if producto_id else f"movimientos_bodega_{bodega_id}"
        result = service.generate(query, params, filename)
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Kardex: %s", exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="kardex",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        status = 400 if error_detail and "ValueError" not in type(error_detail).__name__ else 500
        raise HTTPException(status_code=status, detail=error_detail or "Error al obtener el reporte")
    return result


@router.get("/productos")
async def export_productos(
    request: Request,
    background_tasks: BackgroundTasks,
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetProductosCatalogo", None, "catalogo_productos"
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Productos: %s", exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="productos",
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


@router.get("/usuarios")
async def export_usuarios(
    request: Request,
    background_tasks: BackgroundTasks,
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetUsuariosSistema", None, "directorio_usuarios"
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error exportando Usuarios: %s", exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="usuarios",
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


@router.get("/stock-actual")
async def export_stock_actual(
    request: Request,
    background_tasks: BackgroundTasks,
    bodega_id: int = Query(...),
    producto_id: Optional[int] = Query(None),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetStockActualBodega @BodegaID=?, @SedeID=NULL, @ProductoID=?",
            (bodega_id, producto_id),
            f"stock_actual_bodega_{bodega_id}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error stock actual: %s", exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="stock-actual",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error interno")
    return result


@router.get("/valorizacion")
async def export_valorizacion(
    request: Request,
    background_tasks: BackgroundTasks,
    bodega_id: int = Query(...),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetValorizacionInventario @BodegaID=?, @SedeID=NULL",
            (bodega_id,),
            f"valorizacion_bodega_{bodega_id}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error valorizacion: %s", exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="valorizacion",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error interno")
    return result


@router.get("/aging")
async def export_aging(
    request: Request,
    background_tasks: BackgroundTasks,
    bodega_id: int = Query(...),
    dias: int = Query(30, description="30=0-30d, 60=31-90d, 90=91-180d, 180=crítico/sin mov."),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if dias not in (30, 60, 90, 180):
        dias = 30
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetInventarioAging @BodegaID=?, @SedeID=NULL, @DiasMinimos=?",
            (bodega_id, dias),
            f"aging_inventario_bodega_{bodega_id}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error aging: %s", exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="aging",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error interno")
    return result


@router.get("/rotacion")
async def export_rotacion(
    request: Request,
    background_tasks: BackgroundTasks,
    bodega_id: int = Query(...),
    fecha_inicio: str = Query(...),
    fecha_fin: str = Query(...),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetRotacionInventario @BodegaID=?, @FechaInicio=?, @FechaFin=?, @SedeID=NULL",
            (bodega_id, fecha_inicio, fecha_fin),
            f"rotacion_bodega_{bodega_id}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error rotacion: %s", exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="rotacion",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error interno")
    return result


@router.get("/stock-cero")
async def export_stock_cero(
    request: Request,
    background_tasks: BackgroundTasks,
    bodega_id: int = Query(...),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetStockCeroBodega @BodegaID=?, @SedeID=NULL",
            (bodega_id,),
            f"stock_cero_bodega_{bodega_id}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error stock cero: %s", exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="stock-cero",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error de base de datos al obtener el reporte")
    return result


@router.get("/resumen-movimientos")
async def export_resumen_movimientos(
    request: Request,
    background_tasks: BackgroundTasks,
    bodega_id: int = Query(...),
    fecha_inicio: str = Query(...),
    fecha_fin: str = Query(...),
    format: str = Query("xlsx"),
    audit: AuditRepository = Depends(get_audit_repo),
):
    if format not in ("xlsx", "csv"):
        raise HTTPException(status_code=400, detail=f"Formato no soportado: '{format}'. Use 'xlsx' o 'csv'.")
    success, error_detail, result = True, None, None
    try:
        result = ReportFactory.create(format).generate(
            "EXEC sp_GetResumenMovimientos @BodegaID=?, @FechaInicio=?, @FechaFin=?, @SedeID=NULL",
            (bodega_id, fecha_inicio, fecha_fin),
            f"resumen_movimientos_bodega_{bodega_id}",
        )
    except ValueError as exc:
        success, error_detail = False, str(exc)
    except Exception as exc:
        success, error_detail = False, str(exc)
        logger.error("Error resumen movimientos: %s", exc)
    finally:
        record = build_report_record(
            requested_by=getattr(request.state, "caller", "unknown"),
            report_type="resumen-movimientos",
            endpoint=str(request.url.path),
            success=success,
            params_json=json.dumps(dict(request.query_params)),
            format=format,
            error_detail=error_detail,
        )
        background_tasks.add_task(audit.save, record)
    if not success:
        raise HTTPException(status_code=500, detail=error_detail or "Error interno")
    return result
