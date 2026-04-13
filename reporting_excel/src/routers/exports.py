from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
import io
import logging

from src.database import execute_sp_to_dataframe
from src.services.excel_generator import dataframe_to_excel_bytes

router = APIRouter()
logger = logging.getLogger(__name__)

def generate_download_response(df, file_format, filename):
    if df.empty:
        raise HTTPException(status_code=404, detail="REPORT_DATA_EMPTY: No se encontraron registros para los filtros seleccionados.")
        
    if file_format == 'csv':
        csv_data = df.to_csv(index=False)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}.csv"}
        )
    else:
        excel_bytes = dataframe_to_excel_bytes(df, sheet_name="Reporte")
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}.xlsx",
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0"
            }
        )

from typing import Optional

@router.get("/kardex")
def export_kardex(
    bodega_id: int = Query(..., description="ID de la bodega"),
    producto_id: Optional[str] = Query(None, description="ID del producto (opcional para reporte general)"),
    proveedor_id: Optional[str] = Query(None, description="Filtro opcional por ID de proveedor"),
    fecha_inicio: Optional[str] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    lote_codigo: Optional[str] = Query(None, description="Filtro opcional por código de lote"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        # Usamos el SP de Kardex que ahora soporta ProductoID opcional
        # y maneja todos los filtros directamente en la base de datos.
        query = "EXEC sp_GetKardexBodega @BodegaID=?, @ProductoID=?, @FechaInicio=?, @FechaFin=?, @ProveedorID=?, @LoteCodigo=?"
        
        params = (
            bodega_id,
            int(producto_id) if (producto_id and producto_id != '0' and producto_id != '') else None,
            fecha_inicio if (fecha_inicio and fecha_inicio != '') else None,
            fecha_fin if (fecha_fin and fecha_fin != '') else None,
            int(proveedor_id) if (proveedor_id and proveedor_id != 'all' and proveedor_id != '') else None,
            lote_codigo if (lote_codigo and lote_codigo != '') else None
        )
        
        df = execute_sp_to_dataframe(query, params=params)
        
        if producto_id and producto_id != '0' and producto_id != '':
            filename = f"kardex_{bodega_id}_{producto_id}"
        else:
            filename = f"movimientos_bodega_{bodega_id}"
            
        return generate_download_response(df, format, filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Kardex: {e}")
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener el reporte")


@router.get("/productos")
def export_productos(
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        query = "EXEC sp_GetProductosCatalogo"
        df = execute_sp_to_dataframe(query)
        return generate_download_response(df, format, "catalogo_productos")
    except Exception as e:
        logger.error(f"Error exportando Productos: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/usuarios")
def export_usuarios(
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        query = "EXEC sp_GetUsuariosSistema"
        df = execute_sp_to_dataframe(query)
        return generate_download_response(df, format, "directorio_usuarios")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Usuarios: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/stock-actual")
def export_stock_actual(
    bodega_id: int = Query(...),
    producto_id: Optional[int] = Query(None),
    format: str = Query('xlsx')
):
    try:
        query = "EXEC sp_GetStockActualBodega @BodegaID=?, @SedeID=NULL, @ProductoID=?"
        df = execute_sp_to_dataframe(query, params=(bodega_id, producto_id))
        return generate_download_response(df, format, f"stock_actual_bodega_{bodega_id}")
    except Exception as e:
        logger.error(f"Error stock actual: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/valorizacion")
def export_valorizacion(
    bodega_id: int = Query(...),
    format: str = Query('xlsx')
):
    try:
        query = "EXEC sp_GetValorizacionInventario @BodegaID=?, @SedeID=NULL"
        df = execute_sp_to_dataframe(query, params=(bodega_id,))
        return generate_download_response(df, format, f"valorizacion_bodega_{bodega_id}")
    except Exception as e:
        logger.error(f"Error valorizacion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/aging")
def export_aging(
    bodega_id: int = Query(...),
    dias: int = Query(30),
    format: str = Query('xlsx')
):
    try:
        query = "EXEC sp_GetInventarioAging @BodegaID=?, @SedeID=NULL, @DiasMinimos=?"
        df = execute_sp_to_dataframe(query, params=(bodega_id, dias))
        return generate_download_response(df, format, f"aging_inventario_bodega_{bodega_id}")
    except Exception as e:
        logger.error(f"Error aging: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rotacion")
def export_rotacion(
    bodega_id: int = Query(...),
    fecha_inicio: str = Query(...),
    fecha_fin: str = Query(...),
    format: str = Query('xlsx')
):
    try:
        query = "EXEC sp_GetRotacionInventario @BodegaID=?, @FechaInicio=?, @FechaFin=?, @SedeID=NULL"
        df = execute_sp_to_dataframe(query, params=(bodega_id, fecha_inicio, fecha_fin))
        return generate_download_response(df, format, f"rotacion_bodega_{bodega_id}")
    except Exception as e:
        logger.error(f"Error rotacion: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stock-cero")
def export_stock_cero(
    bodega_id: int = Query(..., description="ID de la bodega"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    """
    Exporta todos los productos con stock = 0 o sin registro en la bodega indicada.
    Útil para identificar qué productos necesitan reposición urgente.
    """
    try:
        query = "EXEC sp_GetStockCeroBodega @BodegaID=?, @SedeID=NULL"
        df = execute_sp_to_dataframe(query, params=(bodega_id,))
        return generate_download_response(df, format, f"stock_cero_bodega_{bodega_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error stock cero: {e}")
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener el reporte")


@router.get("/resumen-movimientos")
def export_resumen_movimientos(
    bodega_id: int = Query(...),
    fecha_inicio: str = Query(...),
    fecha_fin: str = Query(...),
    format: str = Query('xlsx')
):
    try:
        query = "EXEC sp_GetResumenMovimientos @BodegaID=?, @FechaInicio=?, @FechaFin=?, @SedeID=NULL"
        df = execute_sp_to_dataframe(query, params=(bodega_id, fecha_inicio, fecha_fin))
        return generate_download_response(df, format, f"resumen_movimientos_bodega_{bodega_id}")
    except Exception as e:
        logger.error(f"Error resumen movimientos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
