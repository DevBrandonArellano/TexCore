"""
App factory del scanning_service.
SRP: única responsabilidad — crear la app FastAPI, registrar middleware y routers.
Toda la lógica de negocio vive en services/. El acceso a datos en repositories/.
"""
import logging
import logging.handlers
import os
import time

from fastapi import FastAPI, Request

from .logging_rfc5424 import RFC5424Formatter
from .routers import health as health_router
from .routers import validate as validate_router


def _setup_logging() -> None:
    formatter = RFC5424Formatter(facility=18, app_name="texcore-scanning")
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
logger = logging.getLogger(__name__)

app = FastAPI(
    title="TexCore Scanning Service",
    description="Microservicio de validación de códigos de barras/QR para despachos",
    version="2.0.0",
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
            "duration_ms": duration_ms,
        }
        level = (
            logging.ERROR if status_code >= 500
            else logging.WARNING if status_code >= 400
            else logging.INFO
        )
        request_logger.log(
            level,
            f"{request.method} {request.url.path} {status_code}",
            extra={"sd": sd},
        )


@app.get("/", include_in_schema=False)
def read_root():
    return {"service": "TexCore Scanning Service", "status": "running", "version": "2.0.0"}


app.include_router(health_router.router)
app.include_router(validate_router.router)
