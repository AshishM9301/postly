# T-014 · Areas API: PIN lookup, GPS nearest, name search

- status: ready
- quest: Q1
- depends: T-013
- owner: -
- updated: -
- files: backend/app/api/v1/areas.py, backend/app/api/v1/categories.py, backend/app/schemas/area.py, backend/app/services/geo.py, backend/tests/test_areas.py

## Goal

Let a user find their area three ways — type a PIN code, let the browser detect GPS, or search by name —
and let the app show the areas around them. All three must work with **zero external calls** on the hot
path, using the seeded local data.

## Done when

- [ ] `GET /api/v1/areas/search?q=110019` returns the area with pincode `110019` (exact PIN match first).
- [ ] `GET /api/v1/areas/search?q=karol` returns areas whose name or district matches, case-insensitively,
      with a bounded result count.
- [ ] `GET /api/v1/areas/detect?lat=28.63&lng=77.07` returns the nearest area **with `distance_meters`**,
      and the distance is correct to within a metre or two (check against a known pair of coordinates).
- [ ] `GET /api/v1/areas/detect` with coordinates outside Delhi returns the nearest area anyway, with its
      distance, or a `404 area_not_found` if nothing is within the threshold — pick one behaviour and document
      it in `docs/API.md`.
- [ ] `GET /api/v1/categories` returns the 9 seeded categories in `sortOrder`.
- [ ] `pytest -q` covers all three lookups plus the distance calculation (a known pair → a known distance).
- [ ] No request in this task calls out to the internet. (Nominatim is optional label enrichment and is
      **not** part of this task — see the notes.)

## Notes / gotchas

- Haversine on the earth radius (6,371,000 m). Return the distance in metres as an integer.
- **Do not** use PostGIS. Plain `Float` columns plus a Haversine calculation in Python or SQL is enough for
  103 areas.
- If you do the nearest-area search in SQL, remember that a naive formula on a spherical earth is fine at
  this scale; keep the SQL readable and test it against a Python reference implementation.
- Search must be a LIKE/ILIKE over `name` and `district`, and also an exact match on `pincode` — a user
  typing six digits means the PIN, not a fuzzy name.
- The optional reverse-geocode label (Nominatim) is deliberately **out of scope** here. If you add it later:
  ≤1 req/s, a real User-Agent, no autocomplete, cache the result in the DB, and make the provider swappable.
- Throttle: a public endpoint that scans the table is a DoS target. Add a simple bound and cache.

## Research notes

The dataset and its quirks: `docs/GEO_DATA.md`. The Nominatim policy (for the optional later step) is
summarised in `docs/GEO_DATA.md` §3.

The endpoint contract to implement: `docs/API.md` §3. If you change the response shape, update `docs/API.md`
in the same task.

## Work log

## Report

## Manager review
