"""Geometry helpers for area lookup.

Pure Python and framework-free: 103 rows do not need PostGIS, and the same
Haversine can be unit-tested against a hand-known pair of coordinates.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_METERS = 6_371_000.0


@dataclass(frozen=True)
class AreaPoint:
    """The minimal area fields the nearest-area search needs."""

    id: str
    pincode: str
    name: str
    district: str
    lat: float
    lng: float


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance in metres on a 6,371 km sphere."""
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    dphi = phi2 - phi1
    dlambda = radians(lng2 - lng1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * asin(sqrt(a))


def nearest_area(
    areas: Iterable[AreaPoint], lat: float, lng: float
) -> tuple[AreaPoint, int] | None:
    """Return the closest area and its distance in whole metres.

    Ties keep the first candidate (callers pass a stable, pincode-sorted list),
    so the endpoint is deterministic. ``None`` means there were no candidates.
    """
    best: AreaPoint | None = None
    best_distance = 0.0

    for area in areas:
        distance = haversine_meters(lat, lng, area.lat, area.lng)
        if best is None or distance < best_distance:
            best = area
            best_distance = distance

    if best is None:
        return None
    return best, int(round(best_distance))
