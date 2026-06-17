"""
App factory del scanning_service — versión independiente (v3.0).
Toda la configuración de BD fue reemplazada por JWT + Django Internal API.
SRP: crea la app FastAPI, singletons y registra middleware/routers.
"""
import logging
import logging.handlers
import os
import time

from fastapi import FastAPI, Request

from .logging_rfc5424 import RFC5424Formatter
from .routers import health as health_router
from .routers import validate as validate_router
from .infrastructure.jwt_token_manager import JWTTokenManager
from .infrastructure.django_client import DjangoApiClient


def _get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Variable de entorno requerida no configurada: '{name}'"
        )
    return value


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

# Fail-Fast: el servicio no arranca sin estas variables
DJANGO_INTERNAL_URL = _get_required_env("DJANGO_INTERNAL_URL")
SERVICE_NAME = _get_required_env("SERVICE_NAME")
SERVICE_SECRET = _get_required_env("SERVICE_SECRET")
INTERNAL_JWT_PUBLIC_KEY = _get_required_env("INTERNAL_JWT_PUBLIC_KEY").replace("\\n", "\n")

# Singleton: token manager y cliente Django
token_manager = JWTTokenManager(
    django_url=DJANGO_INTERNAL_URL,
    service_name=SERVICE_NAME,
    service_secret=SERVICE_SECRET,
    public_key=INTERNAL_JWT_PUBLIC_KEY,
)
django_client = DjangoApiClient(
    token_manager=token_manager,
    base_url=DJANGO_INTERNAL_URL,
)

app = FastAPI(
    title="TexCore Scanning Service",
    description="Microservicio de validación de lotes — independiente de BD",
    version="3.0.0",
)
app.state.django_client = django_client


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
        level = (
            logging.ERROR
            if status_code >= 500
            else logging.WARNING
            if status_code >= 400
            else logging.INFO
        )
        logging.getLogger("http-request").log(
            level,
            f"{request.method} {request.url.path} {status_code}",
            extra={
                "sd": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                }
            },
        )


@app.get("/", include_in_schema=False)
def read_root():
    return {
        "service": "TexCore Scanning Service",
        "status": "running",
        "version": "3.0.0",
    }


app.include_router(health_router.router)
app.include_router(validate_router.router)
