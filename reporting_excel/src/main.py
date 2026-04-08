from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from fastapi import Request
from fastapi.responses import JSONResponse

# Configuración de log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _get_required_env(var_name: str) -> str:
    """Obtiene una variable de entorno requerida. Falla al arrancar si no existe (Fail-Fast)."""
    value = os.environ.get(var_name)
    if not value:
        raise RuntimeError(
            f"Variable de entorno requerida no configurada: '{var_name}'. "
            "El servicio no puede arrancar sin ella."
        )
    return value


# Fail-Fast: el servicio no arranca si no está configurada la clave interna
INTERNAL_KEY = _get_required_env("REPORTING_INTERNAL_KEY")

# Orígenes permitidos — solo red interna Docker
_raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://backend:8000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app = FastAPI(
    title="Reporting Excel Microservice",
    description="Microservicio dedicado a la generación de archivos Excel/CSV utilizando Stored Procedures de SQL Server",
    version="1.0.0"
)

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
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["X-Internal-Key"],
)

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "reporting_excel"}

from src.routers import exports, vendedores, gerencial
app.include_router(exports.router, prefix="/export", tags=["Exports"])
app.include_router(vendedores.router, prefix="/vendedores", tags=["Vendedores"])
app.include_router(gerencial.router, prefix="/gerencial", tags=["Gerencial"])
