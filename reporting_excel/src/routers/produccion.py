"""
RUP - Router: Reportes de Producción
=====================================
Artefacto   : Diseño de Componentes — Microservicio reporting_excel
Módulo      : Producción / Reportes Excel Ejecutivos
Patrón      : Strategy (reutiliza generate_download_response para diferentes formatos)
              Chain of Responsibility (FastAPI middleware → router → SP)

Responsabilidad: Generar reportes Excel/CSV de producción para descarga ejecutiva.
Solo se comunica con SQL Server vía Stored Procedures. Sin lógica de negocio.
"""

from fastapi import APIRouter, HTTPException, Query
import logging
from datetime import date

from src.database import execute_sp_to_dataframe
from src.routers.exports import generate_download_response

router = APIRouter()
logger = logging.getLogger("reporting.produccion")


@router.get(
    "/ordenes",
    summary="Reporte de Órdenes de Producción",
    description="Exporta el detalle de órdenes de producción filtradas por fecha y sede.",
)
def export_ordenes_produccion(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    sede_id: int = Query(None, description="ID de sede (opcional — None = todas)"),
    format: str = Query("xlsx", description="Formato de salida: csv o xlsx"),
):
    """
    SP esperado: sp_GetOrdenesProduccionGerencial
    Parámetros : @FechaInicio, @FechaFin, @SedeID (nullable)
    Retorna    : codigo, producto, formula_color, peso_requerido, peso_producido,
                 estado, sede, area, maquina, operario, fecha_inicio, fecha_fin
    """
    try:
        logger.info("Iniciando exportación órdenes", extra={"sd": {"reporte": "ordenes_produccion", "sede_id": sede_id, "fecha_inicio": str(fecha_inicio), "fecha_fin": str(fecha_fin)}})
        query = (
            "EXEC sp_GetOrdenesProduccionGerencial "
            "@FechaInicio=?, @FechaFin=?, @SedeID=?"
        )
        df = execute_sp_to_dataframe(query, params=(fecha_inicio, fecha_fin, sede_id))
        logger.info("Terminando exportación órdenes con éxito", extra={"sd": {"reporte": "ordenes_produccion", "filas_generadas": len(df)}})
        return generate_download_response(
            df, format, f"ordenes_produccion_{fecha_inicio}_{fecha_fin}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exportando Órdenes de Producción", extra={"sd": {"reporte": "ordenes_produccion", "error": str(e)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/lotes",
    summary="Reporte de Lotes de Producción",
    description="Exporta lotes producidos con pesos, tiempos y operarios.",
)
def export_lotes_produccion(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    sede_id: int = Query(None, description="ID de sede (opcional)"),
    format: str = Query("xlsx", description="Formato de salida: csv o xlsx"),
):
    """
    SP esperado: sp_GetLotesProduccionGerencial
    Parámetros : @FechaInicio, @FechaFin, @SedeID (nullable)
    Retorna    : codigo_lote, orden_produccion, producto, peso_bruto, tara,
                 peso_neto_producido, operario, maquina, turno, hora_inicio,
                 hora_final, duracion_min, sede
    """
    try:
        logger.info("Iniciando exportación lotes", extra={"sd": {"reporte": "lotes_produccion", "sede_id": sede_id, "fecha_inicio": str(fecha_inicio), "fecha_fin": str(fecha_fin)}})
        query = (
            "EXEC sp_GetLotesProduccionGerencial "
            "@FechaInicio=?, @FechaFin=?, @SedeID=?"
        )
        df = execute_sp_to_dataframe(query, params=(fecha_inicio, fecha_fin, sede_id))
        logger.info("Terminando exportación lotes con éxito", extra={"sd": {"reporte": "lotes_produccion", "filas_generadas": len(df)}})
        return generate_download_response(
            df, format, f"lotes_produccion_{fecha_inicio}_{fecha_fin}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exportando Lotes de Producción", extra={"sd": {"reporte": "lotes_produccion", "error": str(e)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get(
    "/tendencia",
    summary="Reporte de Tendencia de Producción",
    description="Exporta kg producidos por día en el rango indicado.",
)
def export_tendencia_produccion(
    fecha_inicio: date = Query(..., description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: date = Query(..., description="Fecha de fin (YYYY-MM-DD)"),
    sede_id: int = Query(None, description="ID de sede (opcional)"),
    format: str = Query("xlsx", description="Formato de salida: csv o xlsx"),
):
    """
    SP esperado: sp_GetTendenciaProduccionGerencial
    Parámetros : @FechaInicio, @FechaFin, @SedeID (nullable)
    Retorna    : fecha, kg_producidos, sede
    """
    try:
        logger.info("Iniciando exportación tendencia", extra={"sd": {"reporte": "tendencia_produccion", "sede_id": sede_id, "fecha_inicio": str(fecha_inicio), "fecha_fin": str(fecha_fin)}})
        query = (
            "EXEC sp_GetTendenciaProduccionGerencial "
            "@FechaInicio=?, @FechaFin=?, @SedeID=?"
        )
        df = execute_sp_to_dataframe(query, params=(fecha_inicio, fecha_fin, sede_id))
        logger.info("Terminando exportación tendencia con éxito", extra={"sd": {"reporte": "tendencia_produccion", "filas_generadas": len(df)}})
        return generate_download_response(
            df, format, f"tendencia_produccion_{fecha_inicio}_{fecha_fin}"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error exportando Tendencia de Producción", extra={"sd": {"reporte": "tendencia_produccion", "error": str(e)}})
        raise HTTPException(status_code=500, detail="Error interno del servidor")
