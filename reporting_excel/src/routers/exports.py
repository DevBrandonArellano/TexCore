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

@router.get("/kardex")
def export_kardex(
    bodega_id: int = Query(..., description="ID de la bodega"),
    producto_id: int = Query(..., description="ID del producto"),
    format: str = Query('xlsx', description="Formato de salida: csv o xlsx")
):
    try:
        # Llamamos al procedimiento almacenado pasando parámetros
        query = "EXEC sp_GetKardexBodega @BodegaID=?, @ProductoID=?"
        df = execute_sp_to_dataframe(query, params=(bodega_id, producto_id))
        
        return generate_download_response(df, format, f"kardex_{bodega_id}_{producto_id}")
    except Exception as e:
        logger.error(f"Error exportando Kardex: {e}")
        raise HTTPException(status_code=500, detail="Error de base de datos al obtener el Kardex")

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
