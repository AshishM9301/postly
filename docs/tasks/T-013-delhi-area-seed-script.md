# T-013 · Delhi area seed script

- status: done
- quest: Q1
- depends: T-010
- owner: s-20261101-0810
- updated: 2026-11-01 08:31
- files: backend/scripts/seed_areas.py, backend/tests/test_seed_areas.py, docs/GEO_DATA.md, backend/pyproject.toml, .gitignore

## Goal

Turn the CC0 India Post PIN dataset into the `Area` rows the app needs: one area per Delhi PIN code, with a
clean locality name, a normalised district, a centre coordinate and a radius. The script must be
re-runnable without duplicating rows, and it must not need the network once the CSV is cached.

## Done when

- [x] `python scripts/seed_areas.py` inserts **103 Delhi PINs**, and **0** of them lack a latitude or
      longitude (assert both numbers in the script's output).
- [x] Every `district` is upper-case and trimmed (`SOUTH WEST`, not `South East`).
- [x] Every `name` has the office-type suffix stripped (`Karol Bagh`, not `Karol Bagh SO`).
- [x] Every area's `radiusMeters` ≥ 1500 and is the max distance from the centre to that PIN's other
      offices.
- [x] Running the script twice changes nothing (idempotent — upsert on `pincode`).
- [x] The script works from a cached copy of the CSV (no network) and can download it if missing.
- [x] `pytest -q` includes a test for the normalisation rules (suffix stripping, district casing, `NA`
      coordinates) using small inline fixtures — not the whole 21 MB file.
- [x] `docs/GEO_DATA.md` is updated with the actual row counts and any new quirks found in the data.

## Notes / gotchas

- Source: `https://raw.githubusercontent.com/ghousekw/india-pincodes/master/pincode.csv` (**CC0 1.0**), columns
  `circlename, regionname, divisionname, officename, pincode, officetype, delivery, district, statename,
  latitude, longitude`. Full details and the verified numbers are in `docs/GEO_DATA.md`.
- The file is ~21 MB with 165,627 rows. Stream it (`csv.DictReader` over a urllib response) — do not load it
  into memory as a list of dicts.
- Filter with `statename.strip().upper() == "DELHI"`.
- Pick the **main office** per PIN: prefer `officetype == "SO"`, else the most common `officename`. The main
  office's coordinates become the area centre.
- The raw data has `NA` in the coordinate columns for some rows — treat that as missing.
- District casing is inconsistent in the source (`SOUTH WEST` vs `South East`). Normalise, do not assume.
- `officename` endings vary: ` SO`, ` BO`, ` PO`, ` S.O.`, ` B.O.`, ` Post Office`. Strip them all.
- Cache the CSV under `backend/.cache/` (gitignored) so re-running the seed is offline and fast.
- Write the counts to stdout — the manager verifies them from the real output.

## Research notes

Everything about the dataset is already measured and documented in `docs/GEO_DATA.md` §1 — do not
re-download and re-count it from scratch unless you are validating the seed script itself.

If you find a quirk that is not in `docs/GEO_DATA.md`, add it there (this file is the reference for later
sessions) and mention it in your report.

## Work log

- 2026-11-01 s-20261101-0810: implemented the streaming seed, offline cache + download, upsert, 11 fixture
  tests; ran it twice against the live DB; documented two new data quirks (PO/HO labels, dirty coordinates).

## Report

### 2026-11-01 · worker s-20261101-0810

- changed:
  - `backend/scripts/seed_areas.py` — streams `pincode.csv` with `csv.DictReader` (keeps only the 550 Delhi
    rows), caches under `backend/.cache/pincode.csv`, downloads it when missing (`--offline` refuses),
    normalises names/districts, picks the main office (SO → PO → HO → most common name), computes a
    Haversine radius (floor 1500 m) and upserts 103 `Area` rows on `pincode`.
  - `backend/tests/test_seed_areas.py` — 11 fixture-based tests: every suffix variant, district casing,
    `NA`/bogus coordinates, main-office preference, centre/name, radius calc and floor, the bad-coordinate
    cap, and the no-centre skip. No test reads the CSV.
  - `docs/GEO_DATA.md` — corrected the `officetype` claim (`PO`/`BO`/`HO`, no `SO`) and added the dirty
    coordinates + mixed-district quirks, the bbox/spread rules, and the measured results.
  - `.gitignore` — ignores `backend/.cache/` so the 21 MB download never enters git.
- data quirks found (new):
  - `officetype` has **no `SO`** rows at all: 403 `PO`, 135 `BO`, 12 `HO`. The `PO` names still end in `SO`,
    so the seed treats `PO` as the sub-office level.
  - **16 Delhi rows have non-Delhi or corrupt coordinates** (e.g. `24.8715/86.2071`, `22.0/77.0`,
    `32.6439/74.0469`) plus `Garhi Mandu BO` at `28.38/77.12` (inside the bbox, ~37 km from its PIN).
    Out-of-bbox values are treated as missing; an office > 20 km from the main office is ignored. Without
    this the worst radius was **4,406,519 m**; with it the max is **11,869 m**.
  - 23 of the 103 PINs mix districts across their rows; the seed uses the main office's district.
- verified (real output, in-container):
  - `python scripts/seed_areas.py` → `103 Delhi PINs upserted`, `0 without coordinates`, `0 skipped`,
    `103 areas present in the database`.
  - SQL: `areas=103`, `missing_coords=0`, `small_radius=0`, `bad_district=0`,
    `suffixed_names=0`, `min_radius=1500`, `max_radius=11869`, `office_count 1..23`.
  - Idempotency: second run → still 103 rows and the same snapshot
    `md5=899a7e7e37aaaea8cb3c527f4e716e01`.
  - Cache/network: `--offline --csv .cache/pincode.csv` → no download, same 103 rows;
    `--csv /tmp/pincode-test.csv` → `downloading …`, same 103 rows; `--offline` with a missing file → exit 1.
  - `python -m pytest -q` → **29 passed** (11 new); `ruff check .` → all checks passed;
    `ruff format --check .` → 25 files already formatted.
- issues / notes:
  - I added `backend/.cache/` to `.gitignore` (not in the original `files:` list, but the task requires the
    cache to be gitignored). The cache itself is on disk and untracked.
  - The bbox/spread cleaning is stricter than the task's literal "max distance to other offices": rows with
    obviously broken coordinates are treated as missing, same as `NA`. The rule and the numbers are written
    into `docs/GEO_DATA.md` so the manager can accept or reject it explicitly.
  - `backend/prisma` contains a `generated/` tree; running the seed **outside** the container from the repo
    root can shadow the installed `prisma` package. Run it from `backend/` (or in the container) as the task
    says.
- next: T-014 (Areas API: PIN lookup, GPS nearest, search) is now unblocked.

## Manager review

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**. I re-ran every `## Done when` check myself, re-derived the whole seed with an
  independent implementation that does not import `scripts.seed_areas`, and found **0 mismatches** on all 103
  rows. One number in `docs/GEO_DATA.md` was wrong (16 → 18); I corrected it myself, since the manager owns
  the docs.
- checked (re-run by the manager; the worker report was not taken on trust):
  - `docker compose exec api python scripts/seed_areas.py` → `103 Delhi PINs upserted`, `0 without
    coordinates`, `0 skipped (no usable centre): -`, `103 areas present in the database`, exit 0.
  - **SQL invariants:** `areas=103`, `count(distinct id)=103`, `count(distinct pincode)=103`, no empty ids,
    `missing_coords=0`, `bad_district=0` (no row where `district <> upper(btrim(district))`),
    `small_radius=0`, `suffixed_names=0` (my regex also covers `POST OFFICE`), `radius_meters` 1500–11869,
    `office_count` 1–23.
  - **Idempotent, re-proved:** I took my own snapshot before the first run
    (`md5(string_agg(pincode||'|'||name||'|'||district||'|'||lat||'|'||lng||'|'||radius_meters||'|'||office_count))`
    = `b4c08d9495af44ab0d6cae15146a7c83`) and re-took it after four more runs (seed, `--offline` seed,
    downloaded-CSV seed): **byte-identical**. `Area.id` is a cuid set on create and the upsert's `update`
    payload does not touch it, so area ids stay stable for `posts.area_id`.
  - **Independent re-derivation (the strong check).** I wrote a throwaway script that re-implements the
    grouping, the main-office choice, the haversine maths and the suffix rules straight from the task file
    — it does **not** import `scripts.seed_areas` — and compared all 103 rows against the database:
    `mismatches: 0` on name, district, centre, radius and office_count. It also reproduced the dataset
    facts: `550` Delhi rows, `103` PINs, `23` dirty-coordinate rows, `23` PINs mixing districts, `1` PIN with
    an office > 20 km from its centre. The script and the downloaded CSV were deleted afterwards.
  - **The one deviation from the literal done-when, accepted.** "radius = max distance to that PIN's other
    offices" is implemented with a 20 km spread cap, and it changes exactly one row: PIN 110053 Brahampuri,
    whose `Garhi Mandu BO` sits at `28.38/77.12` while the other seven offices of that PIN cluster at
    28.67–28.70 N / 77.25–77.30 E (36.9 km away) — a corrupt coordinate, not a real spread. Without the
    cleaning the worst radius is **4,406,519 m** (PIN 110043 `Gopal Nagar SO` vs `Kair B.O` at 31.77/76.00);
    I reproduced that number exactly with my own script. The cleaned maximum is **11,869 m**. The rule is
    documented in `docs/GEO_DATA.md` §2, so it is auditable — I accept it explicitly rather than by silence.
  - **Cache and network.** `--offline` with the cache → 103 areas, no download. `--offline --csv
    /tmp/definitely-missing.csv` → `seed_areas: missing cache /tmp/definitely-missing.csv (offline mode)`,
    exit 1. `--csv /tmp/pincode-manager-test.csv` → `downloading …` → 21,625,751 bytes → 103 areas. So the
    seed is offline-capable *and* can fetch the CSV when it is missing.
  - **Tests.** `docker compose exec api python -m pytest -q` → `29 passed, 1 warning` (the warning is the
    pre-existing Starlette `httpx` deprecation from `fastapi.testclient`). The new test file uses inline
    fixtures only — no test opens the 21 MB CSV, as the done-when requires.
  - **Lint / format.** `ruff check .` → `All checks passed!`; `ruff format --check .` → `25 files already
    formatted`.
  - **The 21 MB file stays out of git.** `git check-ignore -v backend/.cache/pincode.csv` →
    `.gitignore:44:backend/.cache/`; `git status` does not list it.
  - **The data claims in `docs/GEO_DATA.md` are true.** I measured `officetype` = 403 `PO` / 135 `BO` /
    12 `HO` and **no `SO` rows**, and the district values are exactly the eleven listed (including the
    mixed-case `South East`).
  - I read all 103 rows: names are real localities (`Karol Bagh`-style names such as `Baroda House`,
    `Rana Pratap Bagh`, `Janakpuri A 3`) plus a tail of post-office/institution names (`AGCR`,
    `DELHI GPO NDC`, `KALKAJI NDC`, `Union Public Service Commission`, `NDC DWARKA SEC-6`) — inherent to the
    dataset, and GEO_DATA already says the office name is only a locality proxy.
- correction I made (manager owns the docs):
  - `docs/GEO_DATA.md` said "**16** more have coordinates outside Delhi". Measured: 5 rows with `NA` and
    **18** out-of-bbox rows (23 dirty rows, 527 clean) — the worker's own report repeats the wrong figure.
    Corrected to 18. Everything else in the doc matches my measurements.
- notes (no action required, carried forward):
  - **The areas are not seeded on boot.** The `api` container runs `prisma migrate deploy` + uvicorn only, so
    a fresh stack has no `areas` rows (same for the 9 categories). T-014's API needs the seed to have run;
    the first run downloads the 21 MB CC0 CSV. Decide whether the seed belongs on boot or in a one-shot
    compose service.
  - **Search has to cope with office names.** Several `name` values are institutions or delivery hubs
    (`AGCR`, `NDC NDHO`, `Nodal Delivery Centre(Parcel) Rohini`), so T-014's name search should also match
    PIN, district and the raw office name. `region` is the useless constant `DivReportingCircle` for every
    Delhi row; `circle` is `Delhi Circle`.
  - `officeCount` counts **distinct office names**, not CSV rows.
  - `DELHI_BBOX` (28.30–29.00 N, 76.80–77.60 E) and `MAX_OFFICE_SPREAD_METERS` (20 km) are magic numbers in
    the script. They are documented in `docs/GEO_DATA.md` §2; re-validate both if the dataset is refreshed.
  - The worker flagged that `backend/prisma/generated/` can shadow the installed `prisma` package when the
    seed is run from the repo root. In the container (`/app` as cwd) `from prisma import Prisma` resolves to
    site-packages — a regular package beats a namespace directory — so the canonical in-container command is
    fine; `python -m prisma` (the CLI) is the one that can be shadowed.
  - Process: the worker added `backend/.cache/` to `.gitignore`, which was outside the task's `files:` list
    but required by the task text. Accepted.
- next: **T-014** (Areas API: PIN lookup, GPS nearest, name search) is unblocked and consumes these 103
  rows. T-015 still needs the `owner_key` encoding and the DELETE transport pinned in `docs/API.md`.
