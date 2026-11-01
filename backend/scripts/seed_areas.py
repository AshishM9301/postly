"""Seed one ``Area`` per Delhi PIN code from the CC0 India Post dataset.

Source: https://github.com/ghousekw/india-pincodes (``pincode.csv``, CC0 1.0).
The file is ~21 MB; it is streamed and only the Delhi rows (550) are kept.

The CSV is cached under ``backend/.cache/pincode.csv`` (gitignored) so the seed
is offline and fast after the first run. Deleting the cache re-downloads it.

Idempotent: rows are upserted on ``Area.pincode``.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import math
import re
import shutil
import sys
import urllib.request
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

from prisma import Prisma

DATASET_URL = "https://raw.githubusercontent.com/ghousekw/india-pincodes/master/pincode.csv"
DEFAULT_CACHE = Path(__file__).resolve().parents[1] / ".cache" / "pincode.csv"

DELHI = "DELHI"
MIN_RADIUS_METERS = 1500
EARTH_RADIUS_METERS = 6_371_000.0

# Delhi NCT sits at roughly 28.4–28.9 N, 76.8–77.4 E. A generous box rejects the
# rows whose coordinates are actually in another state (24.87/86.21), a round
# placeholder (22.0/77.0), or otherwise corrupted (32.64/74.05). Without this,
# one bad office blows a PIN's radius up to thousands of kilometres.
DELHI_BBOX = (28.30, 76.80, 29.00, 77.60)

# The largest legitimate spread inside a Delhi PIN is ~12 km. A single office
# farther than this from the PIN's main office is a bad coordinate (e.g.
# "Garhi Mandu BO" at 28.38/77.12 instead of ~28.70/77.25); ignore it rather
# than growing a neighbourhood to 37 km.
MAX_OFFICE_SPREAD_METERS = 20_000

# India Post office-type suffixes as they appear in this file: "Karol Bagh SO",
# "Chaukhandi B.O", "L. M. Nagar S.O", "X Post Office". Some names also carry a
# trailing district qualifier ("Saket SO South Delhi", "Tilak Nagar S.O (West
# Delhi)"); that is part of the suffix, not the locality.
_OFFICE_SUFFIX = re.compile(
    r"\s+(?:S\.?O|B\.?O|P\.?O|H\.?O|POST\s+OFFICE)\.?"
    r"(?:\s*\(?\s*"
    r"(?:CENTRAL|EAST|NEW|NORTH(?:\s+EAST|\s+WEST)?|SOUTH(?:\s+EAST|\s+WEST)?|WEST|SHAHDARA)"
    r"\s+DELHI\s*\)?)?\s*$",
    re.IGNORECASE,
)

# The dataset labels the sub-office rows "PO" (their names still end in "SO"),
# and head offices "HO". Prefer a sub office, then a head office.
_MAIN_OFFICE_ORDER = ("SO", "PO", "HO")


@dataclass(frozen=True)
class Office:
    name: str
    officetype: str
    district: str
    lat: float | None
    lng: float | None
    circle: str = ""
    region: str = ""
    division: str = ""


def parse_coordinate(value: str | None) -> float | None:
    """Return ``None`` for the dataset's missing markers instead of a fake 0."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped or stripped.upper() == "NA":
        return None
    try:
        return float(stripped)
    except ValueError:
        return None


def normalise_district(value: str | None) -> str:
    return (value or "").strip().upper()


def is_delhi_coordinate(lat: float, lng: float) -> bool:
    min_lat, min_lng, max_lat, max_lng = DELHI_BBOX
    return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng


def strip_office_suffix(value: str) -> str:
    """``Karol Bagh SO`` -> ``Karol Bagh``; unrelated names are left alone."""
    name = value.strip()
    stripped = _OFFICE_SUFFIX.sub("", name).strip()
    return stripped or name


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_METERS * math.asin(math.sqrt(a))


def parse_office(row: Mapping[str, str]) -> Office | None:
    if (row.get("statename") or "").strip().upper() != DELHI:
        return None
    pincode = (row.get("pincode") or "").strip()
    if not pincode:
        return None
    lat = parse_coordinate(row.get("latitude"))
    lng = parse_coordinate(row.get("longitude"))
    if lat is None or lng is None or not is_delhi_coordinate(lat, lng):
        lat = None
        lng = None
    return Office(
        name=(row.get("officename") or "").strip(),
        officetype=(row.get("officetype") or "").strip().upper(),
        district=normalise_district(row.get("district")),
        lat=lat,
        lng=lng,
        circle=(row.get("circlename") or "").strip(),
        region=(row.get("regionname") or "").strip(),
        division=(row.get("divisionname") or "").strip(),
    )


