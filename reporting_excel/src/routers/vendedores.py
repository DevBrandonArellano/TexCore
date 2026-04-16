from fastapi import APIRouter, HTTPException, Query
import logging
from typing import Optional
from datetime import date

from src.database import execute_sp_to_dataframe
from src.routers.exports import generate_download_response

router = APIRouter()
logger = logging.getLogger("reporting.vendedores")

@router.get("/{vendedor_id}/ventas")
def export_ventas_vendedor(
    vendedor_id: int,
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        logger.info("Iniciando exportación ventas vendedor", extra={"sd": {"reporte": "ventas_vendedor", "vendedor_id": vendedor_id, "fecha_inicio": str(fecha_inicio), "fecha_fin": str(fecha_fin)}})
        query = "EXEC sp_GetVentasPorVendedor @VendedorID=?, @FechaInicio=?, @FechaFin=?"
        df = execute_sp_to_dataframe(query, params=(vendedor_id, fecha_inicio, fecha_fin))
        logger.info("Terminando exportación ventas vendedor con éxito", extra={"sd": {"reporte": "ventas_vendedor", "filas_generadas": len(df)}})
        return generate_download_response(df, format, f"ventas_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Ventas por Vendedor", extra={"sd": {"reporte": "ventas_vendedor", "error": str(e)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{vendedor_id}/top-clientes")
def export_top_clientes(
    vendedor_id: int,
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        logger.info("Iniciando exportación top-clientes vendedor", extra={"sd": {"reporte": "top_clientes_vendedor", "vendedor_id": vendedor_id, "fecha_inicio": str(fecha_inicio), "fecha_fin": str(fecha_fin)}})
        query = "EXEC sp_GetTopClientesPorVendedor @VendedorID=?, @FechaInicio=?, @FechaFin=?"
        df = execute_sp_to_dataframe(query, params=(vendedor_id, fecha_inicio, fecha_fin))
        logger.info("Terminando exportación top-clientes vendedor con éxito", extra={"sd": {"reporte": "top_clientes_vendedor", "filas_generadas": len(df)}})
        return generate_download_response(df, format, f"top_clientes_vendedor_{vendedor_id}_{fecha_inicio}_{fecha_fin}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Top Clientes", extra={"sd": {"reporte": "top_clientes_vendedor", "error": str(e)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/{vendedor_id}/deudores")
def export_deudores(
    vendedor_id: int,
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        logger.info("Iniciando exportación deudores vendedor", extra={"sd": {"reporte": "deudores_vendedor", "vendedor_id": vendedor_id}})
        query = "EXEC sp_GetDeudoresPorVendedor @VendedorID=?"
        df = execute_sp_to_dataframe(query, params=(vendedor_id,))
        logger.info("Terminando exportación deudores vendedor con éxito", extra={"sd": {"reporte": "deudores_vendedor", "filas_generadas": len(df)}})
        return generate_download_response(df, format, f"clientes_deudores_vendedor_{vendedor_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Deudores", extra={"sd": {"reporte": "deudores_vendedor", "error": str(e)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")
