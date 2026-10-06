"""Health check del printing_service."""
import pathlib

from fastapi import APIRouter, HTTPException

from ..config import REQUIRED_TEMPLATES, TEMPLATES_DIR

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    missing = [t for t in REQUIRED_TEMPLATES if not (pathlib.Path(TEMPLATES_DIR) / t).exists()]
    if missing:
        raise HTTPException(status_code=503, detail=f"Templates ausentes: {missing}")
    return {"status": "ok", "templates": "ok"}
