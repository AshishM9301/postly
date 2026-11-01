"""Comments: creation, depth, threads, ownership, ghost keys and votes."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Iterator
from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.security import hash_session_token, new_session_token, utcnow
from app.main import app
from fastapi.testclient import TestClient
from prisma import Prisma
from prisma.enums import ModerationState, PostStatus

TITLE_PREFIX = "T018:"


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
            alias = f"T018_{uuid4().hex[:10]}"
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
                raise RuntimeError("seed areas and categories before comment tests")
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
                    "title": f"{TITLE_PREFIX} thread",
                    "body": f"{TITLE_PREFIX} body",
                    "status": PostStatus.OPEN,
                    "moderationState": ModerationState.CLEAN,
                }
            )
            return post.id
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _cleanup(post_id: str, user_ids: list[str]) -> None:
    async def run() -> None:
        db = Prisma()
        await db.connect()
        try:
            comments = await db.comment.find_many(where={"postId": post_id})
            target_ids = [post_id] + [comment.id for comment in comments]
            await db.vote.delete_many(where={"targetId": {"in": target_ids}})
            await db.post.delete_many(where={"id": post_id})
            await db.user.delete_many(where={"id": {"in": user_ids}})
        finally:
            await db.disconnect()

    asyncio.run(run())


def _comment_row(comment_id: str):
    async def run():
        db = Prisma()
        await db.connect()
        try:
            return await db.comment.find_unique(where={"id": comment_id})
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _post_comment_count(post_id: str) -> int:
    async def run() -> int:
        db = Prisma()
        await db.connect()
        try:
            post = await db.post.find_unique(where={"id": post_id})
            assert post is not None
            return post.commentCount
        finally:
            await db.disconnect()

    return asyncio.run(run())


@pytest.fixture()
def env(client: TestClient) -> Iterator[dict]:
    alice = _create_user(pseudonymous=False)
    bob = _create_user(pseudonymous=True)
    area_id, category_id = _lookup_ids()
    post_id = _create_post(alice["id"], alice["alias"], area_id, category_id)

    try:
        yield {"alice": alice, "bob": bob, "post_id": post_id}
    finally:
        _cleanup(post_id, [alice["id"], bob["id"]])


def _comment(
    client: TestClient,
    env: dict,
    *,
    who: str = "alice",
    body: str = "T018: comment",
    parent_id: str | None = None,
    comment_id: str | None = None,
    alias: str | None = None,
    owner_key: str | None = None,
):
    headers = {} if who == "ghost" else _bearer(env[who]["token"])
    payload: dict[str, object] = {"body": body}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    if comment_id is not None:
        payload["id"] = comment_id
    if alias is not None:
        payload["alias"] = alias
    if owner_key is not None:
        payload["owner_key"] = owner_key
    return client.post(f"/api/v1/posts/{env['post_id']}/comments", json=payload, headers=headers)


def _thread(client: TestClient, env: dict, **params: object):
    return client.get(f"/api/v1/posts/{env['post_id']}/comments", params=params)


def test_create_top_level_comment_and_count(env: dict, client: TestClient) -> None:
    response = _comment(client, env, body="T018: first")

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["post_id"] == env["post_id"]
    assert data["parent_id"] is None
    assert data["depth"] == 0
    assert data["author"]["id"] == env["alice"]["id"]
    assert data["alias"] == env["alice"]["alias"]
    assert data["upvote_count"] == 0
    assert _post_comment_count(env["post_id"]) == 1


def test_replies_stop_at_depth_three(env: dict, client: TestClient) -> None:
    root = _comment(client, env, body="root").json()["data"]
    depth_one = _comment(client, env, body="one", parent_id=root["id"]).json()["data"]
    depth_two = _comment(client, env, body="two", parent_id=depth_one["id"]).json()["data"]
    depth_three = _comment(client, env, body="three", parent_id=depth_two["id"]).json()["data"]

    assert (root["depth"], depth_one["depth"], depth_two["depth"], depth_three["depth"]) == (
        0,
        1,
        2,
        3,
    )

    too_deep = _comment(client, env, body="four", parent_id=depth_three["id"])
    assert too_deep.status_code == 422
    assert too_deep.json()["error"]["code"] == "max_depth_exceeded"
    assert _post_comment_count(env["post_id"]) == 4


def test_thread_is_oldest_last_and_paginated(env: dict, client: TestClient) -> None:
    created: list[str] = []
    for index in range(3):
        response = _comment(client, env, body=f"T018: comment {index}")
        created.append(response.json()["data"]["id"])
        time.sleep(0.01)

    first = _thread(client, env, limit=2)
    assert first.status_code == 200
    first_body = first.json()
    assert [row["id"] for row in first_body["data"]] == created[:2]
    assert first_body["meta"]["has_more"] is True
    assert first_body["meta"]["cursor"] == created[1]

    second = _thread(client, env, limit=2, cursor=first_body["meta"]["cursor"])
    assert second.status_code == 200
    second_body = second.json()
    assert [row["id"] for row in second_body["data"]] == created[2:]
    assert second_body["meta"]["has_more"] is False
    assert second_body["meta"]["cursor"] is None


def test_reply_exposes_parent_and_depth(env: dict, client: TestClient) -> None:
    root_id = _comment(client, env, body="root").json()["data"]["id"]
    reply = _comment(client, env, body="reply", parent_id=root_id)

    assert reply.status_code == 201
    assert reply.json()["data"]["parent_id"] == root_id
    assert reply.json()["data"]["depth"] == 1

    thread = _thread(client, env).json()["data"]
    assert [row["id"] for row in thread] == [root_id, reply.json()["data"]["id"]]


def test_ghost_comment_stores_key_and_never_leaks_it(env: dict, client: TestClient) -> None:
    comment_id = str(uuid4())
    response = _comment(
        client,
        env,
        who="ghost",
        body="T018: ghost",
        comment_id=comment_id,
        alias="Neighbor_gh0st",
        owner_key="comment-owner-key",
    )

    assert response.status_code == 201, response.text
    assert "comment-owner-key" not in response.text
    assert "ghostOwnerKey" not in response.text
    data = response.json()["data"]
    assert data["id"] == comment_id
    assert data["author"] is None
    assert data["alias"] == "Neighbor_gh0st"

    row = _comment_row(comment_id)
    assert row is not None
    assert row.authorId is None
    assert row.ghostOwnerKey == "comment-owner-key"


def test_edit_is_author_only(env: dict, client: TestClient) -> None:
    comment_id = _comment(client, env).json()["data"]["id"]

    edited = client.patch(
        f"/api/v1/comments/{comment_id}",
        json={"body": "T018: edited"},
        headers=_bearer(env["alice"]["token"]),
    )
    assert edited.status_code == 200
    assert edited.json()["data"]["body"] == "T018: edited"

    other = client.patch(
        f"/api/v1/comments/{comment_id}",
        json={"body": "T018: hijack"},
        headers=_bearer(env["bob"]["token"]),
    )
    assert other.status_code == 403
    assert other.json()["error"]["code"] == "not_owner"


def test_ghost_edit_and_delete_need_the_owner_key(env: dict, client: TestClient) -> None:
    comment_id = _comment(
        client,
        env,
        who="ghost",
        comment_id=str(uuid4()),
        alias="Neighbor_gh0st",
        owner_key="comment-owner-key",
    ).json()["data"]["id"]

    missing_edit = client.patch(f"/api/v1/comments/{comment_id}", json={"body": "T018: nope"})
    assert missing_edit.status_code == 403

    wrong_delete = client.request(
        "DELETE", f"/api/v1/comments/{comment_id}", json={"owner_key": "wrong"}
    )
    assert wrong_delete.status_code == 403

    right_edit = client.request(
        "PATCH",
        f"/api/v1/comments/{comment_id}",
        json={"body": "T018: ghost edit", "owner_key": "comment-owner-key"},
    )
    assert right_edit.status_code == 200
    assert right_edit.json()["data"]["body"] == "T018: ghost edit"

    right_delete = client.request(
        "DELETE",
        f"/api/v1/comments/{comment_id}",
        json={"owner_key": "comment-owner-key"},
    )
    assert right_delete.status_code == 204
    assert _comment_row(comment_id) is None


def test_delete_keeps_replies_as_top_level(env: dict, client: TestClient) -> None:
    root_id = _comment(client, env, body="root").json()["data"]["id"]
    reply_id = _comment(client, env, body="reply", parent_id=root_id).json()["data"]["id"]
    nested_id = _comment(client, env, body="nested", parent_id=reply_id).json()["data"]["id"]
    assert _post_comment_count(env["post_id"]) == 3

    other = client.request(
        "DELETE",
        f"/api/v1/comments/{root_id}",
        headers=_bearer(env["bob"]["token"]),
    )
    assert other.status_code == 403

    deleted = client.request(
        "DELETE",
        f"/api/v1/comments/{root_id}",
        headers=_bearer(env["alice"]["token"]),
    )
    assert deleted.status_code == 204
    assert _comment_row(root_id) is None
    assert _post_comment_count(env["post_id"]) == 2

    thread = _thread(client, env).json()["data"]
    by_id = {row["id"]: row for row in thread}
    assert by_id[reply_id]["parent_id"] is None
    assert by_id[reply_id]["depth"] == 0
    assert by_id[nested_id]["parent_id"] == reply_id
    assert by_id[nested_id]["depth"] == 1


def test_comment_votes_use_the_comment_counters(env: dict, client: TestClient) -> None:
    comment_id = _comment(client, env).json()["data"]["id"]

    voted = client.put(
        f"/api/v1/votes/COMMENT/{comment_id}",
        json={"value": 1},
        headers=_bearer(env["alice"]["token"]),
    )
    assert voted.status_code == 200
    assert voted.json()["data"]["upvote_count"] == 1

    thread = _thread(client, env).json()["data"]
    row = next(item for item in thread if item["id"] == comment_id)
    assert row["upvote_count"] == 1
    assert row["downvote_count"] == 0


def test_unknown_post_parent_and_cursor(env: dict, client: TestClient) -> None:
    missing_post = client.get(f"/api/v1/posts/{uuid4()}/comments")
    assert missing_post.status_code == 404

    missing_parent = _comment(client, env, parent_id=str(uuid4()))
    assert missing_parent.status_code == 404
    assert missing_parent.json()["error"]["code"] == "comment_not_found"

    bad_cursor = _thread(client, env, cursor=str(uuid4()))
    assert bad_cursor.status_code == 422
    assert bad_cursor.json()["error"]["code"] == "validation_error"
