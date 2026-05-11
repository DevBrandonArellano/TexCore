"""Reportes gerenciales consolidados (todos los vendedores) para ejecutivos."""
from fastapi import APIRouter, HTTPException, Query
import logging
from datetime import date

from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger("reporting.gerencial")


@router.get("/ventas")
def export_ventas_gerencial(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
):
    try:
        logger.info("Exportando ventas gerencial", extra={"sd": {"sede_id": sede_id}})
        return ReportFactory.create(format).generate(
            "EXEC sp_GetVentasGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"ventas_gerencial_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Ventas Gerencial", extra={"sd": {"error": str(exc)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/top-clientes")
def export_top_clientes_gerencial(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
):
    try:
        logger.info("Exportando top-clientes gerencial", extra={"sd": {"sede_id": sede_id}})
        return ReportFactory.create(format).generate(
            "EXEC sp_GetTopClientesGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"top_clientes_gerencial_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Top Clientes Gerencial", extra={"sd": {"error": str(exc)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/deudores")
def export_deudores_gerencial(
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
):
    try:
        logger.info("Exportando deudores gerencial", extra={"sd": {"sede_id": sede_id}})
        return ReportFactory.create(format).generate(
            "EXEC sp_GetDeudoresGerencial @SedeID=?",
            (sede_id,),
            "clientes_deudores_gerencial",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Deudores Gerencial", extra={"sd": {"error": str(exc)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")
