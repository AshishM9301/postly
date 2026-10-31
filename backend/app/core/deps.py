"""Request-time identity resolution.

A request is one of three modes:

* ``google`` / ``pseudonymous`` — a bearer session token resolves a ``User``;
* ``ghost`` — no header at all, so no identity is resolved. Per-row ownership is
  proven separately with a ghost ``owner_key`` (see ``app.services.ghost``).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request

from app.core.config import get_settings
from app.core.security import hash_session_token, utcnow
from app.db.client import db

Mode = Literal["google", "pseudonymous", "ghost"]


@dataclass(frozen=True)
class Principal:
    mode: Mode
    user_id: str | None = None
    alias: str | None = None
    session_id: str | None = None
    expiry_days: int = 90
    is_admin: bool = False


def _unauthorized(message: str) -> HTTPException:
    return HTTPException(status_code=401, detail={"code": "unauthorized", "message": message})


def _bearer_token(request: Request) -> str | None:
    header = request.headers.get("Authorization")
    if not header:
        return None
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise _unauthorized("Malformed Authorization header")
    return token.strip()


async def get_principal(request: Request) -> Principal:
    """Resolve the caller. No header means ghost mode, not an error."""
    expiry_days = get_settings().ghost_post_ttl_days
    token = _bearer_token(request)
    if token is None:
        return Principal(mode="ghost", expiry_days=expiry_days)

    session = await db.session.find_unique(
        where={"tokenHash": hash_session_token(token)},
        include={"user": True},
    )
    if session is None or session.revokedAt is not None or session.expiresAt <= utcnow():
        raise _unauthorized("Invalid or expired session")

    user = session.user
    if user is None:
        raise _unauthorized("Session has no user")
    if user.isBanned:
        raise HTTPException(
            status_code=403,
            detail={"code": "forbidden", "message": "Account banned"},
        )

    return Principal(
        mode="pseudonymous" if user.isPseudonymous else "google",
        user_id=user.id,
        alias=user.alias,
        session_id=session.id,
        expiry_days=expiry_days,
        is_admin=user.isAdmin,
    )


async def require_user(
    principal: Annotated[Principal, Depends(get_principal)],
) -> Principal:
    """Reject ghost callers for endpoints that need a persisted identity."""
    if principal.mode == "ghost" or principal.user_id is None:
        raise _unauthorized("This endpoint requires a session")
    return principal
