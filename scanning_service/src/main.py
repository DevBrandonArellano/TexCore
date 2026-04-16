from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload
from .database import SessionLocal, engine
from .models import Base, LoteProduccion, StockBodega, Producto, Bodega, OrdenProduccion
import logging
import logging.handlers
import os
import time
from fastapi import Request
from src.logging_rfc5424 import RFC5424Formatter

def _setup_logging():
    formatter = RFC5424Formatter(facility=18, app_name="texcore-scanning")              
    handler = logging.StreamHandler()                                                    
    handler.setFormatter(formatter)
    handlers = [handler]                                                                 
    if os.path.exists('/dev/log'):
        syslog_h = logging.handlers.SysLogHandler(address='/dev/log')                    
        syslog_h.setFormatter(formatter)                                                 
        handlers.append(syslog_h)
    logging.root.handlers = []                                                           
    logging.basicConfig(level=logging.INFO, handlers=handlers)

_setup_logging()
logger = logging.getLogger(__name__)

# Crear las tablas si no existen (en producción esto no es necesario)
# Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TexCore Scanning Service",
    description="Microservicio de validación de códigos de barras/QR para despachos",
    version="1.0.0"
)

@app.middleware("http")
async def log_requests_rfc5424(request: Request, call_next):
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        status_code = response.status_code if response else 500
        
        request_logger = logging.getLogger("http-request")
        sd = {
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms
        }
        
        level = logging.INFO
        if status_code >= 500:
            level = logging.ERROR
        elif status_code >= 400:
            level = logging.WARNING
            
        request_logger.log(level, f"{request.method} {request.url.path} {status_code}", extra={"sd": sd})

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
        logger.info("Recibiendo solicitud de validación de lote", extra={"sd": {"code": request.code[:8]}})
        # Buscar el lote por código con eager loading de relaciones
        lote = db.query(LoteProduccion).options(
            joinedload(LoteProduccion.orden_produccion).joinedload(OrdenProduccion.producto)
        ).filter(
            LoteProduccion.codigo_lote == request.code
        ).first()
        
        if not lote:
            logger.warning("Lote no encontrado", extra={"sd": {"reason": "Lote no encontrado en el sistema"}})
            return ValidateResponse(
                valid=False,
                reason="Lote no encontrado en el sistema"
            )
        
        # Verificar que el lote tenga una orden de producción con producto
        if not lote.orden_produccion or not lote.orden_produccion.producto:
            logger.warning("Lote sin orden o producto", extra={"sd": {"reason": "Lote no tiene orden de producción o producto asociado"}})
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
            logger.warning("Lote sin stock", extra={"sd": {"reason": "Lote existe pero no tiene stock disponible (0 kg)"}})
            return ValidateResponse(
                valid=False,
                reason="Lote existe pero no tiene stock disponible (0 kg)"
            )
        
        # Obtener información del producto desde la orden de producción
        producto = lote.orden_produccion.producto
        bodega = stock.bodega
        
        logger.info("Validación exitosa", extra={"sd": {"valid": "true", "producto_id": producto.id, "bodega_id": bodega.id}})
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
        logger.error(f"Error interno", extra={"sd": {"error": str(e)}})
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
    finally:
        db.close()

