"""Auth endpoints: Google, pseudonymous and alias rotation.

Ghost mode deliberately has **no endpoint here** — it has no user row and no
session row. Ghost ownership is verified per resource, never by authenticating.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from prisma.models import User

from app.core.config import get_settings
from app.core.deps import Principal, require_user
from app.core.security import (
    FirebaseNotConfigured,
    InvalidFirebaseToken,
    hash_secret,
    hash_session_token,
    new_session_token,
    random_alias,
    utcnow,
    verify_firebase_token,
)
from app.db.client import db
from app.schemas.auth import (
    AliasResponse,
    AuthResponse,
    Envelope,
    GoogleAuthRequest,
    PseudoAuthRequest,
)

router = APIRouter(tags=["auth"])

_ALIAS_ATTEMPTS = 12


async def _unique_alias() -> str:
    for _ in range(_ALIAS_ATTEMPTS):
        alias = random_alias()
        if await db.user.find_unique(where={"alias": alias}) is None:
            return alias
    raise HTTPException(
        status_code=500,
        detail={"code": "internal_error", "message": "Could not allocate an alias"},
    )


async def _new_session(user_id: str) -> str:
    settings = get_settings()
    token = new_session_token()
    await db.session.create(
        data={
            "userId": user_id,
            "tokenHash": hash_session_token(token),
            "expiresAt": utcnow() + timedelta(days=settings.session_ttl_days),
        }
    )
    return token


def _validate_expiry(expiry_days: int | None) -> None:
    if expiry_days is None:
        return
    if expiry_days not in get_settings().ghost_expiry_option_list:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_error",
                "message": "expiry_days must be one of the configured options",
                "details": {"options": get_settings().ghost_expiry_option_list},
            },
        )


@router.post("/auth/google", response_model=Envelope[AuthResponse])
async def auth_google(body: GoogleAuthRequest) -> Envelope[AuthResponse]:
    """Exchange a Firebase ID token for an opaque Postly session token."""
    try:
        firebase_uid = verify_firebase_token(body.id_token)
    except InvalidFirebaseToken as exc:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "Invalid Firebase ID token"},
        ) from exc
    except FirebaseNotConfigured as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "firebase_unavailable", "message": "Google sign-in is not configured"},
        ) from exc

    user = await db.user.find_unique(where={"firebaseUid": firebase_uid})
    if user is None:
        user = await db.user.create(
            data={
                "alias": await _unique_alias(),
                "firebaseUid": firebase_uid,
                "isPseudonymous": False,
            }
        )

    token = await _new_session(user.id)
    return Envelope(data=AuthResponse(alias=user.alias, token=token, mode="google"))


@router.post("/auth/pseudo", response_model=Envelope[AuthResponse])
async def auth_pseudo(body: PseudoAuthRequest) -> Envelope[AuthResponse]:
    """Create or reopen a pseudonymous identity.

    The raw ``secret`` leaves this function unpersisted: only its salted hash is
    written to ``User.secretHash``. Reusing the same secret reopens the identity.
    """
    _validate_expiry(body.expiry_days)

    secret_hash = hash_secret(body.secret)
    user = await db.user.find_first(where={"secretHash": secret_hash})

    if user is None:
        if body.alias is not None:
            if await db.user.find_unique(where={"alias": body.alias}) is not None:
                raise HTTPException(
                    status_code=409,
                    detail={"code": "alias_taken", "message": "That alias is already in use"},
                )
            alias = body.alias
        else:
            alias = await _unique_alias()

        user = await db.user.create(
            data={
                "alias": alias,
                "secretHash": secret_hash,
                "isPseudonymous": True,
            }
        )

    token = await _new_session(user.id)
    return Envelope(data=AuthResponse(alias=user.alias, token=token, mode="pseudonymous"))


@router.post("/auth/rotate-alias", response_model=Envelope[AliasResponse])
async def rotate_alias(
    principal: Annotated[Principal, Depends(require_user)],
) -> Envelope[AliasResponse]:
    """Issue a fresh alias for the same identity, leaving history intact."""
    user = await _reload_user(principal.user_id)
    updated: User = await db.user.update(
        where={"id": user.id},
        data={"alias": await _unique_alias()},
    )
    mode = "pseudonymous" if updated.isPseudonymous else "google"
    return Envelope(data=AliasResponse(alias=updated.alias, mode=mode))


async def _reload_user(user_id: str | None) -> User:
    user = await db.user.find_unique(where={"id": user_id}) if user_id else None
    if user is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "Session has no user"},
        )
    return user
