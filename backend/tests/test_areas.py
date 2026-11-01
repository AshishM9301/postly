"""Areas and categories: search, GPS detection, distance and ordering.

The fixtures live at (0, 0) and (0.01, 0) so they are far from every seeded
Delhi area, which makes the nearest-area assertions deterministic.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from app.api.v1.areas import clear_area_cache
from app.main import app
from app.services.geo import AreaPoint, haversine_meters, nearest_area
from fastapi.testclient import TestClient
from prisma import Prisma

# pincode, name, district, lat, lng
FIXTURES: list[tuple[str, str, str, float, float]] = [
    ("000001", "Testville", "TEST", 0.0, 0.0),
    ("000002", "Karol Test Bagh", "TEST", 0.01, 0.0),
]

# Extra locality names for the PIN, the way the seed stores every office name.
FIXTURE_ALIASES: dict[str, list[str]] = {
    "000001": ["Aliasville", "Karol Bagh"],
    "000002": ["Karol Test Bagh"],
}

SEEDED_CATEGORIES = [
    "pothole",
    "water",
    "garbage",
    "electricity",
    "roads",
    "streetlight",
    "noise",
    "drainage",
    "other",
]


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def _seed_areas() -> None:
    async def run() -> None:
        db = Prisma()
        await db.connect()
        try:
            for pincode, name, district, lat, lng in FIXTURES:
                await db.area.delete_many(where={"pincode": pincode})
                area = await db.area.create(
                    data={
                        "pincode": pincode,
                        "name": name,
                        "district": district,
                        "lat": lat,
                        "lng": lng,
                    }
                )
                await db.areaname.create_many(
                    data=[{"areaId": area.id, "name": alias} for alias in FIXTURE_ALIASES[pincode]],
                    skip_duplicates=True,
                )
        finally:
            await db.disconnect()

    asyncio.run(run())


def _clean_areas() -> None:
    async def run() -> None:
        db = Prisma()
        await db.connect()
        try:
            await db.area.delete_many(where={"pincode": {"in": [row[0] for row in FIXTURES]}})
        finally:
            await db.disconnect()

    asyncio.run(run())


@pytest.fixture()
def areas(client: TestClient) -> Iterator[None]:
    _seed_areas()
    clear_area_cache()
    try:
        yield
    finally:
        _clean_areas()
        clear_area_cache()


def test_search_exact_pin(areas: None, client: TestClient) -> None:
    response = client.get("/api/v1/areas/search", params={"q": "000001"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["pincode"] == "000001"
    assert data[0]["name"] == "Testville"


def test_search_six_digits_does_not_fall_back_to_names(areas: None, client: TestClient) -> None:
    response = client.get("/api/v1/areas/search", params={"q": "999999"})

    assert response.status_code == 200
    assert response.json()["data"] == []


def test_search_by_name_is_case_insensitive_and_bounded(areas: None, client: TestClient) -> None:
    response = client.get("/api/v1/areas/search", params={"q": "KAROL", "limit": 1})

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["pincode"] == "000001"


def test_search_matches_a_stored_alias(areas: None, client: TestClient) -> None:
    response = client.get("/api/v1/areas/search", params={"q": "aliasville"})

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["pincode"] == "000001"
    assert data[0]["name"] == "Testville"


def test_search_treats_like_wildcards_literally(areas: None, client: TestClient) -> None:
    for query in ("%", "_", "\\", "alias%"):
        response = client.get("/api/v1/areas/search", params={"q": query})

        assert response.status_code == 200, query
        assert response.json()["data"] == [], query


def test_search_by_district(areas: None, client: TestClient) -> None:
    response = client.get("/api/v1/areas/search", params={"q": "test"})

    assert response.status_code == 200
    pincodes = {row["pincode"] for row in response.json()["data"]}
    assert {"000001", "000002"} <= pincodes


def test_detect_returns_nearest_area_with_distance(areas: None, client: TestClient) -> None:
    response = client.get("/api/v1/areas/detect", params={"lat": 0.0, "lng": 1.0})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pincode"] == "000001"

    expected = haversine_meters(0.0, 1.0, 0.0, 0.0)
    assert abs(data["distance_meters"] - expected) <= 2


def test_detect_outside_delhi_returns_nearest_anyway(areas: None, client: TestClient) -> None:
    response = client.get("/api/v1/areas/detect", params={"lat": 0.0, "lng": 0.5})

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pincode"] == "000001"
    assert data["distance_meters"] > 50_000


def test_detect_rejects_out_of_range_coordinates(areas: None, client: TestClient) -> None:
    response = client.get("/api/v1/areas/detect", params={"lat": 91, "lng": 0})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_get_area_by_id_includes_post_count(areas: None, client: TestClient) -> None:
    search = client.get("/api/v1/areas/search", params={"q": "000001"})
    area_id = search.json()["data"][0]["id"]

    response = client.get(f"/api/v1/areas/{area_id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["pincode"] == "000001"
    assert data["name"] == "Testville"
    assert data["post_count"] == 0


def test_get_unknown_area_is_404(client: TestClient) -> None:
    response = client.get(f"/api/v1/areas/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "area_not_found"


def test_categories_are_returned_in_sort_order(client: TestClient) -> None:
    response = client.get("/api/v1/categories")

    assert response.status_code == 200
    data = response.json()["data"]
    assert [row["slug"] for row in data] == SEEDED_CATEGORIES
    sort_orders = [row["sort_order"] for row in data]
    assert sort_orders == sorted(sort_orders)
    assert sort_orders[0] == 1


def test_haversine_known_pair_and_nearest_tie_break() -> None:
    # One degree of longitude at the equator: 2*pi*6371000/360 = 111,194.93 m.
    assert haversine_meters(0.0, 0.0, 0.0, 1.0) == pytest.approx(111_194.93, abs=0.01)

    first = AreaPoint("a", "000001", "First", "TEST", 0.0, 0.0)
    second = AreaPoint("b", "000002", "Second", "TEST", 0.0, 0.0)
    found = nearest_area([first, second], 0.0, 0.0)

    assert found is not None
    assert found[0] is first
    assert found[1] == 0
