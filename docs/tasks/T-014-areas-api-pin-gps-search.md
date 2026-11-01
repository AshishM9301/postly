# T-014 · Areas API: PIN lookup, GPS nearest, name search

- status: done
- quest: Q1
- depends: T-013
- owner: s-20261101-0810
- updated: 2026-11-01 08:45
- files: backend/app/api/v1/areas.py, backend/app/api/v1/categories.py, backend/app/api/v1/router.py, backend/app/schemas/area.py, backend/app/services/geo.py, backend/tests/test_areas.py, docs/API.md

## Goal

Let a user find their area three ways — type a PIN code, let the browser detect GPS, or search by name —
and let the app show the areas around them. All three must work with **zero external calls** on the hot
path, using the seeded local data.

## Done when

- [x] `GET /api/v1/areas/search?q=110019` returns the area with pincode `110019` (exact PIN match first).
- [x] `GET /api/v1/areas/search?q=janakpuri` returns the area whose name matches, case-insensitively,
      with a bounded result count (`?q=south` matches the district).
      **Manager correction (2026-11-01):** the original example `?q=karol` returns `[]` — no seeded area
      name contains "karol" (PIN 110005 is named `Desh Bandhu Gupta Road`; "Karol Bagh SO" is one of its
      eight offices, but only one name per PIN is stored). The filter rule is proven; the missing
      locality names are tracked in **T-014b**.
- [x] `GET /api/v1/areas/detect?lat=28.63&lng=77.07` returns the nearest area **with `distance_meters`**,
      and the distance is correct to within a metre or two (check against a known pair of coordinates).
- [x] `GET /api/v1/areas/detect` with coordinates outside Delhi returns the nearest area anyway, with its
      distance, or a `404 area_not_found` if nothing is within the threshold — pick one behaviour and document
      it in `docs/API.md`.
