"""Postly API application."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.db.client import db

settings = get_settings()
logger = logging.getLogger(__name__)

_HTTP_ERROR_CODES = {
    400: "validation_error",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "internal_error",
}


def error_body(status_code: int, detail: object) -> dict[str, dict[str, object]]:
    """Normalise errors to the ``{"error": {code, message, details}}`` contract."""
    if isinstance(detail, dict) and "code" in detail:
        return {
            "error": {
                "code": detail["code"],
                "message": detail.get("message", ""),
                "details": detail.get("details", {}),
            }
        }
    return {
        "error": {
            "code": _HTTP_ERROR_CODES.get(status_code, "internal_error"),
            "message": str(detail),
            "details": {},
        }
    }


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(exc.status_code, exc.detail),
        headers=exc.headers,
    )


def _safe_validation_errors(errors: object) -> list[dict[str, Any]]:
    """Keep only type/loc/msg.

    ``input`` is the submitted value and ``ctx`` may carry it too — reflecting
    either would leak secrets (e.g. a too-short pseudonymous secret) into logs.
    """
    if not isinstance(errors, (list, tuple)):
        return []
    cleaned: list[dict[str, Any]] = []
    for error in errors:
        if not isinstance(error, dict):
            continue
        loc = error.get("loc", ())
        cleaned.append(
            {
                "type": str(error.get("type", "validation_error")),
                "loc": [str(part) for part in loc] if isinstance(loc, (list, tuple)) else [],
                "msg": str(error.get("msg", "Invalid value")),
            }
        )
    return cleaned


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Request validation failed",
                "details": {"errors": _safe_validation_errors(exc.errors())},
            }
        },
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "Internal server error",
                "details": {},
            }
        },
    )


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

app.include_router(v1_router, prefix=settings.api_prefix)
