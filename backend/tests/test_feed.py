"""Feed tabs: ordering, personalisation, nearby, filters and pagination."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from app.core.security import hash_session_token, new_session_token, utcnow
from app.main import app
from fastapi.testclient import TestClient
from prisma import Prisma
from prisma.enums import ModerationState, PostStatus

PREFIX = "T019:"
AREA_A = "019001"
AREA_B = "019002"
CAT_MAIN = "t019-feed"
CAT_OTHER = "t019-other"


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _create_world() -> dict:
    async def run() -> dict:
        db = Prisma()
        await db.connect()
        try:
            # Idempotent setup: wipe a previous failed run first.
            old = await db.post.find_many(where={"title": {"startswith": PREFIX}})
            old_ids = [post.id for post in old]
            if old_ids:
                await db.vote.delete_many(where={"targetId": {"in": old_ids}})
            await db.post.delete_many(where={"title": {"startswith": PREFIX}})
            await db.user.delete_many(where={"alias": {"startswith": "T019_"}})
            await db.area.delete_many(where={"pincode": {"in": [AREA_A, AREA_B]}})
            await db.category.delete_many(where={"slug": {"in": [CAT_MAIN, CAT_OTHER]}})

            area_a = await db.area.create(
                data={
                    "pincode": AREA_A,
                    "name": "T019 Area A",
                    "district": "TEST",
                    "lat": 28.63,
                    "lng": 77.07,
                }
            )
            area_b = await db.area.create(
                data={
                    "pincode": AREA_B,
                    "name": "T019 Area B",
                    "district": "TEST",
                    "lat": 28.64,
                    "lng": 77.08,
                }
            )
            category = await db.category.create(
                data={
                    "name": "T019 Feed",
                    "slug": CAT_MAIN,
                    "icon": "circle-help",
                    "color": "#000000",
                    "sortOrder": 1000,
                }
            )
            other_category = await db.category.create(
                data={
                    "name": "T019 Other",
                    "slug": CAT_OTHER,
                    "icon": "circle-help",
                    "color": "#111111",
                    "sortOrder": 1001,
                }
            )

            viewer = await db.user.create(
                data={"alias": f"T019_viewer_{uuid4().hex[:6]}", "isPseudonymous": True}
            )
            author_x = await db.user.create(
                data={"alias": f"T019_authorx_{uuid4().hex[:6]}", "isPseudonymous": True}
            )
            author_y = await db.user.create(
                data={"alias": f"T019_authory_{uuid4().hex[:6]}", "isPseudonymous": True}
            )
            token = new_session_token()
            await db.session.create(
                data={
                    "userId": viewer.id,
                    "tokenHash": hash_session_token(token),
                    "expiresAt": utcnow() + timedelta(hours=1),
                }
            )
            await db.areafollow.create(data={"userId": viewer.id, "areaId": area_b.id})
            await db.follow.create(data={"followerId": viewer.id, "followingId": author_x.id})

            return {
                "area_a": area_a.id,
                "area_b": area_b.id,
                "category": category.id,
                "other_category": other_category.id,
                "viewer": {"id": viewer.id, "token": token},
                "author_x": author_x.id,
                "author_y": author_y.id,
            }
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _cleanup_world() -> None:
    async def run() -> None:
        db = Prisma()
        await db.connect()
        try:
            posts = await db.post.find_many(where={"title": {"startswith": PREFIX}})
            ids = [post.id for post in posts]
            if ids:
                await db.vote.delete_many(where={"targetId": {"in": ids}})
            await db.post.delete_many(where={"title": {"startswith": PREFIX}})
            await db.user.delete_many(where={"alias": {"startswith": "T019_"}})
            await db.area.delete_many(where={"pincode": {"in": [AREA_A, AREA_B]}})
            await db.category.delete_many(where={"slug": {"in": [CAT_MAIN, CAT_OTHER]}})
        finally:
            await db.disconnect()

    asyncio.run(run())


@pytest.fixture()
def world(client: TestClient) -> Iterator[dict]:
    data = _create_world()
    try:
        yield data
    finally:
        _cleanup_world()


def _create_post(
    world: dict,
    *,
    title: str,
    area: str = "area_a",
    category: str = "category",
    author: str | None = None,
    created_at: datetime | None = None,
    upvotes: int = 0,
    downvotes: int = 0,
    comments: int = 0,
    views: int = 0,
    lat: float | None = None,
    lng: float | None = None,
    moderation: ModerationState = ModerationState.CLEAN,
) -> str:
    area_id = world[area]
    category_id = world[category]
    author_id = world[author] if author is not None else None

    async def run() -> str:
        db = Prisma()
        await db.connect()
        try:
            post = await db.post.create(
                data={
                    "authorId": author_id,
                    "alias": "T019_neighbor",
                    "isAnonymous": author_id is not None,
                    "areaId": area_id,
                    "categoryId": category_id,
                    "title": f"{PREFIX} {title}",
                    "body": f"{PREFIX} body",
                    "status": PostStatus.OPEN,
                    "moderationState": moderation,
                    "upvoteCount": upvotes,
                    "downvoteCount": downvotes,
                    "commentCount": comments,
                    "viewCount": views,
                    "lat": lat,
                    "lng": lng,
                    **({} if created_at is None else {"createdAt": created_at}),
                }
            )
            return post.id
        finally:
            await db.disconnect()

    return asyncio.run(run())


def _params(world: dict, **overrides: object) -> dict[str, object]:
    params: dict[str, object] = {
        "area_id": world["area_a"],
        "category_id": world["category"],
    }
    params.update(overrides)
    return params


def _ids(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [row["id"] for row in response.json()["data"]]


def test_new_is_newest_first_and_filters(world: dict, client: TestClient) -> None:
    now = datetime.now(UTC)
    newer = _create_post(world, title="newer", created_at=now - timedelta(hours=1))
    older = _create_post(world, title="older", created_at=now - timedelta(hours=3))
    middle = _create_post(world, title="middle", created_at=now - timedelta(hours=2))
    _create_post(
        world,
        title="other area",
        area="area_b",
        created_at=now - timedelta(minutes=30),
    )
    _create_post(
        world,
        title="other category",
        category="other_category",
        created_at=now - timedelta(minutes=20),
    )

    response = client.get("/api/v1/feed/new", params=_params(world, limit=10))

    assert _ids(response) == [newer, middle, older]


def test_trending_order_with_fixed_timestamps(world: dict, client: TestClient) -> None:
    created = utcnow() - timedelta(hours=1)
    low = _create_post(world, title="low", created_at=created, comments=0)
    high = _create_post(world, title="high", created_at=created, comments=5)
    mid = _create_post(world, title="mid", created_at=created, comments=2)

    response = client.get("/api/v1/feed/trending", params=_params(world, limit=10))

    assert _ids(response) == [high, mid, low]
    scores = [row["score"] for row in response.json()["data"]]
    assert scores == sorted(scores, reverse=True)


def test_trending_decays_old_posts(world: dict, client: TestClient) -> None:
    now = datetime.now(UTC)
    old = _create_post(world, title="old", created_at=now - timedelta(hours=100), comments=0)
    fresh = _create_post(world, title="fresh", created_at=now - timedelta(hours=1), comments=0)

    response = client.get("/api/v1/feed/trending", params=_params(world, limit=10))

    assert _ids(response) == [fresh, old]


def test_for_you_boosts_followed_author_and_area(world: dict, client: TestClient) -> None:
    created = utcnow() - timedelta(hours=1)
    followed_author_post = _create_post(
        world, title="followed author", author="author_x", created_at=created
    )
    other_author_post = _create_post(
        world, title="other author", author="author_y", created_at=created
    )

    affinity = client.get(
        "/api/v1/feed/for-you",
        params=_params(world, limit=10),
        headers=_bearer(world["viewer"]["token"]),
    )
    ids = _ids(affinity)
    assert ids.index(followed_author_post) < ids.index(other_author_post)

    in_followed_area = _create_post(
        world, title="followed area", area="area_b", author="author_y", created_at=created
    )
    in_plain_area = _create_post(
        world, title="plain area", area="area_a", author="author_y", created_at=created
    )
    area_boosted = client.get(
        "/api/v1/feed/for-you",
        params={"category_id": world["category"], "limit": 10},
        headers=_bearer(world["viewer"]["token"]),
    )
    ids = _ids(area_boosted)
    assert ids.index(in_followed_area) < ids.index(in_plain_area)


def test_anonymous_for_you_matches_trending(world: dict, client: TestClient) -> None:
    created = utcnow() - timedelta(hours=1)
    _create_post(world, title="a", created_at=created, comments=0)
    _create_post(world, title="b", created_at=created, comments=5)
    _create_post(world, title="c", created_at=created, comments=2)

    trending = client.get("/api/v1/feed/trending", params=_params(world, limit=10))
    for_you = client.get("/api/v1/feed/for-you", params=_params(world, limit=10))

    assert _ids(trending) == _ids(for_you)


def test_nearby_orders_by_distance_and_filters(world: dict, client: TestClient) -> None:
    base = (28.63, 77.07)
    at_centre = _create_post(world, title="centre", lat=base[0], lng=base[1])
    near = _create_post(world, title="near", lat=28.633, lng=77.07)
    in_radius = _create_post(world, title="in radius", lat=28.63, lng=77.11)
    outside = _create_post(world, title="outside", lat=28.63, lng=77.30)
    _create_post(world, title="no coords")

    response = client.get(
        "/api/v1/feed/nearby",
        params=_params(world, lat=base[0], lng=base[1], radius_m=5000, limit=10),
    )

    assert _ids(response) == [at_centre, near, in_radius]
    distances = [row["distance_meters"] for row in response.json()["data"]]
    assert distances == sorted(distances)
    assert outside not in _ids(response)

    tight = client.get(
        "/api/v1/feed/nearby",
        params=_params(world, lat=base[0], lng=base[1], radius_m=1000, limit=10),
    )
    assert _ids(tight) == [at_centre, near]


def test_hidden_posts_never_appear(world: dict, client: TestClient) -> None:
    hidden = _create_post(
        world,
        title="hidden",
        lat=28.63,
        lng=77.07,
        moderation=ModerationState.HIDDEN,
    )
    _create_post(world, title="visible", lat=28.63, lng=77.07)

    queries = [
        ("/api/v1/feed/new", {}),
        ("/api/v1/feed/trending", {}),
        ("/api/v1/feed/for-you", {}),
        ("/api/v1/feed/nearby", {"lat": 28.63, "lng": 77.07, "radius_m": 5000}),
    ]
    for path, extra in queries:
        response = client.get(path, params=_params(world, limit=10, **extra))
        assert hidden not in _ids(response), path


def test_new_pagination_does_not_repeat_originals(world: dict, client: TestClient) -> None:
    now = datetime.now(UTC)
    oldest = _create_post(world, title="p1", created_at=now - timedelta(hours=3))
    middle = _create_post(world, title="p2", created_at=now - timedelta(hours=2))
    newest = _create_post(world, title="p3", created_at=now - timedelta(hours=1))

    first = client.get("/api/v1/feed/new", params=_params(world, limit=2))
    first_ids = _ids(first)
    assert first_ids == [newest, middle]
    cursor = first.json()["meta"]["cursor"]
    assert cursor is not None

    # Arrives between pages; it is newer than the cursor and may be skipped.
    _create_post(world, title="late arrival", created_at=datetime.now(UTC))

    second = client.get("/api/v1/feed/new", params=_params(world, limit=2, cursor=cursor))
    seen = first_ids + _ids(second)
    assert sorted(seen) == sorted([oldest, middle, newest])


def test_trending_pagination_does_not_repeat_originals(world: dict, client: TestClient) -> None:
    created = utcnow() - timedelta(hours=1)
    low = _create_post(world, title="t1", created_at=created, comments=0)
    mid = _create_post(world, title="t2", created_at=created, comments=5)
    high = _create_post(world, title="t3", created_at=created, comments=10)

    first = client.get("/api/v1/feed/trending", params=_params(world, limit=2))
    first_ids = _ids(first)
    assert first_ids == [high, mid]
    cursor = first.json()["meta"]["cursor"]

    _create_post(world, title="late high", created_at=datetime.now(UTC), comments=50)

    second = client.get("/api/v1/feed/trending", params=_params(world, limit=10, cursor=cursor))
    seen = first_ids + _ids(second)
    assert sorted(seen) == sorted([low, mid, high])


def test_invalid_cursor_is_rejected(world: dict, client: TestClient) -> None:
    for path in ("/api/v1/feed/new", "/api/v1/feed/trending"):
        response = client.get(path, params=_params(world, cursor="not-a-cursor"))
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"


def test_nearby_rejects_out_of_range_radius(world: dict, client: TestClient) -> None:
    response = client.get(
        "/api/v1/feed/nearby",
        params=_params(world, lat=28.63, lng=77.07, radius_m=25001),
    )
    assert response.status_code == 422