def select_main_office(offices: Iterable[Office]) -> Office | None:
    """Prefer a sub office, then a head office, then the most common name."""
    candidates = [office for office in offices if office.lat is not None and office.lng is not None]
    if not candidates:
        candidates = list(offices)
    if not candidates:
        return None

    counts = Counter(office.name for office in candidates)
    for wanted in _MAIN_OFFICE_ORDER:
        for office in candidates:
            if office.officetype == wanted:
                return office
    best_count = max(counts.values())
    for office in candidates:
        if counts[office.name] == best_count:
            return office
    return candidates[0]


def build_area(pincode: str, offices: list[Office]) -> dict[str, object] | None:
    """Aggregate one PIN's offices into an ``Area`` row (``None`` without a centre)."""
    located = [office for office in offices if office.lat is not None and office.lng is not None]
    main = select_main_office(located)
    if main is None or main.lat is None or main.lng is None:
        return None

    farthest = 0.0
    for office in located:
        if office.name == main.name:
            continue
        distance = haversine_meters(main.lat, main.lng, office.lat, office.lng)
        if distance > MAX_OFFICE_SPREAD_METERS:
            continue
        farthest = max(farthest, distance)

    return {
        "pincode": pincode,
        "name": strip_office_suffix(main.name),
        "district": normalise_district(main.district),
        "circle": main.circle or None,
        "region": main.region or None,
        "division": main.division or None,
        "lat": main.lat,
        "lng": main.lng,
        "radiusMeters": max(MIN_RADIUS_METERS, math.ceil(farthest)),
        "officeCount": len({office.name for office in offices}),
        "isActive": True,
    }


def iter_delhi_offices(handle: Iterable[str]) -> Iterator[tuple[str, Office]]:
    for row in csv.DictReader(handle):
        office = parse_office(row)
        if office is None:
            continue
        yield (row.get("pincode") or "").strip(), office


def group_by_pincode(rows: Iterable[tuple[str, Office]]) -> dict[str, list[Office]]:
    grouped: dict[str, list[Office]] = defaultdict(list)
    for pincode, office in rows:
        grouped[pincode].append(office)
    return grouped


def alias_names(offices: list[Office]) -> list[str]:
    """Every distinct, suffix-stripped office name for one PIN."""
    names = {strip_office_suffix(office.name) for office in offices}
    return sorted(name for name in names if name)


def build_areas(
    grouped: Mapping[str, list[Office]],
) -> tuple[list[dict[str, object]], dict[str, list[str]], list[str]]:
    areas: list[dict[str, object]] = []
    aliases: dict[str, list[str]] = {}
    skipped: list[str] = []
    for pincode in sorted(grouped):
        area = build_area(pincode, grouped[pincode])
        if area is None:
            skipped.append(pincode)
        else:
            areas.append(area)
            aliases[pincode] = alias_names(grouped[pincode])
    return areas, aliases, skipped


def download_dataset(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    request = urllib.request.Request(DATASET_URL, headers={"User-Agent": "postly-seed-areas/0.1"})
    print(f"seed_areas: downloading {DATASET_URL}")
    with urllib.request.urlopen(request) as response, temporary.open("wb") as output:
        shutil.copyfileobj(response, output)
    temporary.replace(destination)


def read_areas(
    csv_path: Path,
) -> tuple[list[dict[str, object]], dict[str, list[str]], list[str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        grouped = group_by_pincode(iter_delhi_offices(handle))
    return build_areas(grouped)


async def seed_areas(
    areas: list[dict[str, object]], aliases: Mapping[str, list[str]]
) -> tuple[int, int]:
    db = Prisma()
    await db.connect()
    try:
        for area in areas:
            pincode = str(area["pincode"])
            row = await db.area.upsert(
                where={"pincode": pincode},
                data={"create": area, "update": area},
            )

            names = aliases.get(pincode, [])
            await db.areaname.delete_many(where={"areaId": row.id, "name": {"notIn": names}})
            if names:
                await db.areaname.create_many(
                    data=[{"areaId": row.id, "name": name} for name in names],
                    skip_duplicates=True,
                )

        return await db.area.count(), await db.areaname.count()
    finally:
        await db.disconnect()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CACHE)
    parser.add_argument(
        "--offline",
        action="store_true",
        help="fail instead of downloading when the cached CSV is missing",
    )
    args = parser.parse_args(argv)

    csv_path: Path = args.csv
    if not csv_path.exists():
        if args.offline:
            print(f"seed_areas: missing cache {csv_path} (offline mode)", file=sys.stderr)
            return 1
        download_dataset(csv_path)

    areas, aliases, skipped = read_areas(csv_path)
    missing_coordinates = [area["pincode"] for area in areas if area["lat"] is None]

    total_areas, total_aliases = asyncio.run(seed_areas(areas, aliases))

    print(f"seed_areas: {len(areas)} Delhi PINs upserted")
    print(f"seed_areas: {len(missing_coordinates)} without coordinates")
    print(f"seed_areas: {len(skipped)} skipped (no usable centre): {', '.join(skipped) or '-'}")
    print(f"seed_areas: {total_aliases} area-name aliases present")
    print(f"seed_areas: {total_areas} areas present in the database")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
