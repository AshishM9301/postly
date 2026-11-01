"""Votes: one per key, flipping, counters and ghost-session isolation."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
from collections.abc import Iterator
from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.security import hash_session_token, new_session_token, utcnow
from app.main import app
from fastapi.testclient import TestClient
from prisma import Prisma
from prisma.enums import ModerationState, PostStatus

TITLE_PREFIX = "T017:"


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
            alias = f"T017_{uuid4().hex[:10]}"
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
                raise RuntimeError("seed areas and categories before vote tests")
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
                    "title": f"{TITLE_PREFIX} vote target",
                    "body": f"{TITLE_PREFIX} body",
                    "status": PostStatus.OPEN,
                    "moderationState": ModerationState.CLEAN,
                }
            )
            return post.id
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _create_comment(post_id: str, user_id: str, alias: str) -> str:
    async def run() -> str:
        db = Prisma()
        await db.connect()
        try:
            comment = await db.comment.create(
                data={
                    "postId": post_id,
                    "authorId": user_id,
                    "alias": alias,
                    "body": f"{TITLE_PREFIX} comment",
                    "moderationState": ModerationState.CLEAN,
                }
            )
            return comment.id
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _cleanup(target_ids: list[str], user_ids: list[str]) -> None:
    async def run() -> None:
        db = Prisma()
        await db.connect()
        try:
            await db.vote.delete_many(where={"targetId": {"in": target_ids}})
            await db.user.delete_many(where={"id": {"in": user_ids}})
        finally:
            await db.disconnect()

    asyncio.run(run())


def _post_counters(post_id: str) -> tuple[int, int]:
    async def run() -> tuple[int, int]:
        db = Prisma()
        await db.connect()
        try:
            post = await db.post.find_unique(where={"id": post_id})
            assert post is not None
            return post.upvoteCount, post.downvoteCount
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _comment_counters(comment_id: str) -> tuple[int, int]:
    async def run() -> tuple[int, int]:
        db = Prisma()
        await db.connect()
        try:
            comment = await db.comment.find_unique(where={"id": comment_id})
            assert comment is not None
            return comment.upvoteCount, comment.downvoteCount
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _vote_rows(target_id: str) -> int:
    async def run() -> int:
        db = Prisma()
        await db.connect()
        try:
            return await db.vote.count(where={"targetId": target_id})
        finally:
            await db.disconnect()

    return asyncio.run(run())


@pytest.fixture()
def env(client: TestClient) -> Iterator[dict]:
    alice = _create_user(pseudonymous=False)
    bob = _create_user(pseudonymous=True)
    area_id, category_id = _lookup_ids()
    post_id = _create_post(alice["id"], alice["alias"], area_id, category_id)
    comment_id = _create_comment(post_id, alice["id"], alice["alias"])

    try:
        yield {
            "alice": alice,
            "bob": bob,
            "post_id": post_id,
            "comment_id": comment_id,
        }
    finally:
        _cleanup([post_id, comment_id], [alice["id"], bob["id"]])


def _ghost_key(target_id: str, salt: str) -> str:
    digest = hmac.new(salt.encode(), target_id.encode(), hashlib.sha256).digest()
    return "a:" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


def _put(
    client: TestClient,
    env: dict,
    target_type: str,
    target_id: str,
    value: int,
    *,
    who: str = "alice",
    voter_key: str | None = None,
):
    headers = {} if who == "ghost" else _bearer(env[who]["token"])
    body: dict[str, object] = {"value": value}
    if voter_key is not None:
        body["voter_key"] = voter_key
    return client.put(f"/api/v1/votes/{target_type}/{target_id}", json=body, headers=headers)


def _delete(
    client: TestClient,
    env: dict,
    target_type: str,
    target_id: str,
    *,
    who: str = "alice",
    voter_key: str | None = None,
):
    headers = {} if who == "ghost" else _bearer(env[who]["token"])
    kwargs: dict[str, object] = {"headers": headers}
    if voter_key is not None:
        kwargs["json"] = {"voter_key": voter_key}
    return client.request("DELETE", f"/api/v1/votes/{target_type}/{target_id}", **kwargs)


def test_vote_creates_and_returns_counters(env: dict, client: TestClient) -> None:
    response = _put(client, env, "POST", env["post_id"], 1)

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["target_type"] == "POST"
    assert data["target_id"] == env["post_id"]
    assert data["value"] == 1
    assert data["upvote_count"] == 1
    assert data["downvote_count"] == 0
    assert _post_counters(env["post_id"]) == (1, 0)


def test_repeat_vote_flips_without_double_counting(env: dict, client: TestClient) -> None:
    _put(client, env, "POST", env["post_id"], 1)
    flipped = _put(client, env, "POST", env["post_id"], -1)

    assert flipped.status_code == 200
    data = flipped.json()["data"]
    assert data["value"] == -1
    assert data["upvote_count"] == 0
    assert data["downvote_count"] == 1
    assert _vote_rows(env["post_id"]) == 1
    assert _post_counters(env["post_id"]) == (0, 1)


def test_delete_vote_restores_counters(env: dict, client: TestClient) -> None:
    _put(client, env, "POST", env["post_id"], 1)

    removed = _delete(client, env, "POST", env["post_id"])

    assert removed.status_code == 200
    data = removed.json()["data"]
    assert data["value"] is None
    assert data["upvote_count"] == 0
    assert data["downvote_count"] == 0
    assert _vote_rows(env["post_id"]) == 0
    assert _post_counters(env["post_id"]) == (0, 0)

    again = _delete(client, env, "POST", env["post_id"])
    assert again.status_code == 200
    assert again.json()["data"]["value"] is None


def test_two_users_have_independent_votes(env: dict, client: TestClient) -> None:
    _put(client, env, "POST", env["post_id"], 1)
    second = _put(client, env, "POST", env["post_id"], 1, who="bob")
    assert second.json()["data"]["upvote_count"] == 2

    flip = _put(client, env, "POST", env["post_id"], -1)
    assert flip.json()["data"]["upvote_count"] == 1
    assert flip.json()["data"]["downvote_count"] == 1
    assert _vote_rows(env["post_id"]) == 2
    assert _post_counters(env["post_id"]) == (1, 1)


def test_ghost_sessions_are_independent_per_target(env: dict, client: TestClient) -> None:
    alice_key = _ghost_key(env["post_id"], "session-a")
    bob_key = _ghost_key(env["post_id"], "session-b")

    first = _put(client, env, "POST", env["post_id"], 1, who="ghost", voter_key=alice_key)
    assert first.json()["data"]["upvote_count"] == 1

    flipped = _put(client, env, "POST", env["post_id"], -1, who="ghost", voter_key=alice_key)
    assert flipped.json()["data"]["upvote_count"] == 0
    assert flipped.json()["data"]["downvote_count"] == 1
    assert _vote_rows(env["post_id"]) == 1

    second = _put(client, env, "POST", env["post_id"], 1, who="ghost", voter_key=bob_key)
    assert second.json()["data"]["upvote_count"] == 1
    assert second.json()["data"]["downvote_count"] == 1
    assert _vote_rows(env["post_id"]) == 2


def test_ghost_must_send_a_salted_voter_key(env: dict, client: TestClient) -> None:
    missing = _put(client, env, "POST", env["post_id"], 1, who="ghost")
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "voter_key_required"

    impersonating = _put(client, env, "POST", env["post_id"], 1, who="ghost", voter_key="u:someone")
    assert impersonating.status_code == 422
    assert impersonating.json()["error"]["code"] == "validation_error"

    short = _put(client, env, "POST", env["post_id"], 1, who="ghost", voter_key="a:short")
    assert short.status_code == 422


def test_comment_vote_uses_the_comment_counters(env: dict, client: TestClient) -> None:
    response = _put(client, env, "COMMENT", env["comment_id"], 1)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["target_type"] == "COMMENT"
    assert data["target_id"] == env["comment_id"]
    assert data["upvote_count"] == 1
    assert data["downvote_count"] == 0
    assert _comment_counters(env["comment_id"]) == (1, 0)
    assert _post_counters(env["post_id"]) == (0, 0)


def test_unknown_targets_and_invalid_types(env: dict, client: TestClient) -> None:
    missing_post = _put(client, env, "POST", str(uuid4()), 1)
    assert missing_post.status_code == 404
    assert missing_post.json()["error"]["code"] == "post_not_found"

    missing_comment = _put(client, env, "COMMENT", str(uuid4()), 1)
    assert missing_comment.status_code == 404
    assert missing_comment.json()["error"]["code"] == "comment_not_found"

    bad_type = _put(client, env, "LIKE", env["post_id"], 1)
    assert bad_type.status_code == 422

    blame = _put(client, env, "BLAME", env["post_id"], 1)
    assert blame.status_code == 422
    assert "T-050" in blame.json()["error"]["message"]

    bad_value = _put(client, env, "POST", env["post_id"], 2)
    assert bad_value.status_code == 422
