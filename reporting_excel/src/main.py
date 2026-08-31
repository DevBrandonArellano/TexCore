"""
App factory del reporting_excel — versión independiente (v2.0).
Autenticación: JWT Bearer RS256 (reemplaza X-Internal-Key).
ISO 27001: sin credenciales de BD, audit trail por cada reporte.

Nota (auditoría de performance 2026-08-31): este servicio ya NO llama de
vuelta a Django — el backend (inventory/reporting_proxy.py) consulta sus
propios datos en proceso y solo le pide a /generate que formatee el
archivo. Por eso ya no hay aquí un cliente HTTP saliente ni un token
manager propio (se eliminaron DjangoReportRepository/JWTTokenManager y los
routers por-reporte que dependían de ellos).
"""
import logging
import logging.handlers
import os
import time

from contextlib import asynccontextmanager

import httpx
import jwt
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.database.engine import init_db
from src.logging_rfc5424 import RFC5424Formatter


def _get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Variable de entorno requerida no configurada: '{name}'"
        )
    return value


def _setup_logging() -> None:
    formatter = RFC5424Formatter(facility=17, app_name="texcore-reporting")
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handlers = [handler]
    if os.path.exists("/dev/log"):
        syslog_h = logging.handlers.SysLogHandler(address="/dev/log")
        syslog_h.setFormatter(formatter)
        handlers.append(syslog_h)
    logging.root.handlers = []
    logging.basicConfig(level=logging.INFO, handlers=handlers)


_setup_logging()
logger = logging.getLogger(__name__)

# Fail-Fast. DJANGO_INTERNAL_URL se mantiene solo para el healthcheck.
DJANGO_INTERNAL_URL = _get_required_env("DJANGO_INTERNAL_URL")
INTERNAL_JWT_PUBLIC_KEY = _get_required_env("INTERNAL_JWT_PUBLIC_KEY").replace("\\n", "\n")

_raw_origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://backend:8000")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Reporting Excel Microservice",
    description="Formatea reportes Excel/CSV a partir de datos que le envía el backend Django",
    version="3.0.0",
    lifespan=lifespan,
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


@app.middleware("http")
async def verify_jwt_service_token(request: Request, call_next):
    """Reemplaza X-Internal-Key por JWT Bearer RS256 (ISO 27001 A.9.4)."""
    if request.url.path == "/health":
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Authorization header Bearer requerido."},
        )

    token = auth_header.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(
            token,
            INTERNAL_JWT_PUBLIC_KEY,
            algorithms=["RS256"],
            options={
                "verify_exp": True,
                "require": ["sub", "type"],
            },
        )
    except jwt.ExpiredSignatureError:
        return JSONResponse(status_code=401, content={"detail": "Token expirado."})
    except jwt.InvalidTokenError as exc:
        return JSONResponse(
            status_code=401, content={"detail": f"Token inválido: {exc}"}
        )

    # ISO 27001 A.9.4: rechazar refresh tokens usados como access tokens
    if payload.get("type") != "service_access":
        return JSONResponse(
            status_code=401,
            content={"detail": "Tipo de token incorrecto. Se requiere service_access."},
        )
    if payload.get("iss") != "texcore":
        return JSONResponse(
            status_code=401,
            content={"detail": "Emisor de token no reconocido."},
        )

    request.state.caller = payload.get("sub", "unknown")
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization"],
)


@app.get("/health")
def health_check():
    try:
        resp = httpx.get(f"{DJANGO_INTERNAL_URL}/api/health/", timeout=3.0)
        if resp.status_code == 200:
            return {"status": "healthy", "django_api": "connected"}
        return {"status": "degraded", "django_api": f"HTTP {resp.status_code}"}
    except httpx.RequestError:
        return {"status": "degraded", "django_api": "unreachable"}


from src.routers import generate

app.include_router(generate.router, tags=["Generate"])
