"""Reportes de Producción para descarga ejecutiva."""
from fastapi import APIRouter, HTTPException, Query
import logging
from datetime import date

from src.services.report_factory import ReportFactory

router = APIRouter()
logger = logging.getLogger("reporting.produccion")


@router.get("/ordenes", summary="Reporte de Órdenes de Producción")
def export_ordenes_produccion(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
):
    try:
        logger.info("Exportando órdenes producción", extra={"sd": {"sede_id": sede_id}})
        return ReportFactory.create(format).generate(
            "EXEC sp_GetOrdenesProduccionGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"ordenes_produccion_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Órdenes de Producción", extra={"sd": {"error": str(exc)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/lotes", summary="Reporte de Lotes de Producción")
def export_lotes_produccion(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
):
    try:
        logger.info("Exportando lotes producción", extra={"sd": {"sede_id": sede_id}})
        return ReportFactory.create(format).generate(
            "EXEC sp_GetLotesProduccionGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"lotes_produccion_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Lotes de Producción", extra={"sd": {"error": str(exc)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/tendencia", summary="Reporte de Tendencia de Producción")
def export_tendencia_produccion(
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    sede_id: int = Query(None),
    format: str = Query("xlsx"),
):
    try:
        logger.info("Exportando tendencia producción", extra={"sd": {"sede_id": sede_id}})
        return ReportFactory.create(format).generate(
            "EXEC sp_GetTendenciaProduccionGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?",
            (fecha_inicio, fecha_fin, sede_id),
            f"tendencia_produccion_{fecha_inicio}_{fecha_fin}",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error("Error exportando Tendencia de Producción", extra={"sd": {"error": str(exc)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")
