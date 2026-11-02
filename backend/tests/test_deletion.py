"""Hard-deletion flows: post cascade, account cascade, ghost purge, removal request."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import io
from collections.abc import Awaitable, Callable, Iterator
from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.security import hash_secret, hash_session_token, new_session_token, utcnow
from app.main import app
from app.providers.storage.local import LocalStorageProvider
from app.services import media as media_service
from fastapi.testclient import TestClient
from PIL import Image
from prisma import Prisma
from prisma.enums import ModerationState, PostStatus, ReportStatus, VoteTarget
from prisma.fields import Json

TITLE_PREFIX = "T021:"
SESSION_SECRET = bytes(range(32))
SESSION_KEY = base64.urlsafe_b64encode(SESSION_SECRET).rstrip(b"=").decode("ascii")
OTHER_SECRET = bytes(range(32, 64))
OTHER_KEY = base64.urlsafe_b64encode(OTHER_SECRET).rstrip(b"=").decode("ascii")


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _with_db[T](operation: Callable[[Prisma], Awaitable[T]]) -> T:
    db = Prisma()
    await db.connect()
    try:
        return await operation(db)
    finally:
        await db.disconnect()


def _db[T](operation: Callable[[Prisma], Awaitable[T]]) -> T:
    return asyncio.run(_with_db(operation))


def _create_user(pseudonymous: bool, secret: str | None = None) -> dict[str, str | None]:
    async def run(db: Prisma) -> dict[str, str | None]:
        alias = f"T021_{uuid4().hex[:10]}"
        data: dict[str, object] = {"alias": alias, "isPseudonymous": pseudonymous}
        if secret is not None:
            data["secretHash"] = hash_secret(secret)
        user = await db.user.create(data=data)
        token = new_session_token()
        session = await db.session.create(
            data={
                "userId": user.id,
                "tokenHash": hash_session_token(token),
                "expiresAt": utcnow() + timedelta(hours=1),
            }
        )
        return {
            "id": user.id,
            "alias": alias,
            "token": token,
            "secret": secret,
            "session_id": session.id,
        }

    return _db(run)


def _lookup_ids() -> tuple[str, str]:
    async def run(db: Prisma) -> tuple[str, str]:
        area = await db.area.find_unique(where={"pincode": "110019"})
        category = await db.category.find_unique(where={"slug": "pothole"})
        if area is None or category is None:
            raise RuntimeError("seed areas and categories before deletion tests")
        return area.id, category.id

    return _db(run)


def _title(suffix: str) -> str:
    return f"{TITLE_PREFIX} {suffix} {uuid4().hex[:8]}"


def _create_post(
    author_id: str | None,
    alias: str,
    area_id: str,
    category_id: str,
    *,
    suffix: str = "post",
    ghost_owner_key: str | None = None,
) -> str:
    async def run(db: Prisma) -> str:
        post = await db.post.create(
            data={
                "authorId": author_id,
                "ghostOwnerKey": ghost_owner_key,
                "alias": alias,
                "isAnonymous": author_id is None,
                "areaId": area_id,
                "categoryId": category_id,
                "title": _title(suffix),
                "body": _title(f"{suffix} body"),
                "status": PostStatus.OPEN,
                "moderationState": ModerationState.CLEAN,
            }
        )
        return post.id

    return _db(run)


def _create_comment(
    post_id: str,
    author_id: str | None,
    alias: str,
    *,
    parent_id: str | None = None,
    depth: int = 0,
    ghost_owner_key: str | None = None,
) -> str:
    async def run(db: Prisma) -> str:
        comment = await db.comment.create(
            data={
                "postId": post_id,
                "authorId": author_id,
                "ghostOwnerKey": ghost_owner_key,
                "alias": alias,
                "body": _title("comment"),
                "parentId": parent_id,
                "depth": depth,
                "moderationState": ModerationState.CLEAN,
            }
        )
        return comment.id

    return _db(run)


def _create_vote(
    target_type: str,
    target_id: str,
    *,
    voter_id: str | None,
    voter_key: str,
    value: int = 1,
) -> None:
    async def run(db: Prisma) -> None:
        await db.vote.create(
            data={
                "targetType": VoteTarget(target_type),
                "targetId": target_id,
                "voterId": voter_id,
                "voterKey": voter_key,
                "value": value,
            }
        )

    _db(run)


def _create_reveal(user_id: str, target_type: str, target_id: str) -> None:
    async def run(db: Prisma) -> None:
        await db.userreveal.create(
            data={"userId": user_id, "targetType": target_type, "targetId": target_id}
        )

    _db(run)


def _create_report(
    target_type: str,
    target_id: str,
    *,
    reporter_id: str | None = None,
    reason: str = "spam",
) -> None:
    async def run(db: Prisma) -> None:
        await db.report.create(
            data={
                "targetType": target_type,
                "targetId": target_id,
                "reporterId": reporter_id,
                "reason": reason,
                "status": ReportStatus.OPEN,
            }
        )

    _db(run)


def _create_view(post_id: str, viewer_key: str) -> None:
    async def run(db: Prisma) -> None:
        await db.postview.create(data={"postId": post_id, "viewerKey": viewer_key})

    _db(run)


def _create_follow(follower_id: str, following_id: str) -> None:
    async def run(db: Prisma) -> None:
        await db.follow.create(data={"followerId": follower_id, "followingId": following_id})

    _db(run)


def _create_area_follow(user_id: str, area_id: str) -> None:
    async def run(db: Prisma) -> None:
        await db.areafollow.create(data={"userId": user_id, "areaId": area_id})

    _db(run)


def _create_notification(user_id: str) -> None:
    async def run(db: Prisma) -> None:
        await db.notification.create(
            data={"userId": user_id, "type": "test", "payload": Json({"test": True})}
        )

    _db(run)


def _create_push_subscription(user_id: str) -> None:
    async def run(db: Prisma) -> None:
        await db.pushsubscription.create(
            data={
                "userId": user_id,
                "endpoint": f"https://push.example/{uuid4().hex}",
                "p256dh": "p256dh",
                "auth": "auth",
            }
        )

    _db(run)


def _fetch(model: str, where: dict):
    async def run(db: Prisma):
        return await getattr(db, model).find_unique(where=where)

    return _db(run)


def _count(model: str, where: dict) -> int:
    async def run(db: Prisma) -> int:
        return await getattr(db, model).count(where=where)

    return _db(run)


def _cleanup(user_ids: list[str]) -> None:
    async def run(db: Prisma) -> None:
        posts = await db.post.find_many(where={"title": {"startswith": TITLE_PREFIX}})
        post_ids = [post.id for post in posts]
        comments = (
            await db.comment.find_many(where={"postId": {"in": post_ids}}) if post_ids else []
        )
        target_ids = post_ids + [comment.id for comment in comments]

        if target_ids:
            await db.vote.delete_many(where={"targetId": {"in": target_ids}})
            await db.userreveal.delete_many(where={"targetId": {"in": target_ids}})
            await db.report.delete_many(where={"targetId": {"in": target_ids}})
        if post_ids:
            await db.post.delete_many(where={"id": {"in": post_ids}})
        if user_ids:
            await db.user.delete_many(where={"id": {"in": user_ids}})

    _db(run)


@pytest.fixture()
def env(tmp_path, monkeypatch, client: TestClient) -> Iterator[dict]:
    provider = LocalStorageProvider(tmp_path / "media")
    monkeypatch.setattr(media_service, "storage", provider)

    google = _create_user(pseudonymous=False)
    pseudo = _create_user(pseudonymous=True, secret="pseudo-secret-" + "x" * 40)
    other = _create_user(pseudonymous=False)
    area_id, category_id = _lookup_ids()

    try:
        yield {
            "google": google,
            "pseudo": pseudo,
            "other": other,
            "area_id": area_id,
            "category_id": category_id,
            "root": tmp_path / "media",
        }
    finally:
        _cleanup([google["id"], pseudo["id"], other["id"]])


def _png_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


def _upload_image(client: TestClient, post_id: str, token: str) -> str:
    response = client.post(
        "/api/v1/media",
        files={"file": ("photo.png", _png_bytes(), "image/png")},
        data={"post_id": post_id},
        headers=_bearer(token),
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["media_id"]


def _feed_ids(client: TestClient, tab: str) -> set[str]:
    response = client.get(f"/api/v1/feed/{tab}", params={"limit": 50})
    assert response.status_code == 200, response.text
    return {post["id"] for post in response.json()["data"]}


def _ghost_owner(secret: bytes, target_id: str) -> str:
    digest = hmac.new(secret, target_id.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _ghost_voter(secret: bytes, target_id: str) -> str:
    return f"a:{_ghost_owner(secret, target_id)}"


def _ghost_post(client: TestClient, env: dict, post_id: str, secret: bytes) -> None:
    response = client.post(
        "/api/v1/posts",
        json={
            "id": post_id,
            "title": _title("ghost post"),
            "body": _title("ghost body"),
            "area_id": env["area_id"],
            "category_id": env["category_id"],
            "alias": "Neighbor_gh0st",
            "owner_key": _ghost_owner(secret, post_id),
        },
    )
    assert response.status_code == 201, response.text


def test_delete_post_removes_rows_and_media_files(env: dict, client: TestClient) -> None:
    owner = env["google"]
    other = env["other"]
    post_id = _create_post(owner["id"], owner["alias"], env["area_id"], env["category_id"])
    media_id = _upload_image(client, post_id, owner["token"])
    media = _fetch("media", {"id": media_id})
    assert media is not None
    file_path = env["root"] / media.path

    comment_id = _create_comment(post_id, other["id"], other["alias"])
    _create_vote("POST", post_id, voter_id=owner["id"], voter_key=f"u:{owner['id']}")
    _create_vote(
        "COMMENT",
        comment_id,
        voter_id=other["id"],
        voter_key=f"u:{other['id']}",
    )
    _create_reveal(owner["id"], "POST", post_id)
    _create_reveal(owner["id"], "COMMENT", comment_id)
    _create_report("POST", post_id, reporter_id=other["id"])
    _create_view(post_id, f"u:{owner['id']}")

    assert file_path.exists()

    response = client.request("DELETE", f"/api/v1/posts/{post_id}", headers=_bearer(owner["token"]))

    assert response.status_code == 204, response.text
    assert _fetch("post", {"id": post_id}) is None
    assert _count("media", {"postId": post_id}) == 0
    assert _count("comment", {"postId": post_id}) == 0
    assert _count("vote", {"targetId": post_id}) == 0
    assert _count("vote", {"targetId": comment_id}) == 0
    assert _count("userreveal", {"targetId": post_id}) == 0
    assert _count("userreveal", {"targetId": comment_id}) == 0
    assert _count("report", {"targetId": post_id}) == 0
    assert _count("postview", {"postId": post_id}) == 0
    assert not file_path.exists()


def test_delete_account_removes_content_and_related_rows(env: dict, client: TestClient) -> None:
    owner = env["google"]
    other = env["other"]

    post_id = _create_post(owner["id"], owner["alias"], env["area_id"], env["category_id"])
    media_id = _upload_image(client, post_id, owner["token"])
    media = _fetch("media", {"id": media_id})
    assert media is not None
    file_path = env["root"] / media.path

    other_post_id = _create_post(other["id"], other["alias"], env["area_id"], env["category_id"])
    own_comment = client.post(
        f"/api/v1/posts/{other_post_id}/comments",
        json={"body": _title("user comment")},
        headers=_bearer(owner["token"]),
    )
    assert own_comment.status_code == 201, own_comment.text
    comment_id = own_comment.json()["data"]["id"]

    reply = client.post(
        f"/api/v1/posts/{other_post_id}/comments",
        json={"body": _title("reply"), "parent_id": comment_id},
        headers=_bearer(other["token"]),
    )
    assert reply.status_code == 201, reply.text
    reply_id = reply.json()["data"]["id"]

    _create_vote(
        "POST",
        other_post_id,
        voter_id=owner["id"],
        voter_key=f"u:{owner['id']}",
    )
    _create_reveal(owner["id"], "POST", other_post_id)
    _create_follow(owner["id"], other["id"])
    _create_area_follow(owner["id"], env["area_id"])
    _create_notification(owner["id"])
    _create_push_subscription(owner["id"])

    assert post_id in _feed_ids(client, "new")

    response = client.request("DELETE", "/api/v1/me", headers=_bearer(owner["token"]))

    assert response.status_code == 204, response.text
    assert _fetch("user", {"id": owner["id"]}) is None
    assert _fetch("session", {"id": owner["session_id"]}) is None
    assert _fetch("post", {"id": post_id}) is None
    assert _fetch("media", {"id": media_id}) is None
    assert not file_path.exists()
    assert _fetch("comment", {"id": comment_id}) is None
    assert _fetch("post", {"id": other_post_id}) is not None

    promoted = _fetch("comment", {"id": reply_id})
    assert promoted is not None
    assert promoted.parentId is None
    assert promoted.depth == 0

    assert _count("vote", {"voterId": owner["id"]}) == 0
    assert _count("follow", {"followerId": owner["id"]}) == 0
    assert _count("areafollow", {"userId": owner["id"]}) == 0
    assert _count("userreveal", {"userId": owner["id"]}) == 0
    assert _count("notification", {"userId": owner["id"]}) == 0
    assert _count("pushsubscription", {"userId": owner["id"]}) == 0

    assert post_id not in _feed_ids(client, "new")
    assert post_id not in _feed_ids(client, "trending")


def test_pseudonymous_account_deletion_requires_the_secret(env: dict, client: TestClient) -> None:
    pseudo = env["pseudo"]
    post_id = _create_post(pseudo["id"], pseudo["alias"], env["area_id"], env["category_id"])

    missing = client.request("DELETE", "/api/v1/me", headers=_bearer(pseudo["token"]))
    assert missing.status_code == 403
    assert missing.json()["error"]["code"] == "invalid_secret"

    wrong = client.request(
        "DELETE",
        "/api/v1/me",
        headers=_bearer(pseudo["token"]),
        json={"secret": "wrong-" + "x" * 40},
    )
    assert wrong.status_code == 403
    assert wrong.json()["error"]["code"] == "invalid_secret"
    assert _fetch("user", {"id": pseudo["id"]}) is not None
    assert _fetch("post", {"id": post_id}) is not None

    right = client.request(
        "DELETE",
        "/api/v1/me",
        headers=_bearer(pseudo["token"]),
        json={"secret": pseudo["secret"]},
    )
    assert right.status_code == 204, right.text
    assert _fetch("user", {"id": pseudo["id"]}) is None
    assert _fetch("post", {"id": post_id}) is None


def test_ghost_purge_deletes_only_its_own_session(env: dict, client: TestClient) -> None:
    other = env["other"]
    target_post_id = _create_post(other["id"], other["alias"], env["area_id"], env["category_id"])

    ghost_post_id = str(uuid4())
    _ghost_post(client, env, ghost_post_id, SESSION_SECRET)

    other_post_id = str(uuid4())
    _ghost_post(client, env, other_post_id, OTHER_SECRET)

    ghost_comment_id = str(uuid4())
    ghost_comment = client.post(
        f"/api/v1/posts/{target_post_id}/comments",
        json={
            "id": ghost_comment_id,
            "body": _title("ghost comment"),
            "alias": "Neighbor_gh0st",
            "owner_key": _ghost_owner(SESSION_SECRET, ghost_comment_id),
        },
    )
    assert ghost_comment.status_code == 201, ghost_comment.text

    other_comment_id = str(uuid4())
    other_comment = client.post(
        f"/api/v1/posts/{target_post_id}/comments",
        json={
            "id": other_comment_id,
            "body": _title("other ghost comment"),
            "alias": "Neighbor_gh0st",
            "owner_key": _ghost_owner(OTHER_SECRET, other_comment_id),
        },
    )
    assert other_comment.status_code == 201, other_comment.text

    reply = client.post(
        f"/api/v1/posts/{target_post_id}/comments",
        json={"body": _title("public reply"), "parent_id": ghost_comment_id},
        headers=_bearer(other["token"]),
    )
    assert reply.status_code == 201, reply.text
    reply_id = reply.json()["data"]["id"]

    own_vote = client.put(
        f"/api/v1/votes/POST/{target_post_id}",
        json={"value": 1, "voter_key": _ghost_voter(SESSION_SECRET, target_post_id)},
    )
    assert own_vote.status_code == 200, own_vote.text
    other_vote = client.put(
        f"/api/v1/votes/POST/{target_post_id}",
        json={"value": 1, "voter_key": _ghost_voter(OTHER_SECRET, target_post_id)},
    )
    assert other_vote.status_code == 200, other_vote.text

    invalid = client.post("/api/v1/ghost/purge", json={"session_key": "not-a-session-key"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "validation_error"

    response = client.post("/api/v1/ghost/purge", json={"session_key": SESSION_KEY})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data == {"posts": 1, "comments": 1, "votes": 1}

    assert _fetch("post", {"id": ghost_post_id}) is None
    assert _fetch("post", {"id": other_post_id}) is not None
    assert _fetch("post", {"id": target_post_id}) is not None
    assert _fetch("comment", {"id": ghost_comment_id}) is None
    assert _fetch("comment", {"id": other_comment_id}) is not None
    assert _count("vote", {"targetId": target_post_id}) == 1

    promoted = _fetch("comment", {"id": reply_id})
    assert promoted is not None
    assert promoted.parentId is None
    assert promoted.depth == 0


def test_removal_request_is_anonymous_and_left_for_a_moderator(
    env: dict, client: TestClient
) -> None:
    owner = env["other"]
    post_id = _create_post(owner["id"], owner["alias"], env["area_id"], env["category_id"])

    response = client.post(
        f"/api/v1/posts/{post_id}/removal-request",
        json={"details": "I lost my ghost key. Original wording: broken streetlight."},
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["target_type"] == "POST"
    assert data["target_id"] == post_id
    assert data["status"] == "OPEN"

    report = _fetch("report", {"id": data["id"]})
    assert report is not None
    assert report.reason == "removal_request"
    assert report.reporterId is None
    assert report.status == ReportStatus.OPEN

    # The post stays up until a human acts on the request.
    assert _fetch("post", {"id": post_id}) is not None

    by_user = client.post(
        f"/api/v1/posts/{post_id}/removal-request",
        json={"details": "Original wording, timestamp and photo description."},
        headers=_bearer(owner["token"]),
    )
    assert by_user.status_code == 201
    assert _fetch("report", {"id": by_user.json()["data"]["id"]}).reporterId == owner["id"]

    missing = client.post(
        f"/api/v1/posts/{uuid4()}/removal-request",
        json={"details": "This target does not exist."},
    )
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "post_not_found"
