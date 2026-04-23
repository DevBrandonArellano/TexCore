"""
Router de health check.
DIP: la sesión se inyecta via Depends(get_db) en lugar de instanciar SessionLocal().
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db

router = APIRouter(tags=["Health"])


@router.get("/health", summary="Health check del servicio y conexión a BD")
def health_check(db: Session = Depends(get_db)):
    """Verifica conectividad con SQL Server. Retorna 503 si la BD no responde."""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {exc}")
