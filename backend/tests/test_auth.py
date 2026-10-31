"""Auth: three identity modes, session resolution and ghost ownership."""

from __future__ import annotations

import asyncio
import hmac
import secrets
from hashlib import sha256
from uuid import uuid4

import pytest
from app.core import security
from app.core.config import get_settings
from app.main import app, http_exception_handler, unhandled_exception_handler
from app.services.ghost import assert_ghost_owner
from fastapi import FastAPI
from fastapi.testclient import TestClient
from prisma import Prisma
from prisma.enums import ModerationState, PostStatus
from prisma.models import Session, User
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

PROJECT_ID = "postly-test"
FORBIDDEN_FIELDS = {
    "email",
    "phone",
    "phone_number",
    "ip",
    "ip_address",
    "user_agent",
    "useragent",
}


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def firebase(monkeypatch: pytest.MonkeyPatch) -> dict:
    """Stand in for firebase-admin while keeping the issuer/audience checks real."""
    state: dict = {
        "uid": f"uid-{uuid4().hex}",
        "error": None,
        "aud": PROJECT_ID,
        "iss": f"https://securetoken.google.com/{PROJECT_ID}",
        "extra": {},
    }

    def fake_verify(id_token, app=None, check_revoked=False, clock_skew_seconds=0):
        if state["error"] is not None:
            raise state["error"]
        return {
            "uid": state["uid"],
            "sub": state["uid"],
            "aud": state["aud"],
            "iss": state["iss"],
            **state["extra"],
        }

    monkeypatch.setattr(security, "_ensure_firebase_app", lambda: None)
    monkeypatch.setattr(security, "_firebase_project_id", lambda: PROJECT_ID)
    monkeypatch.setattr(security.auth, "verify_id_token", fake_verify)
    return state


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _fetch_user(alias: str) -> User | None:
    db = Prisma()
    await db.connect()
    try:
        return await db.user.find_unique(where={"alias": alias})
    finally:
        await db.disconnect()


async def _fetch_sessions(user_id: str) -> list[Session]:
    db = Prisma()
    await db.connect()
    try:
        return await db.session.find_many(where={"userId": user_id})
    finally:
        await db.disconnect()


async def _delete_user(user_id: str) -> None:
    db = Prisma()
    await db.connect()
    try:
        await db.user.delete_many(where={"id": user_id})
    finally:
        await db.disconnect()


def _cleanup(user_id: str | None) -> None:
    if user_id:
        asyncio.run(_delete_user(user_id))


def test_google_valid_token_creates_session(client: TestClient, firebase: dict) -> None:
    response = client.post("/api/v1/auth/google", json={"id_token": "a-valid-token"})

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["mode"] == "google"
    assert payload["alias"].startswith("Neighbor_")
    assert payload["token"].startswith("postly_sess_")

    me = client.get("/api/v1/me", headers=_bearer(payload["token"]))
    assert me.status_code == 200
    principal = me.json()["data"]
    assert principal["mode"] == "google"
    assert principal["alias"] == payload["alias"]
    assert principal["user_id"] is not None
    assert principal["expiry_days"] == get_settings().ghost_post_ttl_days

    _cleanup(principal["user_id"])


