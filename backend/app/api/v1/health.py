"""Health endpoint: reports the real database status."""

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.db.client import db

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: Literal["ok", "down"]


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse}},
)
async def health() -> JSONResponse:
    try:
        await db.query_raw("SELECT 1")
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "down"},
        )
    return JSONResponse(status_code=200, content={"status": "ok", "db": "ok"})
