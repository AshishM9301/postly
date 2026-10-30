"""Minimal Postly API skeleton.

T-003 expands this into the real structure: app/core/config.py (settings),
app/db/client.py (prisma singleton), app/api/v1/ routers and tests.
For now: one health endpoint that really talks to the database.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from prisma import Prisma

db = Prisma()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await db.connect()
    try:
        yield
    finally:
        await db.disconnect()


app = FastAPI(
    title="Postly API",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    try:
        await db.spikerow.count()
    except Exception:
        return {"status": "degraded", "db": "down", "version": "0.1.0"}
    return {"status": "ok", "db": "ok", "version": "0.1.0"}