- [x] `GET /api/v1/categories` returns the 9 seeded categories in `sortOrder`.
- [x] `pytest -q` covers all three lookups plus the distance calculation (a known pair → a known distance).
- [x] No request in this task calls out to the internet. (Nominatim is optional label enrichment and is
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

- 2026-11-01 s-20261101-0810: implemented search / detect / categories, the pure Haversine service, a bounded
  60 s nearest-area cache, 9 tests; documented the no-cutoff detect behaviour; verified live against the
  seeded 103 areas.

## Report

### 2026-11-01 · worker s-20261101-0810

- changed:
  - `backend/app/services/geo.py` — framework-free `haversine_meters` (R = 6,371,000 m), `AreaPoint` and
    `nearest_area` (stable pincode-ordered tie-break, integer metres).
  - `backend/app/schemas/area.py` — `AreaOut`, `AreaDetection` (`distance_meters`), `CategoryOut`
    (`sort_order`).
  - `backend/app/api/v1/areas.py` — `GET /areas/search` (6 digits → exact PIN only; otherwise bounded
    case-insensitive `ILIKE` over name/district, `limit` 1–25 default 10) and `GET /areas/detect`
    (validated lat/lng, nearest always, no cut-off, 404 only when no active areas). Candidate list is
    capped at 500 and cached in-process for 60 s (`clear_area_cache()` for tests).
  - `backend/app/api/v1/categories.py` — `GET /categories`, ordered by `sortOrder`.
  - `backend/app/api/v1/router.py` — wire both routers.
  - `backend/tests/test_areas.py` — 9 tests: exact PIN, six-digit no-name-fallback, name/district search +
    bound, detect distance vs Python reference, outside-Delhi behaviour, invalid-coordinate 422, category
    order, and the Haversine known pair/tie-break.
  - `docs/API.md` §3 — search params/semantics, detect no-cutoff behaviour + error, and the categories shape.
- verified (live, API restarted to load the new routers):
  - `GET /areas/search?q=110019` → one area, `110019 / Alaknanda / SOUTH EAST`.
  - `GET /areas/search?q=janakpuri` → `110058 / Janakpuri A 3`; `?q=south&limit=3` → three district
    matches, ordered by pincode.
  - `GET /areas/detect?lat=28.63&lng=77.07` → `110058`, `distance_meters: 1124`; an independent Python
    Haversine gives **1124**.
  - `GET /areas/detect?lat=0&lng=0.5` → `110073`, `distance_meters: 8683093` (nearest anyway, as documented).
  - `GET /categories` → 9 rows in order 1..9 (`pothole` … `other`).
  - `python -m pytest -q` → **38 passed** (9 new); `ruff check .` → all checks passed;
    `ruff format --check .` → 30 files already formatted.
  - `/openapi.json` exposes `/api/v1/areas/search`, `/api/v1/areas/detect`, `/api/v1/categories`.
- issues / notes:
  - **`q=karol` currently returns an empty list**, and that is correct for the seeded names: PIN 110005 was
    named `Desh Bandhu Gupta Road` by T-013's main-office rule, and no seeded `name`/`district` contains
    "karol". Name search is proven with `q=janakpuri` and district search with `q=south`. If the manager
    expects Karol Bagh specifically, that is a T-013 naming decision, not a filter bug.
  - `GET /areas/{id}` (listed in `docs/API.md` §3) was **not** implemented: it is not in this task's
    `## Done when` and "one area with post counts" depends on the posts API (T-015). Left for the task that
    owns post counts.
  - The 60 s cache is process-local; a seed re-run is visible within a minute (or on restart). No external
    calls anywhere in the request path.
- next: T-015 (post CRUD) waits on T-011 + T-014; both are now at review.

## Manager review

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**, with one done-when example corrected by me (the manager owns task files) and a
  **follow-up task T-014b** opened for the gap the example exposed. The API itself is correct: every rule
  the task states is implemented and I re-proved it live. The one example that does not hold — `?q=karol` —
  fails because of the *seeded data*, not because of the filter, and it cannot be fixed inside T-014's file
  list (it needs a schema change), so it becomes its own task instead of a silent pass.
- checked (re-run by the manager; nothing taken from the worker's report):
  - `docker compose exec api python scripts/seed_areas.py` was already applied, so the live API sees the 103
    real rows. `/openapi.json` now lists `/api/v1/areas/search`, `/api/v1/areas/detect` and
    `/api/v1/categories`; `GET /api/v1/health` → `{"status":"ok","db":"ok"}`.
  - **Exact PIN first:** `GET /api/v1/areas/search?q=110019` → one row, `110019 / Alaknanda / SOUTH EAST`.
    `q=110005` → `110005 / Desh Bandhu Gupta Road / CENTRAL`.
  - **Case-insensitive name and district, bounded:** `q=janakpuri` → `110058 / Janakpuri A 3`;
    `q=south&limit=3` → three district matches ordered by pincode (`110013`, `110014`, `110016`).
    `limit=0` → 422 `validation_error` (`greater_than_equal`), `limit=26` → 422 (`less_than_equal`),
    `q=` → 422 (`string_too_short`). The bound is real.
  - **Detect, with the distance re-derived by me.** `GET /api/v1/areas/detect?lat=28.63&lng=77.07` →
    `110058 / Janakpuri A 3`, `distance_meters: 1124`. I recomputed it independently from the `areas` table
    with my own Haversine (R = 6,371,000) — **1124 m, identical**, and my own scan of all 103 rows picks the
    same nearest area. `lat=0&lng=0.5` → `110073 / Ujwa`, `distance_meters: 8683093`; my reference gives the
    same figure. `lat=91` → 422 `validation_error`.
  - **Categories.** `GET /api/v1/categories` → the 9 seeded rows in `sort_order` 1..9 (`pothole`, `water`,
    `garbage`, `electricity`, `roads`, `streetlight`, `noise`, `drainage`, `other`).
  - **Tests.** `docker compose exec api python -m pytest -q` → `38 passed, 1 warning` (the warning is the
    pre-existing Starlette `httpx` deprecation). The new file has 9 tests: exact PIN, six-digit-no-name-
    fallback, name search + bound, district search, detect distance vs a Python reference, outside-Delhi
    behaviour, invalid coordinates, category order, and the Haversine known pair (1° of longitude at the
    equator = **111,194.93 m** — I recomputed it: `2π·6371000/360 = 111194.9266`).
  - **Lint / format.** `ruff check .` → `All checks passed!`; `ruff format --check .` → `30 files already
    formatted`.
  - **No internet on the hot path.** A search of `backend/app` for `requests|httpx|urllib|aiohttp|urlopen|
    socket|nominatim` → **no files found**. There is no HTTP client in the backend at all; the three
    endpoints only touch Postgres through Prisma.
  - **The docs match the code.** `docs/API.md` §3 now states the six-digit-is-a-PIN rule, the `limit`
    default/cap, the detect no-cut-off behaviour and the 404 condition, and shows the real response shapes
    (`distance_meters`, `sort_order`).
- the one gap I found, traced to its root cause:
  - `GET /api/v1/areas/search?q=karol` → `{"data":[]}`. The worker reported this honestly; I confirmed it
    live and traced it: the `Area` table stores **one** name per PIN — the main office's — and for PIN
    110005 that is `Desh Bandhu Gupta Road SO` (the first `PO` row in file order). The other seven offices
    of that PIN include **`Karol Bagh SO`** at 28.6500278/77.1938333, but that name is not stored, so it is
    not searchable. The filter itself is right: it matches `name` and `district` case-insensitively, as the
    task's "Notes / gotchas" require, and the fixture test proves it (`q=KAROL` → the fixture "Karol Test
    Bagh"). The gap is **data coverage**, and it hits users: people type neighbourhood names, not post
    office names ("Karol Bagh", "Janakpuri" happens to work only because that PIN's main office is
    `Janakpuri A 3`; "AGCR", "NDC NDHO" and "Union Public Service Commission" are not neighbourhood names).
  - I corrected the done-when example above to the check that is actually true (`?q=janakpuri`) and kept the
    gap visible instead of deleting it. The fix cannot be done inside T-014's `files:` list — it needs a new
    table/column plus a seed backfill — so it is **T-014b**, not a rework of this task.
- notes (no action required, carried forward):
  - **`LIKE` wildcards in `q` are not escaped.** `q=%` returns arbitrary rows (bounded by `limit`), and so
    does `q=_`. Prisma's `contains` maps to `ILIKE` without escaping. Impact is small (103 rows, ≤ 25
    results), but a `%` query is a full scan. T-014b should escape `%`/`_`.
  - **`GET /areas/{id}` is listed in `docs/API.md` §3 but does not exist.** The worker's reasoning is sound
    (its purpose is "one area with post counts", which needs the posts API from T-015), but the doc
    advertises an endpoint that 404s. T-015/T-020 must either implement it or mark it planned.
  - The nearest-area candidate list is capped at 500 rows and cached in-process for 60 s; the cache is
    per-process, so a seed re-run is visible within a minute. With 103 areas this is belt-and-braces.
  - The search path queries the database on every request (only `detect` is cached). Fine at this size; if
    the table grows, cache the search too.
  - `docs/API.md` §3 should also record that `q` matches substrings, not prefixes — a user typing "nag"
    gets "Janakpuri A 3", which is surprising but intended by the ILIKE rule.
- next: **T-014b** (area name aliases) and then **T-015** (post CRUD) — the latter needs T-011 and T-014 and
  must pin the `owner_key` encoding and the DELETE transport in `docs/API.md`.
