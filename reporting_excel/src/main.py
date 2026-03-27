from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Configuración de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Reporting Excel Microservice",
    description="Microservicio dedicado a la generación de archivos Excel/CSV utilizando Stored Procedures de SQL Server",
    version="1.0.0"
)

import os
from fastapi import Request
from fastapi.responses import JSONResponse

INTERNAL_KEY = os.getenv("REPORTING_INTERNAL_KEY", "dev-internal-secret-key-change-in-prod")

@app.middleware("http")
async def verify_internal_key(request: Request, call_next):
    # Excluir health check
    if request.url.path == "/health":
        return await call_next(request)
    
    # Verificar header
    key = request.headers.get("X-Internal-Key", "")
    if not INTERNAL_KEY or key != INTERNAL_KEY:
        return JSONResponse(status_code=403, content={"detail": "Acceso no autorizado - Se requiere X-Internal-Key correcta"})
    
    return await call_next(request)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "reporting_excel"}

from src.routers import exports, vendedores, gerencial
app.include_router(exports.router, prefix="/export", tags=["Exports"])
app.include_router(vendedores.router, prefix="/vendedores", tags=["Vendedores"])
app.include_router(gerencial.router, prefix="/gerencial", tags=["Gerencial"])
