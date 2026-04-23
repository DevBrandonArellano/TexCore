"""Health check del printing_service."""
import os
from fastapi import APIRouter, HTTPException
from ..config import TEMPLATES_DIR, REQUIRED_TEMPLATES

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    missing = [t for t in REQUIRED_TEMPLATES if not os.path.exists(os.path.join(TEMPLATES_DIR, t))]
    if missing:
        raise HTTPException(status_code=503, detail=f"Templates ausentes: {missing}")
    return {"status": "ok", "templates": "ok"}
