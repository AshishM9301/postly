"""Health endpoint: reports the real database status."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.db.client import db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> JSONResponse:
    try:
        await db.query_raw("SELECT 1")
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "down"},
        )
    return JSONResponse(status_code=200, content={"status": "ok", "db": "ok"})
