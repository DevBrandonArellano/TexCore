from fastapi import APIRouter, HTTPException, Query
import logging
from typing import Optional
from datetime import date

from src.database import execute_sp_to_dataframe
from src.routers.exports import generate_download_response

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/{vendedor_id}/ventas")
def export_ventas_vendedor(
    vendedor_id: int,
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        query = "EXEC sp_GetVentasPorVendedor @VendedorID=?, @FechaInicio=?, @FechaFin=?"
        df = execute_sp_to_dataframe(query, params=(vendedor_id, fecha_inicio, fecha_fin))
        return generate_download_response(df, format, f"ventas_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Ventas por Vendedor: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{vendedor_id}/top-clientes")
def export_top_clientes(
    vendedor_id: int,
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        query = "EXEC sp_GetTopClientesPorVendedor @VendedorID=?, @FechaInicio=?, @FechaFin=?"
        df = execute_sp_to_dataframe(query, params=(vendedor_id, fecha_inicio, fecha_fin))
        return generate_download_response(df, format, f"top_clientes_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Top Clientes: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{vendedor_id}/deudores")
def export_deudores(
    vendedor_id: int,
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        query = "EXEC sp_GetDeudoresPorVendedor @VendedorID=?"
        df = execute_sp_to_dataframe(query, params=(vendedor_id,))
        return generate_download_response(df, format, f"clientes_deudores_vendedor_{vendedor_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Deudores: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
