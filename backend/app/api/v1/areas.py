"""Area lookup: exact PIN, name/district search and GPS nearest.

All three are served from the seeded local table with no external calls. The
nearest-area scan is bounded and cached: there are 103 areas today, but a public
endpoint that reads every row on each request is still worth a cheap guard.
"""

from __future__ import annotations

import re
import time
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from prisma.models import Area

from app.db.client import db
from app.schemas.area import AreaDetail, AreaDetection, AreaOut
from app.schemas.auth import Envelope
from app.services.geo import AreaPoint, nearest_area

router = APIRouter(tags=["areas"])

SEARCH_LIMIT_DEFAULT = 10
SEARCH_LIMIT_MAX = 25
NEAREST_CANDIDATE_LIMIT = 500
AREA_CACHE_TTL_SECONDS = 60.0

_PIN_PATTERN = re.compile(r"^\d{6}$")

_area_cache: tuple[float, list[AreaPoint]] | None = None


def clear_area_cache() -> None:
    """Drop the cached area points (used by tests after changing the table)."""
    global _area_cache
    _area_cache = None


def _to_area_out(area: Area) -> AreaOut:
    return AreaOut(
        id=area.id,
        pincode=area.pincode,
        name=area.name,
        district=area.district,
        lat=area.lat,
        lng=area.lng,
    )


def _to_point(area: Area) -> AreaPoint:
    return AreaPoint(
        id=area.id,
        pincode=area.pincode,
        name=area.name,
        district=area.district,
        lat=area.lat,
        lng=area.lng,
    )


def _escape_like(value: str) -> str:
    """Make ``%``, ``_`` and ``\\`` literal for Postgres LIKE (default escape)."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _area_points() -> list[AreaPoint]:
    global _area_cache
    now = time.monotonic()
    if _area_cache is not None and now - _area_cache[0] < AREA_CACHE_TTL_SECONDS:
        return _area_cache[1]

    rows = await db.area.find_many(
        where={"isActive": True},
        order={"pincode": "asc"},
        take=NEAREST_CANDIDATE_LIMIT,
    )
    points = [_to_point(area) for area in rows]
    _area_cache = (now, points)
    return points


@router.get("/areas/search", response_model=Envelope[list[AreaOut]])
async def search_areas(
    q: Annotated[str, Query(min_length=1, max_length=100)],
    limit: Annotated[int, Query(ge=1, le=SEARCH_LIMIT_MAX)] = SEARCH_LIMIT_DEFAULT,
) -> Envelope[list[AreaOut]]:
    """Search by PIN (exact) or by locality name/district (substring match).

    Six digits are treated as a PIN, never a fuzzy name; anything else is a
    case-insensitive ``ILIKE`` over the area's display name, its stored aliases
    (every office name for the PIN) and its district, bounded by ``limit``.
    ``%``, ``_`` and ``\\`` are matched literally, not as LIKE wildcards.
    """
    query = q.strip()
    if not query:
        return Envelope(data=[])

    if _PIN_PATTERN.match(query):
        area = await db.area.find_unique(where={"pincode": query})
        if area is None or not area.isActive:
            return Envelope(data=[])
        return Envelope(data=[_to_area_out(area)])

    pattern = _escape_like(query)
    rows = await db.area.find_many(
        where={
            "isActive": True,
            "OR": [
                {"name": {"contains": pattern, "mode": "insensitive"}},
                {"district": {"contains": pattern, "mode": "insensitive"}},
                {"names": {"some": {"name": {"contains": pattern, "mode": "insensitive"}}}},
            ],
        },
        order={"pincode": "asc"},
        take=limit,
    )
    return Envelope(data=[_to_area_out(area) for area in rows])


@router.get("/areas/detect", response_model=Envelope[AreaDetection])
async def detect_area(
    lat: Annotated[float, Query(ge=-90, le=90)],
    lng: Annotated[float, Query(ge=-180, le=180)],
) -> Envelope[AreaDetection]:
    """Return the nearest seeded area to a coordinate.

    Deliberately has no distance cut-off: a visitor just outside Delhi (or with a
    coarse GPS fix) still gets the closest area plus the distance to judge it.
    A ``404 area_not_found`` only happens when the table has no active areas.
    """
    found = nearest_area(await _area_points(), lat, lng)
    if found is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "area_not_found", "message": "No areas are available"},
        )

    area, distance = found
    return Envelope(
        data=AreaDetection(
            id=area.id,
            pincode=area.pincode,
            name=area.name,
            district=area.district,
            lat=area.lat,
            lng=area.lng,
            distance_meters=distance,
        )
    )


@router.get("/areas/{area_id}", response_model=Envelope[AreaDetail])
async def get_area(area_id: str) -> Envelope[AreaDetail]:
    """One area plus how many posts belong to it (public profile of an area)."""
    area = await db.area.find_unique(where={"id": area_id})
    if area is None or not area.isActive:
        raise HTTPException(
            status_code=404,
            detail={"code": "area_not_found", "message": "No such area"},
        )

    return Envelope(
        data=AreaDetail(
            id=area.id,
            pincode=area.pincode,
            name=area.name,
            district=area.district,
            lat=area.lat,
            lng=area.lng,
            post_count=await db.post.count(where={"areaId": area_id}),
        )
    )
