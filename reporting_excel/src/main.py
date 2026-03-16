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
