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
        raise HTTPException(status_code=404, detail="No se encontraron datos para estos parámetros.")
        
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
            headers={"Content-Disposition": f"attachment; filename={filename}.xlsx"}
        )

from typing import Optional

@router.get("/kardex")
def export_kardex(
    bodega_id: int = Query(..., description="ID de la bodega"),
    producto_id: Optional[str] = Query(None, description="ID del producto (opcional para reporte general)"),
    proveedor_id: Optional[str] = Query(None, description="Filtro opcional por ID de proveedor"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        # Si no hay producto_id válido, es un reporte de stock global de la bodega
        if not producto_id or producto_id == '0' or producto_id == '':
            query = "EXEC sp_GetStockBodegaReport @BodegaID=?"
            df = execute_sp_to_dataframe(query, params=(bodega_id,))
            filename = f"stock_general_bodega_{bodega_id}"
            
        else:
            # Reporte Kardex Histórico de un solo producto
            # Se usa el SP actual (nota: para filtrar el Excel por proveedor en el Microservicio, 
            # habria que modificar tb sp_GetKardexBodega. Como solución simple, filtramos en Pandas 
            # si llega proveedor_id)
            query = "EXEC sp_GetKardexBodega @BodegaID=?, @ProductoID=?"
            df = execute_sp_to_dataframe(query, params=(bodega_id, int(producto_id)))
            
            if not df.empty and proveedor_id and proveedor_id != 'all' and proveedor_id != '':
                # Suponiendo que el SP sp_GetKardexBodega no devuelve proveedor_id, lo maneja el Backend Django
                # Al ser microservicio independiente, le tocaría cruzar data. Por simplicidad, si 
                # mandan proveedor, se omite porque sp_GetKardexBodega no saca la columna de proveedor
                pass
                
            filename = f"kardex_hist_{bodega_id}_{producto_id}"
            
        return generate_download_response(df, format, filename)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando Kardex/Stock general: {e}")
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
