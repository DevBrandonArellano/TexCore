"""
Router de health check.
Verifica conectividad con Django Internal API con cliente HTTP reutilizable (connection pool).
"""
import os

import httpx
from fastapi import APIRouter, HTTPException

DJANGO_INTERNAL_URL = os.environ.get("DJANGO_INTERNAL_URL", "")

# Cliente con pool de conexiones reutilizado entre health-checks del orquestador.
_health_client = httpx.Client(timeout=3.0)

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check del servicio y conectividad con Django API")
def health_check():
    """Verifica que la Django Internal API es accesible. Retorna 503 si no responde."""
    try:
        resp = _health_client.get(f"{DJANGO_INTERNAL_URL}/api/health/")
        if resp.status_code == 200:
            return {"status": "healthy", "django_api": "connected"}
        raise HTTPException(
            status_code=503,
            detail=f"Django API respondió {resp.status_code}",
        )
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Django API unreachable: {exc}",
        )
