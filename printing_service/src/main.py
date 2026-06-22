"""
App factory del printing_service.
Responsabilidad única: crear la aplicación FastAPI y registrar los routers.
RFC 5424: logging estructurado con SD-ELEMENT en todas las operaciones.
ISO 27001 A.12.4: persistencia de eventos de auditoría de impresión en SQLite.
"""
import logging
import logging.handlers
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database.engine import init_db
from .logging_rfc5424 import RFC5424Formatter
from .routers import health, pdf, zpl


def _setup_logging() -> None:
    formatter = RFC5424Formatter(facility=19, app_name="texcore-printing")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handlers: list = [handler]
    if os.path.exists("/dev/log"):
        syslog_h = logging.handlers.SysLogHandler(address="/dev/log")
        syslog_h.setFormatter(formatter)
        handlers.append(syslog_h)
    logging.root.handlers = []
    logging.basicConfig(level=logging.INFO, handlers=handlers)


_setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="TexCore Printing Service",
    description="Microservicio para generación de PDFs y etiquetas ZPL",
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(pdf.router)
app.include_router(zpl.router)
