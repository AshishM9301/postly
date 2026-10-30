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

**Delhi coverage (verified by streaming the file):** 550 rows → **103 distinct PIN codes, all 103 with
valid latitude/longitude.** Districts present: `CENTRAL`, `EAST`, `NEW DELHI`, `NORTH`, `NORTH EAST`,
`NORTH WEST`, `SHAHDARA`, `SOUTH`, `SOUTH WEST`, `South East`, `WEST`.

### Known data quirks
1. **Mixed casing in `district`** — the raw file contains both `SOUTH WEST` and `South East`. Normalise with
   `district.strip().upper()`.
2. **`officetype`** is `SO` (sub office = main office), `BO` (branch office), and the `delivery` column
   says `Delivery` / `Non-Delivery`. A PIN can have several offices.
3. **`officename` includes the office type suffix** — `Baroda House SO`, `Chawri Bazar SO`. Strip
   ` SO` / ` BO` / ` PO` / ` S.O.` / ` B.O.` to get a locality name.
4. **Some rows have `NA` for coordinates** in other states; treat `NA` as missing everywhere.
5. `officename` is a *post office* name, which is a good locality proxy for Delhi (`Delhi GPO`,
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

`backend/scripts/seed_areas.py` (task T-013):

```
for each row where statename.strip().upper() == 'DELHI':
    pincode, office name, officetype, district, lat, lng
group by pincode:
    main office  = the row with officetype == 'SO', else the most common name
    name         = strip_office_suffix(main office name)
    district     = district.strip().upper()
    lat, lng     = main office coordinates
    radiusMeters = max(haversine(center, other offices of this pin)), floor 1500
    officeCount  = number of offices for this pin
```

Idempotent: re-running updates rows instead of duplicating them (upsert on `pincode`).

**Done when:** 103 Delhi PINs inserted, 0 without coordinates, districts upper-cased, re-running the seed
does not change the row count.

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
