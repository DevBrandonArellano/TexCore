from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from .database import SessionLocal, engine
from .models import Base, LoteProduccion, StockBodega, Producto, Bodega, OrdenProduccion

# Crear las tablas si no existen (en producción esto no es necesario)
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TexCore Scanning Service",
    description="Microservicio de validación de códigos de barras/QR para despachos",
    version="1.0.0"
)

# Modelos Pydantic para request/response
class ValidateRequest(BaseModel):
    code: str

class LoteInfo(BaseModel):
    codigo: str
    producto_id: int
    producto_nombre: str
    peso: str
    bodega_id: int
    bodega_nombre: str

class ValidateResponse(BaseModel):
    valid: bool
    lote: LoteInfo | None = None
    reason: str | None = None

# Dependency para obtener la sesión de BD
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def read_root():
    return {
        "service": "TexCore Scanning Service",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
def health_check():
    """Endpoint de health check para monitoreo"""
    try:
        from sqlalchemy import text
        db = SessionLocal()
        # Intentar una query simple para verificar la conexión
        db.execute(text("SELECT 1"))
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.post("/validate", response_model=ValidateResponse)
def validate_lote(request: ValidateRequest):
    """
    Valida un código de lote escaneado.
    
    Verifica:
    1. Que el lote exista en el sistema
    2. Que tenga stock disponible (cantidad > 0)
    3. Retorna información del producto y bodega
    """
    db = SessionLocal()
    try:
        # Buscar el lote por código con eager loading de relaciones
        lote = db.query(LoteProduccion).options(
            joinedload(LoteProduccion.orden_produccion).joinedload(OrdenProduccion.producto)
        ).filter(
            LoteProduccion.codigo_lote == request.code
        ).first()
        
        if not lote:
            return ValidateResponse(
                valid=False,
                reason="Lote no encontrado en el sistema"
            )
        
        # Verificar que el lote tenga una orden de producción con producto
        if not lote.orden_produccion or not lote.orden_produccion.producto:
            return ValidateResponse(
                valid=False,
                reason="Lote no tiene orden de producción o producto asociado"
            )
        
        # Buscar stock disponible para este lote
        stock = db.query(StockBodega).options(
            joinedload(StockBodega.bodega)
        ).filter(
            StockBodega.lote_id == lote.id,
            StockBodega.cantidad > 0
        ).first()
        
        if not stock:
            return ValidateResponse(
                valid=False,
                reason="Lote existe pero no tiene stock disponible (0 kg)"
            )
        
        # Obtener información del producto desde la orden de producción
        producto = lote.orden_produccion.producto
        bodega = stock.bodega
        
        return ValidateResponse(
            valid=True,
            lote=LoteInfo(
                codigo=lote.codigo_lote,
                producto_id=producto.id,
                producto_nombre=producto.descripcion,
                peso=str(stock.cantidad),
                bodega_id=bodega.id,
                bodega_nombre=bodega.nombre
            )
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        db.close()

