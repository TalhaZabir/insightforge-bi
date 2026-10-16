"""Health endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import engine

router = APIRouter(tags=["system"])


@router.get("/health")
def health():
    return {"status": "ok", "service": "insightforge-backend"}


@router.get("/readiness")
@router.get("/health/readiness")
def readiness():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "up"}
    except Exception as exc:  # never leak stack trace
        return {"status": "not_ready", "database": "down", "detail": type(exc).__name__}
