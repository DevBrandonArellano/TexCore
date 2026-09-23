"""
App factory del printing_service.
Responsabilidad única: crear la aplicación FastAPI y registrar los routers.
RFC 5424: logging estructurado con SD-ELEMENT en todas las operaciones.
ISO 27001 A.12.4: persistencia de eventos de auditoría de impresión en SQLite.
Autenticación: JWT Bearer RS256 (mismo esquema que scanning_service y
reporting_excel) — sin esto, cualquier actor con acceso a la red interna
de Docker podía generar PDFs/ZPL con datos arbitrarios (notas de venta,
etiquetas) sin credenciales, exponiendo información de gerencia.
"""
import logging
import logging.handlers
import os
from contextlib import asynccontextmanager

import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

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


def _get_required_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Variable de entorno requerida no configurada: '{name}'"
        )
    return value


# Fail-Fast: el servicio no arranca sin esta variable
INTERNAL_JWT_PUBLIC_KEY = _get_required_env("INTERNAL_JWT_PUBLIC_KEY").replace("\\n", "\n")

app = FastAPI(
    title="TexCore Printing Service",
    description="Microservicio para generación de PDFs y etiquetas ZPL",
    version="2.0.0",
    lifespan=lifespan,
)


@app.middleware("http")
async def verify_jwt_service_token(request: Request, call_next):
    """Exige JWT Bearer RS256 válido en todo endpoint salvo /health."""
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

    return await call_next(request)


app.include_router(health.router)
app.include_router(pdf.router)
app.include_router(zpl.router)
