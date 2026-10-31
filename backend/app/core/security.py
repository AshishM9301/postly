"""Cryptographic helpers: hashing, session tokens, aliases and Firebase verification.

The invariants live here:

* a secret (pseudonymous key, session token) is only ever stored as ``HMAC-SHA256(PEPPER, value)``;
* a ghost owner key is compared, never derived from anything the server holds;
* we only keep the Firebase ``uid`` — never the email/phone that may ride along in the claims.
"""

from __future__ import annotations

import hmac
import json
import secrets
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

import firebase_admin
from firebase_admin import auth, credentials

from app.core.config import get_settings

SESSION_TOKEN_PREFIX = "postly_sess_"
ALIAS_PREFIX = "Neighbor_"
# No 0/o, 1/i/l so an alias read aloud stays unambiguous.
ALIAS_ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
ALIAS_LENGTH = 4

_FIREBASE_ISSUER_PREFIX = "https://securetoken.google.com/"

_firebase_app: firebase_admin.App | None = None
_firebase_project: str | None = None


class InvalidFirebaseToken(Exception):
    """The Firebase ID token failed signature, expiry, issuer or audience checks."""


class FirebaseNotConfigured(Exception):
    """FIREBASE_ADMIN_CREDENTIALS is missing or unreadable."""


def utcnow() -> datetime:
    """Aware UTC. prisma-client-py returns aware datetimes; compare like with like."""
    return datetime.now(UTC)


def _pepper() -> bytes:
    return get_settings().pepper.encode("utf-8")


def hash_secret(secret: str) -> str:
    """Hash a client-held secret (pseudonymous secret, session token)."""
    return hmac.new(_pepper(), secret.encode("utf-8"), sha256).hexdigest()


def new_session_token() -> str:
    """Opaque session token; only the hash of this value is stored."""
    return f"{SESSION_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_session_token(token: str) -> str:
    return hash_secret(token)


def random_alias() -> str:
    suffix = "".join(secrets.choice(ALIAS_ALPHABET) for _ in range(ALIAS_LENGTH))
    return f"{ALIAS_PREFIX}{suffix}"


def secure_compare(left: str | None, right: str | None) -> bool:
    if not left or not right:
        return False
    return hmac.compare_digest(str(left), str(right))


def _load_firebase_credentials() -> tuple[credentials.Certificate, str | None]:
    raw = get_settings().firebase_admin_credentials.strip()
    if not raw:
        raise FirebaseNotConfigured("FIREBASE_ADMIN_CREDENTIALS is not set")

    try:
        if raw.startswith("{"):
            data: dict[str, Any] = json.loads(raw)
        else:
            path = Path(raw)
            if not path.is_file():
                raise FirebaseNotConfigured(
                    "FIREBASE_ADMIN_CREDENTIALS is not valid JSON or a file"
                )
            data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise FirebaseNotConfigured("FIREBASE_ADMIN_CREDENTIALS is not valid JSON") from exc

    return credentials.Certificate(data), data.get("project_id")


def _ensure_firebase_app() -> None:
    global _firebase_app, _firebase_project
    if _firebase_app is not None:
        return

    try:
        _firebase_app = firebase_admin.get_app()
    except ValueError:
        credential, project_id = _load_firebase_credentials()
        _firebase_app = firebase_admin.initialize_app(credential)
        _firebase_project = project_id


def _firebase_project_id() -> str | None:
    if _firebase_project:
        return _firebase_project
    return get_settings().firebase_project_id.strip() or None


def verify_firebase_token(id_token: str) -> str:
    """Verify a Firebase ID token and return only the ``uid``.

    Raises :class:`InvalidFirebaseToken` for tampered/expired tokens and for a
    token minted for a different project.
    """
    _ensure_firebase_app()

    try:
        claims = auth.verify_id_token(id_token, check_revoked=False)
    except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, ValueError) as exc:
        raise InvalidFirebaseToken("Firebase rejected the ID token") from exc

    project_id = _firebase_project_id()
    if project_id:
        if claims.get("aud") != project_id:
            raise InvalidFirebaseToken("Token audience does not match the project")
        if claims.get("iss") != f"{_FIREBASE_ISSUER_PREFIX}{project_id}":
            raise InvalidFirebaseToken("Token issuer does not match the project")

    uid = claims.get("uid") or claims.get("sub")
    if not uid:
        raise InvalidFirebaseToken("Token has no uid")
    return str(uid)
