"""Media upload, blurHash, signed URLs and revocation."""

from __future__ import annotations

import asyncio
import io
from collections.abc import Iterator
from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.security import hash_session_token, new_session_token, utcnow
from app.main import app
from app.providers.storage.local import LocalStorageProvider
from app.services import media as media_service
from fastapi.testclient import TestClient
from PIL import Image
from prisma import Prisma
from prisma.enums import ModerationState, PostStatus

TITLE_PREFIX = "T016:"


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
            alias = f"T016_{uuid4().hex[:10]}"
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


def _delete_user(user_id: str) -> None:
    async def run() -> None:
        db = Prisma()
        await db.connect()
        try:
            await db.user.delete_many(where={"id": user_id})
        finally:
            await db.disconnect()

    asyncio.run(run())


def _lookup_ids() -> tuple[str, str]:
    async def run() -> tuple[str, str]:
        db = Prisma()
        await db.connect()
        try:
            area = await db.area.find_unique(where={"pincode": "110019"})
            category = await db.category.find_unique(where={"slug": "pothole"})
            if area is None or category is None:
                raise RuntimeError("seed areas and categories before media tests")
            return area.id, category.id
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _create_post(user_id: str, alias: str, area_id: str, category_id: str) -> str:
    async def run() -> str:
        db = Prisma()
        await db.connect()
        try:
            post = await db.post.create(
                data={
                    "authorId": user_id,
                    "alias": alias,
                    "isAnonymous": False,
                    "areaId": area_id,
                    "categoryId": category_id,
                    "title": f"{TITLE_PREFIX} media",
                    "body": f"{TITLE_PREFIX} body",
                    "status": PostStatus.OPEN,
                    "moderationState": ModerationState.CLEAN,
                }
            )
            return post.id
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _delete_media(media_id: str) -> None:
    async def run() -> None:
        db = Prisma()
        await db.connect()
        try:
            await db.media.delete_many(where={"id": media_id})
        finally:
            await db.disconnect()

    asyncio.run(run())


@pytest.fixture()
def env(tmp_path, monkeypatch, client: TestClient) -> Iterator[dict]:
    provider = LocalStorageProvider(tmp_path / "media")
    monkeypatch.setattr(media_service, "storage", provider)

    owner = _create_user(pseudonymous=False)
    other = _create_user(pseudonymous=True)
    area_id, category_id = _lookup_ids()
    post_id = _create_post(owner["id"], owner["alias"], area_id, category_id)

    try:
        yield {
            "owner": owner,
            "other": other,
            "post_id": post_id,
            "storage": provider,
            "root": tmp_path / "media",
        }
    finally:
        _delete_user(owner["id"])
        _delete_user(other["id"])


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 24), "red").save(buffer, format="PNG")
    return buffer.getvalue()


def _upload(
    client: TestClient,
    env: dict,
    *,
    data: bytes,
    content_type: str,
    filename: str = "photo.png",
    token: str | None = None,
    owner_key: str | None = None,
):
    form: dict[str, str] = {"post_id": env["post_id"]}
    if owner_key is not None:
        form["owner_key"] = owner_key
    headers = _bearer(token) if token is not None else {}
    return client.post(
        "/api/v1/media",
        files={"file": (filename, data, content_type)},
        data=form,
        headers=headers,
    )


def _upload_png(client: TestClient, env: dict):
    return _upload(
        client,
        env,
        data=_png_bytes(),
        content_type="image/png",
        token=env["owner"]["token"],
    )


def test_upload_image_blurhash_and_signed_url(env: dict, client: TestClient) -> None:
    payload = _png_bytes()
    uploaded = _upload(
        client,
        env,
        data=payload,
        content_type="image/png",
        token=env["owner"]["token"],
    )

    assert uploaded.status_code == 201, uploaded.text
    data = uploaded.json()["data"]
    media_id = data["media_id"]
    assert data["post_id"] == env["post_id"]
    assert data["kind"] == "IMAGE"
    assert data["mime_type"] == "image/png"
    assert data["width"] == 32
    assert data["height"] == 24
    assert data["blur_hash"], "a PNG must get a blurHash"

    files = list(env["root"].rglob("*.png"))
    assert len(files) == 1
    relative_path = files[0].relative_to(env["root"]).as_posix()

    signed = client.get(f"/api/v1/media/{media_id}/signed")
    assert signed.status_code == 200
    url = signed.json()["data"]["url"]
    assert url.startswith(f"/api/v1/media/{media_id}/file?")
    assert "expires=" in url and "sig=" in url

    served = client.get(url)
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.content == payload

    # The storage path is not a route: no static mount exists.
    assert client.get(f"/{relative_path}").status_code == 404


def test_upload_rejects_oversize(env: dict, client: TestClient, monkeypatch) -> None:
    monkeypatch.setattr(media_service, "MAX_UPLOAD_BYTES", 1024)

    response = _upload(
        client,
        env,
        data=b"x" * 2048,
        content_type="image/png",
        token=env["owner"]["token"],
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"


def test_upload_rejects_non_media_type(env: dict, client: TestClient) -> None:
    response = _upload(
        client,
        env,
        data=b"%PDF-1.7",
        content_type="application/pdf",
        filename="doc.pdf",
        token=env["owner"]["token"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_upload_rejects_heic_with_a_clear_error(env: dict, client: TestClient) -> None:
    response = _upload(
        client,
        env,
        data=b"not-really-heic",
        content_type="image/heic",
        filename="photo.heic",
        token=env["owner"]["token"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_upload_rejects_a_fake_image(env: dict, client: TestClient) -> None:
    response = _upload(
        client,
        env,
        data=b"this is not an image",
        content_type="image/png",
        token=env["owner"]["token"],
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_image"


def test_upload_honours_post_ownership(env: dict, client: TestClient) -> None:
    response = _upload(
        client,
        env,
        data=_png_bytes(),
        content_type="image/png",
        token=env["other"]["token"],
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "not_owner"


def test_video_upload_has_no_blurhash(env: dict, client: TestClient) -> None:
    response = _upload(
        client,
        env,
        data=b"\x00" * 256,
        content_type="video/mp4",
        filename="clip.mp4",
        token=env["owner"]["token"],
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["kind"] == "VIDEO"
    assert data["mime_type"] == "video/mp4"
    assert data["blur_hash"] is None


def test_expired_signature_is_rejected(env: dict, client: TestClient) -> None:
    media_id = _upload_png(client, env).json()["data"]["media_id"]

    expired_url = env["storage"].signed_url(media_id, -5)
    response = client.get(expired_url)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_signature"


def test_deleted_media_revokes_its_signed_url(env: dict, client: TestClient) -> None:
    media_id = _upload_png(client, env).json()["data"]["media_id"]
    url = client.get(f"/api/v1/media/{media_id}/signed").json()["data"]["url"]

    _delete_media(media_id)

    assert client.get(url).status_code == 404
    assert client.get(f"/api/v1/media/{media_id}/signed").status_code == 404
