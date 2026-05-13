from fastapi import APIRouter, HTTPException, Query
import logging
from datetime import date

from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger("reporting.vendedores")


@router.get("/{vendedor_id}/ventas")
def export_ventas_vendedor(
    vendedor_id: int,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    format: str = Query("xlsx"),
):
    try:
        logger.info("Exportando ventas vendedor", extra={"sd": {"vendedor_id": vendedor_id}})
        return ReportFactory.create(format).generate(
            "EXEC sp_GetVentasPorVendedor @VendedorID=?, @FechaInicio=?, @FechaFin=?",
            (vendedor_id, fecha_inicio, fecha_fin),
            f"ventas_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Ventas por Vendedor", extra={"sd": {"error": str(exc)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{vendedor_id}/top-clientes")
def export_top_clientes(
    vendedor_id: int,
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    format: str = Query("xlsx"),
):
    try:
        logger.info("Exportando top-clientes vendedor", extra={"sd": {"vendedor_id": vendedor_id}})
        return ReportFactory.create(format).generate(
            "EXEC sp_GetTopClientesPorVendedor @VendedorID=?, @FechaInicio=?, @FechaFin=?",
            (vendedor_id, fecha_inicio, fecha_fin),
            f"top_clientes_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Top Clientes", extra={"sd": {"error": str(exc)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/{vendedor_id}/deudores")
def export_deudores(
    vendedor_id: int,
    format: str = Query("xlsx"),
):
    try:
        logger.info("Exportando deudores vendedor", extra={"sd": {"vendedor_id": vendedor_id}})
        return ReportFactory.create(format).generate(
            "EXEC sp_GetDeudoresPorVendedor @VendedorID=?",
            (vendedor_id,),
            f"clientes_deudores_vendedor_{vendedor_id}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Deudores", extra={"sd": {"error": str(exc)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")
