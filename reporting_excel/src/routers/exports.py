"""
Router de exportaciones generales de inventario.
SRP: solo traduce parámetros HTTP a llamadas de ReportService.
Sin lógica de formato: delegada a ReportFactory.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/kardex")
def export_kardex(
    bodega_id: int = Query(..., description="ID de la bodega"),
    producto_id: Optional[str] = Query(None),
    proveedor_id: Optional[str] = Query(None),
    fecha_inicio: Optional[str] = Query(None),
    fecha_fin: Optional[str] = Query(None),
    lote_codigo: Optional[str] = Query(None),
    format: str = Query("xlsx"),
):
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
        return service.generate(query, params, filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Kardex: %s", exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener el reporte")


@router.get("/productos")
def export_productos(format: str = Query("xlsx")):
    try:
        return ReportFactory.create(format).generate(
            "EXEC sp_GetProductosCatalogo", None, "catalogo_productos"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Productos: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/usuarios")
def export_usuarios(format: str = Query("xlsx")):
    try:
        return ReportFactory.create(format).generate(
            "EXEC sp_GetUsuariosSistema", None, "directorio_usuarios"
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Usuarios: %s", exc)
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/stock-actual")
def export_stock_actual(
    bodega_id: int = Query(...),
    producto_id: Optional[int] = Query(None),
    format: str = Query("xlsx"),
):
    try:
        return ReportFactory.create(format).generate(
            "EXEC sp_GetStockActualBodega @BodegaID=?, @SedeID=NULL, @ProductoID=?",
            (bodega_id, producto_id),
            f"stock_actual_bodega_{bodega_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error stock actual: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/valorizacion")
def export_valorizacion(bodega_id: int = Query(...), format: str = Query("xlsx")):
    try:
        return ReportFactory.create(format).generate(
            "EXEC sp_GetValorizacionInventario @BodegaID=?, @SedeID=NULL",
            (bodega_id,),
            f"valorizacion_bodega_{bodega_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error valorizacion: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/aging")
def export_aging(
    bodega_id: int = Query(...),
    dias: int = Query(30, description="30=0-30d, 60=31-90d, 90=91-180d, 180=crítico/sin mov."),
    format: str = Query("xlsx"),
):
    if dias not in (30, 60, 90, 180):
        dias = 30
    try:
        return ReportFactory.create(format).generate(
            "EXEC sp_GetInventarioAging @BodegaID=?, @SedeID=NULL, @DiasMinimos=?",
            (bodega_id, dias),
            f"aging_inventario_bodega_{bodega_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error aging: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/rotacion")
def export_rotacion(
    bodega_id: int = Query(...),
    fecha_inicio: str = Query(...),
    fecha_fin: str = Query(...),
    format: str = Query("xlsx"),
):
    try:
        return ReportFactory.create(format).generate(
            "EXEC sp_GetRotacionInventario @BodegaID=?, @FechaInicio=?, @FechaFin=?, @SedeID=NULL",
            (bodega_id, fecha_inicio, fecha_fin),
            f"rotacion_bodega_{bodega_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error rotacion: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stock-cero")
def export_stock_cero(bodega_id: int = Query(...), format: str = Query("xlsx")):
    try:
        return ReportFactory.create(format).generate(
            "EXEC sp_GetStockCeroBodega @BodegaID=?, @SedeID=NULL",
            (bodega_id,),
            f"stock_cero_bodega_{bodega_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error stock cero: %s", exc)
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener el reporte")


@router.get("/resumen-movimientos")
def export_resumen_movimientos(
    bodega_id: int = Query(...),
    fecha_inicio: str = Query(...),
    fecha_fin: str = Query(...),
    format: str = Query("xlsx"),
):
    try:
        return ReportFactory.create(format).generate(
            "EXEC sp_GetResumenMovimientos @BodegaID=?, @FechaInicio=?, @FechaFin=?, @SedeID=NULL",
            (bodega_id, fecha_inicio, fecha_fin),
            f"resumen_movimientos_bodega_{bodega_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error resumen movimientos: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