def test_google_rejects_wrong_project_audience(client: TestClient, firebase: dict) -> None:
    firebase["aud"] = "some-other-project"

    response = client.post("/api/v1/auth/google", json={"id_token": "a-valid-token"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.parametrize(
    "error",
    [
        security.auth.InvalidIdTokenError("bad signature"),
        security.auth.ExpiredIdTokenError("token expired", "expired"),
    ],
)
def test_google_rejects_tampered_or_expired_token(
    client: TestClient, firebase: dict, error: Exception
) -> None:
    firebase["error"] = error

    response = client.post("/api/v1/auth/google", json={"id_token": "not-valid"})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_pseudo_create_and_reuse(client: TestClient) -> None:
    secret = secrets.token_urlsafe(32)

    first = client.post("/api/v1/auth/pseudo", json={"secret": secret})
    second = client.post("/api/v1/auth/pseudo", json={"secret": secret})

    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()["data"]
    second_data = second.json()["data"]
    assert first_data["mode"] == "pseudonymous"
    assert first_data["alias"] == second_data["alias"]
    assert first_data["token"] != second_data["token"]

    me = client.get("/api/v1/me", headers=_bearer(second_data["token"]))
    assert me.status_code == 200
    principal = me.json()["data"]
    assert principal["mode"] == "pseudonymous"
    assert principal["alias"] == first_data["alias"]

    user = asyncio.run(_fetch_user(first_data["alias"]))
    try:
        assert user is not None
        assert user.isPseudonymous is True
        expected_hash = hmac.new(
            get_settings().pepper.encode(), secret.encode(), sha256
        ).hexdigest()
        assert user.secretHash == expected_hash
        assert user.secretHash != secret
        assert secret not in repr(user.model_dump())
    finally:
        _cleanup(principal["user_id"])


def test_rotate_alias_issues_a_new_alias_for_same_identity(client: TestClient) -> None:
    created = client.post("/api/v1/auth/pseudo", json={"secret": secrets.token_urlsafe(32)}).json()[
        "data"
    ]

    rotated = client.post("/api/v1/auth/rotate-alias", headers=_bearer(created["token"]))
    assert rotated.status_code == 200
    new_alias = rotated.json()["data"]["alias"]
    assert new_alias != created["alias"]
    assert new_alias.startswith("Neighbor_")

    me = client.get("/api/v1/me", headers=_bearer(created["token"]))
    principal = me.json()["data"]
    assert principal["alias"] == new_alias
    assert principal["mode"] == "pseudonymous"
    _cleanup(principal["user_id"])


def test_rotate_alias_requires_a_session(client: TestClient) -> None:
    response = client.post("/api/v1/auth/rotate-alias")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_ghost_request_has_no_session(client: TestClient) -> None:
    response = client.get("/api/v1/me")

    assert response.status_code == 200
    principal = response.json()["data"]
    assert principal["mode"] == "ghost"
    assert principal["alias"] is None
    assert principal["user_id"] is None
    assert principal["expiry_days"] == get_settings().ghost_post_ttl_days


def test_validation_error_uses_envelope_and_never_echoes_the_secret(
    client: TestClient,
) -> None:
    secret = "s3cr3t-must-not-appear"

    response = client.post("/api/v1/auth/pseudo", json={"secret": secret})

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "validation_error"
    assert secret not in response.text
    for error in payload["error"]["details"]["errors"]:
        assert set(error) == {"type", "loc", "msg"}


def test_non_object_json_body_uses_envelope_without_echoing_it(client: TestClient) -> None:
    secret = "s3cr3t-must-not-appear"

    response = client.post("/api/v1/auth/pseudo", json=[secret])

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert secret not in response.text


def test_unhandled_error_uses_envelope_without_leaking_details() -> None:
    detail = "internal-detail-must-not-leak"

    probe = FastAPI()
    probe.add_exception_handler(Exception, unhandled_exception_handler)

    @probe.get("/boom")
    async def boom() -> None:
        raise RuntimeError(detail)

    with TestClient(probe, raise_server_exceptions=False) as probe_client:
        response = probe_client.get("/boom")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert detail not in response.text


def test_unknown_session_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/me", headers=_bearer("postly_sess_not-a-real-token"))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


class GhostCheckBody(BaseModel):
    owner_key: str
    ghost_owner_key: str


def test_ghost_ownership_success_and_failure() -> None:
    stored_key = hmac.new(b"post-key", b"post-id", sha256).hexdigest()

    probe = FastAPI()
    probe.add_exception_handler(StarletteHTTPException, http_exception_handler)

    @probe.post("/check")
    async def check(body: GhostCheckBody) -> dict[str, bool]:
        assert_ghost_owner(body.owner_key, body.ghost_owner_key)
        return {"ok": True}

    with TestClient(probe) as probe_client:
        allowed = probe_client.post(
            "/check", json={"owner_key": stored_key, "ghost_owner_key": stored_key}
        )
        denied = probe_client.post(
            "/check", json={"owner_key": "0" * 64, "ghost_owner_key": stored_key}
        )

    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "not_owner"


async def _ghost_row_round_trip() -> None:
    db = Prisma()
    await db.connect()
    suffix = uuid4().hex
    post_id = str(uuid4())
    post_key = secrets.token_bytes(32)
    owner_key = hmac.new(post_key, post_id.encode(), sha256).hexdigest()

    user = None
    area = None
    category = None
    try:
        before_users = await db.user.count()
        before_sessions = await db.session.count()

        area = await db.area.create(
            data={
                "pincode": f"8{int(suffix[:5], 16) % 100_000:05d}",
                "name": "Ghost Test Area",
                "district": "TEST",
                "lat": 28.61,
                "lng": 77.21,
            }
        )
        category = await db.category.create(
            data={
                "name": "Ghost Test Category",
                "slug": f"ghost-test-{suffix[:8]}",
                "icon": "circle-help",
                "color": "#000000",
                "sortOrder": 998,
            }
        )
        post = await db.post.create(
            data={
                "id": post_id,
                "alias": f"Neighbor_g{suffix[:3]}",
                "isAnonymous": True,
                "ghostOwnerKey": owner_key,
                "title": "Ghost post",
                "body": "Created without any identity row.",
                "status": PostStatus.OPEN,
                "moderationState": ModerationState.CLEAN,
                "area": {"connect": {"id": area.id}},
                "category": {"connect": {"id": category.id}},
            }
        )

        stored = await db.post.find_unique(where={"id": post.id})
        assert stored is not None
        assert stored.authorId is None
        assert stored.ghostOwnerKey == owner_key
        assert post_key.hex() != stored.ghostOwnerKey
        assert post_key.hex() not in stored.ghostOwnerKey
        assert await db.user.count() == before_users
        assert await db.session.count() == before_sessions

        user = await db.user.find_first(where={"alias": post.alias})
        assert user is None
    finally:
        await db.post.delete_many(where={"id": post_id})
        if area is not None:
            await db.area.delete_many(where={"id": area.id})
        if category is not None:
            await db.category.delete_many(where={"id": category.id})
        await db.disconnect()


def test_ghost_rows_create_no_identity_and_store_no_secret() -> None:
    asyncio.run(_ghost_row_round_trip())


def test_identity_tables_have_no_contact_or_network_columns() -> None:
    assert FORBIDDEN_FIELDS.isdisjoint(User.model_fields)
    assert FORBIDDEN_FIELDS.isdisjoint(Session.model_fields)


def test_google_claims_email_and_phone_are_not_persisted(
    client: TestClient, firebase: dict
) -> None:
    email = f"person-{uuid4().hex}@example.com"
    phone = f"+9198{uuid4().int % 10**8:08d}"
    firebase["extra"] = {"email": email, "phone_number": phone}

    created = client.post("/api/v1/auth/google", json={"id_token": "valid"}).json()["data"]
    me = client.get("/api/v1/me", headers=_bearer(created["token"])).json()["data"]

    user = asyncio.run(_fetch_user(created["alias"]))
    sessions = asyncio.run(_fetch_sessions(me["user_id"]))
    try:
        assert user is not None
        blob = repr(user.model_dump()) + repr([session.model_dump() for session in sessions])
        assert email not in blob
        assert phone not in blob
    finally:
        _cleanup(me["user_id"])
