"""Health endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import engine

router = APIRouter()


@router.get("/health")
def health():
    return {"status": "ok", "service": "insightforge-backend"}


@router.get("/readiness")
def readiness():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ready", "database": "up"}
    except Exception as exc:  # never leak stack trace
        return {"status": "not_ready", "database": "down", "detail": type(exc).__name__}
