# GEO DATA — Delhi PIN codes

An **Area** is one Delhi PIN code. Posts belong to an area; the area decides who sees them (Nearby,
For You) and how they are grouped.

## 1. Source

| | |
|---|---|
| File | `pincode.csv` |
| URL | `https://raw.githubusercontent.com/ghousekw/india-pincodes/master/pincode.csv` |
| Licence | **CC0 1.0 Universal** (public domain dedication) — verified in the repo's `LICENSE` |
| Structure | India Post: `circlename, regionname, divisionname, officename, pincode, officetype, delivery, district, statename, latitude, longitude` |
| Size | 165,627 rows (all India) |

**Delhi coverage (verified by streaming the file):** 550 rows → **103 distinct PIN codes**. Districts present:
`CENTRAL`, `EAST`, `NEW DELHI`, `NORTH`, `NORTH EAST`, `NORTH WEST`, `SHAHDARA`, `SOUTH`, `SOUTH WEST`,
`South East`, `WEST`.

### Known data quirks
1. **Mixed casing in `district`** — the raw file contains both `SOUTH WEST` and `South East`. Normalise with
   `district.strip().upper()`.
2. **`officetype` is `PO` / `BO` / `HO` in this file** — measured: 403 `PO`, 135 `BO`, 12 `HO`; there are
   **no `SO` rows**. The `PO` rows are the sub offices (their names still end in `SO`), so the seed prefers
   `SO` if one ever appears, then `PO`, then `HO`. The `delivery` column adds `Delivery` / `Non Delivery`.
3. **`officename` includes the office type suffix** — `Baroda House SO`, `Chaukhandi B.O`,
   `L. M. Nagar S.O`, `Panchsheel Enclave Post Office`. Some also carry a trailing district qualifier
   (`Saket SO South Delhi`, `Tilak Nagar S.O (West Delhi)`). Strip the type **and** the qualifier; the seed
   strips both.
4. **Coordinates are dirty.** 5 rows have `NA`; **18 more have coordinates outside Delhi** (e.g.
   `24.8715/86.2071`, `22.0/77.0`, `32.6439/74.0469`) and one is inside the bounding box but ~37 km from the
   rest of its PIN (`Garhi Mandu BO` at `28.38/77.12`). The seed treats out-of-bbox values as missing and
   ignores an office more than 20 km from the PIN's main office. Without this, the worst PIN radius would be
   **4,406 km**; with it, the maximum is **11,869 m**.
5. **A PIN's rows can disagree on `district`** — 23 of the 103 PINs mix districts (e.g. 110003 has `SOUTH`,
   `SOUTH EAST` and `NEW DELHI` rows). The seed takes the main office's district.
6. `officename` is a *post office* name, which is a good locality proxy for Delhi (`Delhi GPO`,
   `Panchsheel Enclave Post Office`, `Karol Bagh SO`) but is not always the neighbourhood people call it.
   Fine for PIN-level areas.

### Rejected alternatives (and why)
| Source | Why not |
|---|---|
| OSM Overpass (`addr:postcode` post offices) | Verified live for Delhi: only **18 distinct PINs** — far too thin. Useful for enrichment, not for the area list. |
| OSM full extract (Geofabrik, 1.63 GB) | Complete and ODbL, but a 1.6 GB download to build 103 rows. Overkill. |
| `data.gov.in` "Post Office PIN Code" | Official, but **no coordinates**. Good fallback for names, useless for GPS matching. |
| Community CSVs (`bilal-webdev/…`, `code-kasha/bharat-post-dir`) | 0–1 stars, unvetted provenance. Use only after validation, never as the primary. |

## 2. Seed rule

`backend/scripts/seed_areas.py` (tasks T-013, T-014b):

```
for each row where statename.strip().upper() == 'DELHI':
    pincode, office name, officetype, district, lat, lng
    drop coordinates that are NA or outside DELHI_BBOX (28.30-29.00 N, 76.80-77.60 E)
group by pincode:
    main office  = first SO, else first PO, else first HO, else the most common name
    name         = strip_office_suffix(main office name)  # type + district qualifier
    district     = district.strip().upper()
    lat, lng     = main office coordinates
    radiusMeters = max(haversine(center, other offices), floor 1500)
                   ignoring offices > 20 km from the centre (bad coordinates)
    officeCount  = number of distinct office names for this pin
    aliases      = every distinct strip_office_suffix(office name) for this pin
                   -> one AreaName row each (same PIN only)
```

Idempotent: re-running updates rows instead of duplicating them (upsert on `pincode`). Aliases are reconciled
per area (stale names deleted, current names inserted with `ON CONFLICT DO NOTHING`). The CSV is cached in
`backend/.cache/pincode.csv` (gitignored); the script downloads it if missing and `--offline` refuses to.

**Verified result (2026-11-01):** 103 PINs inserted, **0** without coordinates, 0 skipped. District casing and
suffix stripping checked with SQL (`0` rows with a non-upper district, `0` names ending in an office suffix).
Radius range **1500–11,869 m**; officeCount **1–23**. Re-running the seed leaves the row count at 103 and the
`md5(string_agg(...))` snapshot unchanged (`899a7e7e37aaaea8cb3c527f4e716e01`).

**Aliases (T-014b):** **549** `area_names` rows, **547** distinct names, **0** orphans, **0** duplicate
`(area_id, name)` pairs. The 549 vs 547 gap is **cross-PIN**, not within-PIN: two locality names exist in two
different PINs (`Sant Nagar` in 110065 and 110084, `Shivaji Park` in 110026 and 110032), so each area keeps its
own row — `@@unique([areaId, name])` is per area and never merges them. Example: PIN `110005` keeps
`Desh Bandhu Gupta Road` as its display name and also stores `Karol Bagh`, `Sat Nagar`, `Anand Parbat`, … as
searchable aliases. Search matches these plus `Area.name` and `Area.district`.

## 3. Runtime resolution — zero external calls on the hot path

| User action | How it resolves | External calls |
|---|---|---|
| Types a PIN code | exact match on `Area.pincode` | 0 |
| Browser GPS | `navigator.geolocation` → Haversine to the nearest seeded area → auto-select, show distance | 0 |
| Searches a name | local `ILIKE` over `Area.name` / `district` | 0 |
| Optional label | reverse geocode through **Nominatim** to name the spot | 1 (cached, on explicit action only) |

### Nominatim rules (public instance policy — respect them)
- Max **1 request per second**.
- Must send a real `User-Agent` / `Referer` identifying the app.
- **No autocomplete** — only geocode after the user commits to a search.
- **No bulk postcode queries** on the public instance (we use the dataset instead).
- Cache results in the DB; make the provider swappable so it can be self-hosted later.
- Never send personal data to it.

Other mirrors available if the main one is busy: `overpass.kumi.systems`, `z.overpass-api.de`,
`photon.komoot.io`. Self-hosting Nominatim from a Delhi extract is the long-term answer.

## 4. Nearby

`GET /feed/nearby?lat=&lng=&radius_m` — bounding-box pre-filter in SQL, then exact Haversine ordering.
Default radius 5 km, max 25 km. Falls back to the selected area when the device has no location permission.

## 5. Future: ward-level areas

Delhi has 11 districts and 70 wards (MCD + NDMC + DDA). Wards are the better unit for "local problems".
They are available as OSM administrative relations (`admin_level` 8/9) and from the LGD (Local Government
Directory). Upgrading means adding a `boundary` polygon to `Area` and switching the nearest-area lookup to
point-in-polygon. Tracked as a Q4 task; PIN-level is the MVP.
