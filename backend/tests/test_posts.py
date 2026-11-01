"""Post CRUD across Google, pseudonymous and ghost callers, plus ownership."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from app.core.security import hash_session_token, new_session_token, utcnow
from app.main import app
from fastapi.testclient import TestClient
from prisma import Prisma
from prisma.enums import MediaKind, ModerationState

TITLE_PREFIX = "T015:"


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_user(pseudonymous: bool) -> dict[str, str]:
    async def run() -> dict[str, str]:
        db = Prisma()
        await db.connect()
        try:
            alias = f"T015_{uuid4().hex[:10]}"
            user = await db.user.create(data={"alias": alias, "isPseudonymous": pseudonymous})
            token = new_session_token()
            await db.session.create(
                data={
                    "userId": user.id,
                    "tokenHash": hash_session_token(token),
                    "expiresAt": utcnow() + timedelta(hours=1),
                }
            )
            return {"id": user.id, "alias": alias, "token": token}
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _lookup_ids() -> tuple[str, str]:
    async def run() -> tuple[str, str]:
        db = Prisma()
        await db.connect()
        try:
            area = await db.area.find_unique(where={"pincode": "110019"})
            category = await db.category.find_unique(where={"slug": "pothole"})
            if area is None or category is None:
                raise RuntimeError("seed areas and categories before running post tests")
            return area.id, category.id
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _cleanup(user_ids: list[str]) -> None:
    async def run() -> None:
        db = Prisma()
        await db.connect()
        try:
            await db.post.delete_many(where={"title": {"startswith": TITLE_PREFIX}})
            await db.user.delete_many(where={"id": {"in": user_ids}})
        finally:
            await db.disconnect()

    asyncio.run(run())


def _fetch_post(post_id: str):
    async def run():
        db = Prisma()
        await db.connect()
        try:
            return await db.post.find_unique(where={"id": post_id})
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _add_media(post_id: str) -> None:
    async def run() -> None:
        db = Prisma()
        await db.connect()
        try:
            await db.media.create(
                data={
                    "postId": post_id,
                    "kind": MediaKind.IMAGE,
                    "path": f"test/{uuid4().hex}.jpg",
                    "mimeType": "image/jpeg",
                    "bytes": 123,
                    "moderationState": ModerationState.CLEAN,
                }
            )
        finally:
            await db.disconnect()

    asyncio.run(run())


def _count_media(post_id: str) -> int:
    async def run() -> int:
        db = Prisma()
        await db.connect()
        try:
            return await db.media.count(where={"postId": post_id})
        finally:
            await db.disconnect()

    return asyncio.run(run())


@pytest.fixture()
def env(client: TestClient) -> Iterator[dict]:
    google = _create_user(pseudonymous=False)
    pseudo = _create_user(pseudonymous=True)
    area_id, category_id = _lookup_ids()
    try:
        yield {
            "google": google,
            "pseudo": pseudo,
            "area_id": area_id,
            "category_id": category_id,
        }
    finally:
        _cleanup([google["id"], pseudo["id"]])


def _payload(env: dict, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "title": f"{TITLE_PREFIX} deep pothole",
        "body": f"{TITLE_PREFIX} three bikes crashed here",
        "area_id": env["area_id"],
        "category_id": env["category_id"],
    }
    payload.update(overrides)
    return payload


def _create(client: TestClient, env: dict, who: str, **overrides: object):
    headers = {} if who == "ghost" else _bearer(env[who]["token"])
    return client.post("/api/v1/posts", json=_payload(env, **overrides), headers=headers)


def test_create_works_for_three_modes_with_the_same_shape(env: dict, client: TestClient) -> None:
    google = _create(client, env, "google")
    pseudo = _create(client, env, "pseudo")
    ghost = _create(
        client,
        env,
        "ghost",
        alias="Neighbor_gh0st",
        owner_key="ghost-key-123",
    )

    assert google.status_code == 201, google.text
    assert pseudo.status_code == 201, pseudo.text
    assert ghost.status_code == 201, ghost.text

    g = google.json()["data"]
    p = pseudo.json()["data"]
    h = ghost.json()["data"]

    assert set(g) == set(p) == set(h)
    assert g["status"] == "OPEN"
    assert g["is_anonymous"] is False
    assert g["author"]["id"] == env["google"]["id"]
    assert g["alias"] == env["google"]["alias"]

    assert p["is_anonymous"] is True
    assert p["author"]["id"] == env["pseudo"]["id"]
    assert p["alias"] == env["pseudo"]["alias"]

    assert h["is_anonymous"] is True
    assert h["author"] is None
    assert h["alias"] == "Neighbor_gh0st"


def test_ghost_create_stores_owner_key_and_no_author(env: dict, client: TestClient) -> None:
    ghost_id = str(uuid4())
    response = _create(
        client,
        env,
        "ghost",
        id=ghost_id,
        alias="Neighbor_gh0st",
        owner_key="ghost-key-123",
    )

    assert response.status_code == 201
    assert "ghost-key-123" not in response.text
    assert "ghostOwnerKey" not in response.text

    row = _fetch_post(ghost_id)
    assert row is not None
    assert row.authorId is None
    assert row.ghostOwnerKey == "ghost-key-123"
    assert row.alias == "Neighbor_gh0st"


def test_client_generated_and_server_generated_ids(env: dict, client: TestClient) -> None:
    provided = str(uuid4())
    created = _create(client, env, "google", id=provided)

    assert created.status_code == 201
    assert created.json()["data"]["id"] == provided
    row = _fetch_post(provided)
    assert row is not None
    assert row.id == provided

    generated = _create(client, env, "google")
    assert generated.status_code == 201
    generated_id = generated.json()["data"]["id"]

    assert str(UUID(generated_id)) == generated_id
    assert _fetch_post(generated_id) is not None


def test_get_post_returns_relations_but_no_secrets(env: dict, client: TestClient) -> None:
    created = _create(
        client,
        env,
        "ghost",
        alias="Neighbor_gh0st",
        owner_key="ghost-key-123",
        blame_category="MUNICIPALITY",
        blame_label="MCD",
        lat=28.631234,
        lng=77.071234,
    )
    post_id = created.json()["data"]["id"]

    response = client.get(f"/api/v1/posts/{post_id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == post_id
    assert data["area"]["pincode"] == "110019"
    assert data["category"]["slug"] == "pothole"
    assert data["media"] == []
    assert data["blame_category"] == "MUNICIPALITY"
    assert data["blame_label"] == "MCD"
    assert data["lat"] == 28.631
    assert data["lng"] == 77.071
    assert data["author"] is None

    for needle in (
        "ghostOwnerKey",
        "ghost_owner_key",
        "owner_key",
        "secretHash",
        "tokenHash",
        "ghost-key-123",
    ):
        assert needle not in response.text, needle


def test_get_unknown_post_is_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/posts/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "post_not_found"


def test_edit_is_owner_only(env: dict, client: TestClient) -> None:
    post_id = _create(client, env, "google").json()["data"]["id"]

    edited = client.patch(
        f"/api/v1/posts/{post_id}",
        json={"title": f"{TITLE_PREFIX} edited title"},
        headers=_bearer(env["google"]["token"]),
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["title"] == f"{TITLE_PREFIX} edited title"

    other = client.patch(
        f"/api/v1/posts/{post_id}",
        json={"title": f"{TITLE_PREFIX} hijack"},
        headers=_bearer(env["pseudo"]["token"]),
    )
    assert other.status_code == 403
    assert other.json()["error"]["code"] == "not_owner"


def test_ghost_edit_requires_the_owner_key(env: dict, client: TestClient) -> None:
    post_id = _create(
        client, env, "ghost", alias="Neighbor_gh0st", owner_key="ghost-key-123"
    ).json()["data"]["id"]

    missing = client.patch(f"/api/v1/posts/{post_id}", json={"title": f"{TITLE_PREFIX} nope"})
    assert missing.status_code == 403

    wrong = client.request(
        "PATCH",
        f"/api/v1/posts/{post_id}",
        json={"title": f"{TITLE_PREFIX} nope", "owner_key": "wrong-key"},
    )
    assert wrong.status_code == 403

    right = client.request(
        "PATCH",
        f"/api/v1/posts/{post_id}",
        json={"title": f"{TITLE_PREFIX} edited by ghost", "owner_key": "ghost-key-123"},
    )
    assert right.status_code == 200
    assert right.json()["data"]["title"] == f"{TITLE_PREFIX} edited by ghost"


def test_delete_is_owner_only_and_hard_deletes(env: dict, client: TestClient) -> None:
    post_id = _create(client, env, "google").json()["data"]["id"]

    other = client.request(
        "DELETE",
        f"/api/v1/posts/{post_id}",
        headers=_bearer(env["pseudo"]["token"]),
    )
    assert other.status_code == 403

    deleted = client.request(
        "DELETE",
        f"/api/v1/posts/{post_id}",
        headers=_bearer(env["google"]["token"]),
    )
    assert deleted.status_code == 204
    assert client.get(f"/api/v1/posts/{post_id}").status_code == 404
    assert _fetch_post(post_id) is None


def test_ghost_delete_requires_the_owner_key(env: dict, client: TestClient) -> None:
    post_id = _create(
        client, env, "ghost", alias="Neighbor_gh0st", owner_key="ghost-key-123"
    ).json()["data"]["id"]

    wrong = client.request(
        "DELETE",
        f"/api/v1/posts/{post_id}",
        json={"owner_key": "wrong-key"},
    )
    assert wrong.status_code == 403
    assert _fetch_post(post_id) is not None

    right = client.request(
        "DELETE",
        f"/api/v1/posts/{post_id}",
        json={"owner_key": "ghost-key-123"},
    )
    assert right.status_code == 204
    assert _fetch_post(post_id) is None


def test_delete_cascades_media_rows(env: dict, client: TestClient) -> None:
    post_id = _create(client, env, "google").json()["data"]["id"]
    _add_media(post_id)
    assert _count_media(post_id) == 1

    deleted = client.request(
        "DELETE",
        f"/api/v1/posts/{post_id}",
        headers=_bearer(env["google"]["token"]),
    )
    assert deleted.status_code == 204
    assert _count_media(post_id) == 0


def test_create_validates_area_category_status_and_blame(env: dict, client: TestClient) -> None:
    headers = _bearer(env["google"]["token"])

    unknown_area = client.post(
        "/api/v1/posts", json=_payload(env, area_id="missing"), headers=headers
    )
    assert unknown_area.status_code == 422
    assert unknown_area.json()["error"]["code"] == "area_required"

    unknown_category = client.post(
        "/api/v1/posts", json=_payload(env, category_id="missing"), headers=headers
    )
    assert unknown_category.status_code == 422
    assert unknown_category.json()["error"]["code"] == "validation_error"

    bad_status = client.post(
        "/api/v1/posts", json=_payload(env, status="IN_PROGRESS"), headers=headers
    )
    assert bad_status.status_code == 422

    label_without_category = client.post(
        "/api/v1/posts", json=_payload(env, blame_label="Somebody"), headers=headers
    )
    assert label_without_category.status_code == 422

    bad_blame = client.post(
        "/api/v1/posts", json=_payload(env, blame_category="INDIVIDUAL"), headers=headers
    )
    assert bad_blame.status_code == 422

    media = client.post("/api/v1/posts", json=_payload(env, media_ids=["x"]), headers=headers)
    assert media.status_code == 422
    assert media.json()["error"]["code"] == "media_not_supported"


def test_ghost_create_requires_alias_and_owner_key(env: dict, client: TestClient) -> None:
    no_alias = client.post("/api/v1/posts", json=_payload(env, owner_key="ghost-key-123"))
    assert no_alias.status_code == 422

    no_key = client.post("/api/v1/posts", json=_payload(env, alias="Neighbor_gh0st"))
    assert no_key.status_code == 422


def test_validation_error_never_echoes_the_owner_key(client: TestClient) -> None:
    secret = "owner-secret-" + "x" * 600

    response = client.request(
        "DELETE",
        f"/api/v1/posts/{uuid4()}",
        json={"owner_key": secret},
    )

    assert response.status_code == 422
    assert secret not in response.text
