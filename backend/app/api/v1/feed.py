"""Feed tabs: new, trending, for-you and nearby."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import Principal, get_principal
from app.schemas.feed import FeedPage
from app.services.feed import (
    NEARBY_DEFAULT_RADIUS_M,
    NEARBY_MAX_RADIUS_M,
    get_nearby_feed,
    get_new_feed,
    get_ranked_feed,
)

router = APIRouter(tags=["feed"])

_LIMIT = Annotated[int, Query(ge=1, le=50)]
_CURSOR = Annotated[str | None, Query(max_length=512)]
_AREA = Annotated[str | None, Query(max_length=64)]
_CATEGORY = Annotated[str | None, Query(max_length=64)]


@router.get("/feed/new", response_model=FeedPage)
async def feed_new(
    area_id: _AREA = None,
    category_id: _CATEGORY = None,
    limit: _LIMIT = 20,
    cursor: _CURSOR = None,
) -> FeedPage:
    """Newest-first, cursor over ``(created_at, id)``."""
    return await get_new_feed(area_id, category_id, limit, cursor)


@router.get("/feed/trending", response_model=FeedPage)
async def feed_trending(
    area_id: _AREA = None,
    category_id: _CATEGORY = None,
    limit: _LIMIT = 20,
    cursor: _CURSOR = None,
) -> FeedPage:
    """Time-decayed engagement, 18 h half-life, no personalisation."""
    return await get_ranked_feed(
        Principal(mode="ghost"), "trending", area_id, category_id, limit, cursor
    )


@router.get("/feed/for-you", response_model=FeedPage)
async def feed_for_you(
    principal: Annotated[Principal, Depends(get_principal)],
    area_id: _AREA = None,
    category_id: _CATEGORY = None,
    limit: _LIMIT = 20,
    cursor: _CURSOR = None,
) -> FeedPage:
    """12 h half-life plus followed-area / followed-author boosts for sessions.

    Anonymous callers get the same ranking as Trending here (all boosts 1.0).
    """
    return await get_ranked_feed(principal, "for-you", area_id, category_id, limit, cursor)


@router.get("/feed/nearby", response_model=FeedPage)
async def feed_nearby(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
    radius_m: Annotated[int, Query(ge=1, le=NEARBY_MAX_RADIUS_M)] = (NEARBY_DEFAULT_RADIUS_M),
    area_id: _AREA = None,
    category_id: _CATEGORY = None,
    limit: _LIMIT = 20,
    cursor: _CURSOR = None,
) -> FeedPage:
    """Posts with coordinates inside ``radius_m``, nearest first."""
    return await get_nearby_feed(lat, lng, radius_m, area_id, category_id, limit, cursor)
