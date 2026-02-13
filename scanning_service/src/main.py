from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import SessionLocal, engine
from .models import Base, LoteProduccion, StockBodega, Producto, Bodega

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
        db = SessionLocal()
        # Intentar una query simple para verificar la conexión
        db.execute("SELECT 1")
        db.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.post("/scanning/validate", response_model=ValidateResponse)
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
        # Buscar el lote por código
        lote = db.query(LoteProduccion).filter(
            LoteProduccion.codigo_lote == request.code
        ).first()
        
        if not lote:
            return ValidateResponse(
                valid=False,
                reason="Lote no encontrado en el sistema"
            )
        
        # Buscar stock disponible para este lote
        stock = db.query(StockBodega).filter(
            StockBodega.lote_id == lote.id,
            StockBodega.cantidad > 0
        ).first()
        
        if not stock:
            return ValidateResponse(
                valid=False,
                reason="Lote existe pero no tiene stock disponible (0 kg)"
            )
        
        # Obtener información del producto y bodega
        producto = db.query(Producto).filter(Producto.id == lote.producto_id).first()
        bodega = db.query(Bodega).filter(Bodega.id == stock.bodega_id).first()
        
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
