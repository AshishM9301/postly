"""Feed ranking and the four tabs.

Trending and For You are ranked in Python from the denormalised counters, with
``now`` pinned inside the cursor so page 2 sees the same scores as page 1.
``/feed/new`` uses a ``(created_at, id)`` cursor, and Nearby uses
``(distance, id)`` — both stable when new posts arrive.
"""

from __future__ import annotations

import base64
import json
import math
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import HTTPException
from prisma.enums import ModerationState
from prisma.models import Post

from app.core.config import get_settings
from app.core.deps import Principal
from app.db.client import db
from app.schemas.feed import FeedMeta, FeedPage, FeedPost
from app.services.geo import haversine_meters
from app.services.posts import post_to_response

FEED_CANDIDATE_LIMIT = 1000
NEARBY_CANDIDATE_LIMIT = 2000
NEARBY_DEFAULT_RADIUS_M = 5000
NEARBY_MAX_RADIUS_M = 25000

CALLER_AREA_BOOST = 2.0
FOLLOWED_AREA_BOOST = 1.5
AFFINITY_BOOST = 1.5

FEED_INCLUDE = {"area": True, "category": True, "author": True, "media": True}

RankedTab = Literal["trending", "for-you"]


def _invalid_cursor() -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={"code": "validation_error", "message": "Invalid cursor"},
    )


def encode_cursor(**payload: object) -> str:
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def decode_cursor(value: str) -> dict[str, Any]:
    try:
        padded = value + "=" * (-len(value) % 4)
        parsed = json.loads(base64.urlsafe_b64decode(padded.encode()))
    except Exception as exc:
        raise _invalid_cursor() from exc
    if not isinstance(parsed, dict):
        raise _invalid_cursor()
    return parsed


def _parse_datetime(value: object) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError as exc:
        raise _invalid_cursor() from exc
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


def engagement(post: Post) -> float:
    """``log10(max(1, net_votes) + 2) + 0.6*comments + 0.05*views``."""
    net_votes = post.upvoteCount - post.downvoteCount
    return math.log10(max(1, net_votes) + 2) + 0.6 * post.commentCount + 0.05 * post.viewCount


def decayed_score(
    post: Post,
    now: datetime,
    half_life_hours: float,
    area_boost: float = 1.0,
    affinity_boost: float = 1.0,
) -> float:
    """``engagement * exp(-age_hours / half_life) * boosts``."""
    age_hours = max(0.0, (now - post.createdAt).total_seconds() / 3600.0)
    return engagement(post) * math.exp(-age_hours / half_life_hours) * area_boost * affinity_boost


def _where(area_id: str | None, category_id: str | None) -> dict[str, object]:
    conditions: list[dict[str, object]] = [{"moderationState": {"not": ModerationState.HIDDEN}}]
    if area_id is not None:
        conditions.append({"areaId": area_id})
    if category_id is not None:
        conditions.append({"categoryId": category_id})
    return {"AND": conditions}


def _feed_post(
    post: Post, *, score: float | None = None, distance_meters: int | None = None
) -> FeedPost:
    return FeedPost(
        **post_to_response(post).model_dump(),
        score=score,
        distance_meters=distance_meters,
    )


async def _affinity(principal: Principal) -> tuple[set[str], set[str]]:
    """Followed areas and authors for a signed-in caller (T-051 exposes these)."""
    if principal.user_id is None:
        return set(), set()

    area_follows = await db.areafollow.find_many(where={"userId": principal.user_id})
    follows = await db.follow.find_many(where={"followerId": principal.user_id})
    return {row.areaId for row in area_follows}, {row.followingId for row in follows}


async def get_new_feed(
    area_id: str | None, category_id: str | None, limit: int, cursor: str | None
) -> FeedPage:
    where = _where(area_id, category_id)

    if cursor is not None:
        data = decode_cursor(cursor)
        created_at = _parse_datetime(data.get("created_at"))
        cursor_id = str(data.get("id", ""))
        if not cursor_id:
            raise _invalid_cursor()
        where = {
            "AND": [
                where,
                {
                    "OR": [
                        {"createdAt": {"lt": created_at}},
                        {"createdAt": created_at, "id": {"lt": cursor_id}},
                    ]
                },
            ]
        }

    rows = await db.post.find_many(
        where=where,
        include=FEED_INCLUDE,
        order=[{"createdAt": "desc"}, {"id": "desc"}],
        take=limit + 1,
    )
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = (
        encode_cursor(created_at=page[-1].createdAt.isoformat(), id=page[-1].id)
        if has_more and page
        else None
    )
    return FeedPage(
        data=[_feed_post(post) for post in page],
        meta=FeedMeta(cursor=next_cursor, has_more=has_more),
    )


