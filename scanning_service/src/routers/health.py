"""
Router de health check.
Verifica conectividad con Django Internal API en lugar de BD directa.
"""
import httpx
from fastapi import APIRouter, HTTPException

from ..main import DJANGO_INTERNAL_URL

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check del servicio y conectividad con Django API")
def health_check():
    """Verifica que la Django Internal API es accesible. Retorna 503 si no responde."""
    try:
        resp = httpx.get(f"{DJANGO_INTERNAL_URL}/api/health/", timeout=3.0)
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
