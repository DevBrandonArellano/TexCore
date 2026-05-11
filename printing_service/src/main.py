"""
App factory del printing_service.
Responsabilidad única: crear la aplicación FastAPI y registrar los routers.
"""
from fastapi import FastAPI
from .routers import pdf, zpl, health

app = FastAPI(
    title="TexCore Printing Service",
    description="Microservicio para generación de PDFs y etiquetas ZPL",
    version="2.0.0",
)

app.include_router(health.router)
app.include_router(pdf.router)
app.include_router(zpl.router)