async def get_ranked_feed(
    principal: Principal,
    tab: RankedTab,
    area_id: str | None,
    category_id: str | None,
    limit: int,
    cursor: str | None,
) -> FeedPage:
    now = datetime.now(UTC)
    cursor_score: float | None = None
    cursor_id = ""

    if cursor is not None:
        data = decode_cursor(cursor)
        now = _parse_datetime(data.get("now"))
        try:
            cursor_score = float(data["score"])
        except (KeyError, TypeError, ValueError) as exc:
            raise _invalid_cursor() from exc
        cursor_id = str(data.get("id", ""))
        if not cursor_id:
            raise _invalid_cursor()

    settings = get_settings()
    if tab == "trending":
        half_life = settings.trending_half_life_hours
        followed_areas: set[str] = set()
        followed_authors: set[str] = set()
    else:
        half_life = settings.for_you_half_life_hours
        followed_areas, followed_authors = await _affinity(principal)

    rows = await db.post.find_many(
        where=_where(area_id, category_id),
        include=FEED_INCLUDE,
        order=[{"createdAt": "desc"}],
        take=FEED_CANDIDATE_LIMIT,
    )

    signed_in = principal.user_id is not None
    ranked: list[tuple[Post, float]] = []
    for post in rows:
        area_boost = 1.0
        if signed_in and area_id is not None and post.areaId == area_id:
            area_boost = CALLER_AREA_BOOST
        elif signed_in and post.areaId in followed_areas:
            area_boost = FOLLOWED_AREA_BOOST

        affinity_boost = (
            AFFINITY_BOOST
            if post.authorId is not None and post.authorId in followed_authors
            else 1.0
        )
        ranked.append((post, decayed_score(post, now, half_life, area_boost, affinity_boost)))

    ranked.sort(key=lambda item: (-item[1], item[0].id))

    if cursor_score is not None:
        cursor_key = (-cursor_score, cursor_id)
        ranked = [item for item in ranked if (-item[1], item[0].id) > cursor_key]

    has_more = len(ranked) > limit
    page = ranked[:limit]
    next_cursor = (
        encode_cursor(now=now.isoformat(), score=page[-1][1], id=page[-1][0].id)
        if has_more and page
        else None
    )
    return FeedPage(
        data=[_feed_post(post, score=score) for post, score in page],
        meta=FeedMeta(cursor=next_cursor, has_more=has_more),
    )


async def get_nearby_feed(
    lat: float,
    lng: float,
    radius_m: int,
    area_id: str | None,
    category_id: str | None,
    limit: int,
    cursor: str | None,
) -> FeedPage:
    cursor_distance: int | None = None
    cursor_id = ""
    if cursor is not None:
        data = decode_cursor(cursor)
        try:
            cursor_distance = int(data["distance"])
        except (KeyError, TypeError, ValueError) as exc:
            raise _invalid_cursor() from exc
        cursor_id = str(data.get("id", ""))
        if not cursor_id:
            raise _invalid_cursor()

    rows = await db.post.find_many(
        where=_where(area_id, category_id),
        include=FEED_INCLUDE,
        order=[{"createdAt": "desc"}],
        take=NEARBY_CANDIDATE_LIMIT,
    )

    located: list[tuple[Post, int]] = []
    for post in rows:
        if post.lat is None or post.lng is None:
            continue
        distance = int(round(haversine_meters(lat, lng, post.lat, post.lng)))
        if distance <= radius_m:
            located.append((post, distance))

    located.sort(key=lambda item: (item[1], item[0].id))

    if cursor_distance is not None:
        cursor_key = (cursor_distance, cursor_id)
        located = [item for item in located if (item[1], item[0].id) > cursor_key]

    has_more = len(located) > limit
    page = located[:limit]
    next_cursor = (
        encode_cursor(distance=page[-1][1], id=page[-1][0].id) if has_more and page else None
    )
    return FeedPage(
        data=[_feed_post(post, distance_meters=distance) for post, distance in page],
        meta=FeedMeta(cursor=next_cursor, has_more=has_more),
    )
