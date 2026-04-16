"""Reportes gerenciales consolidados (todos los vendedores) para ejecutivos."""

from fastapi import APIRouter, HTTPException, Query
import logging
from datetime import date

from src.database import execute_sp_to_dataframe
from src.routers.exports import generate_download_response

router = APIRouter()
logger = logging.getLogger("reporting.gerencial")


@router.get("/ventas")
def export_ventas_gerencial(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    sede_id: int = Query(None, description="ID de sede opcional"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        logger.info("Iniciando exportación ventas", extra={"sd": {"reporte": "ventas_gerencial", "sede_id": sede_id, "fecha_inicio": str(fecha_inicio), "fecha_fin": str(fecha_fin)}})
        query = "EXEC sp_GetVentasGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?"
        df = execute_sp_to_dataframe(query, params=(fecha_inicio, fecha_fin, sede_id))
        logger.info("Terminando exportación ventas con éxito", extra={"sd": {"reporte": "ventas_gerencial", "filas_generadas": len(df)}})
        return generate_download_response(
            df, format, f"ventas_gerencial_{fecha_inicio}_{fecha_fin}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Ventas Gerencial", extra={"sd": {"reporte": "ventas_gerencial", "error": str(e)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/top-clientes")
def export_top_clientes_gerencial(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    sede_id: int = Query(None, description="ID de sede opcional"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        logger.info("Iniciando exportación top-clientes", extra={"sd": {"reporte": "top_clientes_gerencial", "sede_id": sede_id, "fecha_inicio": str(fecha_inicio), "fecha_fin": str(fecha_fin)}})
        query = "EXEC sp_GetTopClientesGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?"
        df = execute_sp_to_dataframe(query, params=(fecha_inicio, fecha_fin, sede_id))
        logger.info("Terminando exportación top-clientes con éxito", extra={"sd": {"reporte": "top_clientes_gerencial", "filas_generadas": len(df)}})
        return generate_download_response(
            df, format, f"top_clientes_gerencial_{fecha_inicio}_{fecha_fin}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Top Clientes Gerencial", extra={"sd": {"reporte": "top_clientes_gerencial", "error": str(e)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/deudores")
def export_deudores_gerencial(
    sede_id: int = Query(None, description="ID de sede opcional"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        logger.info("Iniciando exportación deudores", extra={"sd": {"reporte": "deudores_gerencial", "sede_id": sede_id}})
        query = "EXEC sp_GetDeudoresGerencial @SedeID=?"
        df = execute_sp_to_dataframe(query, params=(sede_id,))
        logger.info("Terminando exportación deudores con éxito", extra={"sd": {"reporte": "deudores_gerencial", "filas_generadas": len(df)}})
        return generate_download_response(df, format, "clientes_deudores_gerencial")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Deudores Gerencial", extra={"sd": {"reporte": "deudores_gerencial", "error": str(e)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")
