"""Reportes gerenciales consolidados (todos los vendedores) para ejecutivos."""

from fastapi import APIRouter, HTTPException, Query
import logging
from datetime import date

from src.database import execute_sp_to_dataframe
from src.routers.exports import generate_download_response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/ventas")
def export_ventas_gerencial(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    sede_id: int = Query(None, description="ID de sede opcional"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        query = "EXEC sp_GetVentasGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?"
        df = execute_sp_to_dataframe(query, params=(fecha_inicio, fecha_fin, sede_id))
        return generate_download_response(
            df, format, f"ventas_gerencial_{fecha_inicio}_{fecha_fin}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Ventas Gerencial: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/top-clientes")
def export_top_clientes_gerencial(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    sede_id: int = Query(None, description="ID de sede opcional"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        query = "EXEC sp_GetTopClientesGerencial @FechaInicio=?, @FechaFin=?, @SedeID=?"
        df = execute_sp_to_dataframe(query, params=(fecha_inicio, fecha_fin, sede_id))
        return generate_download_response(
            df, format, f"top_clientes_gerencial_{fecha_inicio}_{fecha_fin}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Top Clientes Gerencial: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/deudores")
def export_deudores_gerencial(
    sede_id: int = Query(None, description="ID de sede opcional"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        query = "EXEC sp_GetDeudoresGerencial @SedeID=?"
        df = execute_sp_to_dataframe(query, params=(sede_id,))
        return generate_download_response(df, format, "clientes_deudores_gerencial")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Deudores Gerencial: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
