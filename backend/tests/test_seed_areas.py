"""Normalisation and aggregation rules for the Delhi area seed.

These tests use tiny inline fixtures, never the 21 MB CSV.
"""

from __future__ import annotations

import math

from scripts.seed_areas import (
    MIN_RADIUS_METERS,
    Office,
    build_area,
    haversine_meters,
    normalise_district,
    parse_coordinate,
    parse_office,
    select_main_office,
    strip_office_suffix,
)


def office(
    name: str,
    *,
    officetype: str = "PO",
    district: str = "South East",
    lat: float | None = 28.61,
    lng: float | None = 77.21,
) -> Office:
    return Office(
        name=name,
        officetype=officetype,
        district=district,
        lat=lat,
        lng=lng,
    )


def test_strips_every_office_suffix_variant() -> None:
    cases = {
        "Karol Bagh SO": "Karol Bagh",
        "Chaukhandi B.O": "Chaukhandi",
        "L. M. Nagar Indl. Area S.O": "L. M. Nagar Indl. Area",
        "Rana Pratap Bagh SO": "Rana Pratap Bagh",
        "Panchsheel Enclave Post Office": "Panchsheel Enclave",
        "Saket SO South Delhi": "Saket",
        "Shakti Nagar SO North Delhi": "Shakti Nagar",
        "Tilak Nagar S.O (West Delhi)": "Tilak Nagar",
        "Badli SO North West Delhi": "Badli",
        "Delhi GPO": "Delhi GPO",
        "Mukundpur Village": "Mukundpur Village",
    }

    for raw, expected in cases.items():
        assert strip_office_suffix(raw) == expected, raw


def test_district_is_upper_case_and_trimmed() -> None:
    assert normalise_district(" South East ") == "SOUTH EAST"
    assert normalise_district("SOUTH WEST") == "SOUTH WEST"
    assert normalise_district(None) == ""


def test_missing_coordinates_are_none_not_zero() -> None:
    assert parse_coordinate("NA") is None
    assert parse_coordinate(" na ") is None
    assert parse_coordinate("") is None
    assert parse_coordinate(None) is None
    assert parse_coordinate("28.6922500") == 28.69225


def test_out_of_bounds_coordinates_are_treated_as_missing() -> None:
    base = {
        "statename": "DELHI",
        "pincode": "110043",
        "officename": "Khaira B.O",
        "officetype": "BO",
        "district": "WEST",
    }

    out_of_state = parse_office({**base, "latitude": "24.871535", "longitude": "86.207106"})
    placeholder = parse_office({**base, "latitude": "22.0", "longitude": "77.0"})
    corrupt = parse_office({**base, "latitude": "32.643914", "longitude": "74.046903"})
    inside = parse_office({**base, "latitude": "28.65", "longitude": "77.19"})

    for parsed in (out_of_state, placeholder, corrupt):
        assert parsed is not None
        assert parsed.lat is None
        assert parsed.lng is None
    assert inside is not None
    assert inside.lat == 28.65


def test_parse_office_ignores_other_states_and_missing_pincode() -> None:
    row = {
        "statename": "Delhi",
        "pincode": "110001",
        "officename": "Baroda House SO",
        "officetype": "PO",
        "district": "New Delhi",
        "latitude": "28.61",
        "longitude": "77.21",
        "circlename": "Delhi Circle",
        "regionname": "DivReportingCircle",
        "divisionname": "New Delhi Division",
    }
    parsed = parse_office(row)
    assert parsed is not None
    assert parsed.name == "Baroda House SO"
    assert parsed.district == "NEW DELHI"
    assert parsed.lat == 28.61

    assert parse_office({**row, "statename": "Haryana"}) is None
    assert parse_office({**row, "pincode": " "}) is None


def test_prefers_sub_office_over_branch_office() -> None:
    offices = [
        office("Khajoori Khas BO", officetype="BO"),
        office("Karawal Nagar SO"),
    ]

    main = select_main_office(offices)
    assert main is not None
    assert main.name == "Karawal Nagar SO"


def test_builds_area_with_stripped_name_and_upper_district() -> None:
    area = build_area(
        "110001",
        [
            office("Baroda House SO"),
            office("Supreme Court SO"),
        ],
    )

    assert area is not None
    assert area["pincode"] == "110001"
    assert area["name"] == "Baroda House"
    assert area["district"] == "SOUTH EAST"
    assert area["lat"] == 28.61
    assert area["lng"] == 77.21
    assert area["officeCount"] == 2
    assert area["radiusMeters"] == MIN_RADIUS_METERS


def test_radius_is_max_distance_to_the_other_offices() -> None:
    center = office("Karol Bagh SO", lat=28.65, lng=77.19)
    near = office("Sat Nagar SO", lat=28.651, lng=77.191)
    far = office("Desh Bandhu Gupta Road SO", lat=28.67, lng=77.21)

    area = build_area("110005", [center, near, far])
    assert area is not None

    expected = max(
        haversine_meters(center.lat, center.lng, near.lat, near.lng),
        haversine_meters(center.lat, center.lng, far.lat, far.lng),
    )
    assert area["radiusMeters"] == max(MIN_RADIUS_METERS, math.ceil(expected))
    assert area["radiusMeters"] > MIN_RADIUS_METERS


def test_radius_floors_at_1500_even_with_no_other_offices() -> None:
    area = build_area("110011", [office("Nirman Bhawan SO")])
    assert area is not None
    assert area["radiusMeters"] == MIN_RADIUS_METERS


def test_radius_ignores_an_office_with_an_impossible_coordinate() -> None:
    main = office("Brahampuri SO", lat=28.6871944, lng=77.2633056)
    near = office("Jagjit Nagar SO", lat=28.6870833, lng=77.2591111)
    broken = office("Garhi Mandu BO", officetype="BO", lat=28.38, lng=77.12)

    area = build_area("110053", [main, near, broken])
    assert area is not None

    expected = math.ceil(haversine_meters(main.lat, main.lng, near.lat, near.lng))
    assert area["radiusMeters"] == max(MIN_RADIUS_METERS, expected)
    assert area["radiusMeters"] < 5000
    assert area["officeCount"] == 3


def test_area_without_any_coordinate_is_skipped() -> None:
    area = build_area(
        "110999",
        [office("Nowhere BO", officetype="BO", lat=None, lng=None)],
    )
    assert area is None
