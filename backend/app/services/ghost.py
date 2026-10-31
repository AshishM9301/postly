"""Ghost ownership checks.

Ghost mode has no user row and no session row. Ownership is proven per target by
the client sending ``owner_key = HMAC(postKey, targetId)``; the server only ever
stores that opaque key next to the row. This module compares the two keys in
constant time and raises ``403 not_owner`` on a mismatch.
"""

from __future__ import annotations

from fastapi import HTTPException

from app.core.security import secure_compare

NOT_OWNER = {"code": "not_owner", "message": "The ownership key does not match this resource"}


def owner_key_matches(owner_key: str | None, ghost_owner_key: str | None) -> bool:
    return secure_compare(owner_key, ghost_owner_key)


def assert_ghost_owner(owner_key: str | None, ghost_owner_key: str | None) -> None:
    """Allow the action only when the client key matches the stored ghost key."""
    if not owner_key_matches(owner_key, ghost_owner_key):
        raise HTTPException(status_code=403, detail=dict(NOT_OWNER))
