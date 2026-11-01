# T-014b · Area name aliases: search every locality name of a PIN

- status: done
- quest: Q1
- depends: T-013, T-014
- owner: s-20261101-0810
- updated: 2026-11-01 08:54
- files: backend/prisma/schema.prisma, backend/prisma/migrations/, backend/scripts/seed_areas.py, backend/app/api/v1/areas.py, backend/tests/test_areas.py, backend/tests/test_seed_areas.py, docs/API.md, docs/GEO_DATA.md, docs/DATA_MODEL.md

## Goal

A user who types a neighbourhood name — "Karol Bagh", "Saket", "Lajpat Nagar" — must find the PIN that
contains it. Today the `Area` table stores exactly **one** name per PIN (the main office's), so
`GET /api/v1/areas/search?q=karol` returns `{"data":[]}` even though `Karol Bagh SO` is one of PIN 110005's
eight offices. Store the PIN's office names as searchable aliases and match them, so name search covers what
people actually type instead of only what the main post office happens to be called.

## Done when

- [x] `docker compose exec api python scripts/seed_areas.py` → still `103 Delhi PINs upserted`, and the alias
      rows are populated (`select count(*) from area_names;` → more than 103, at most the number of distinct
      office names in the dataset).
- [x] `curl "http://localhost:8000/api/v1/areas/search?q=karol"` → the area with pincode `110005` (Karol
      Bagh is one of its offices).
- [x] `curl "http://localhost:8000/api/v1/areas/search?q=janakpuri"` → still exactly one area, `110058`
      (the main-office name still matches).
- [x] `curl "http://localhost:8000/api/v1/areas/search?q=%25"` → `{"data":[]}` — the `%` is a literal
      character, not a LIKE wildcard (today it returns arbitrary rows). `q=_` behaves the same.
- [x] `docker compose exec api python -m pytest -q` → all tests pass, including new ones for the alias
      match and the wildcard escaping.
- [x] `docker compose exec api ruff check .` → `All checks passed!` and
      `docker compose exec api ruff format --check .` → all files already formatted.
- [x] `docs/API.md` §3 and `docs/GEO_DATA.md` describe the alias storage and the search semantics.

## Notes / gotchas

- **Prefer a separate `AreaName` table** (`area_id`, `name`) over a `String[]` column: Prisma can only do an
  exact `has` match inside a Postgres scalar array, not a substring `ILIKE`, so the search needs a join
  either way — but a table also keeps the schema readable and the rows inspectable.
- The Prisma schema is the single source of truth → a new model needs a migration under
  `backend/prisma/migrations/`. The `api` container runs `python -m prisma migrate deploy` on boot, so the
  migration must be valid for Postgres 16 and idempotent with the rest of the chain.
- `Area` is referenced by `posts.area_id` and `area_follows.area_id`. The alias table must cascade on area
  delete and must never touch `Area.id` (the ids are cuids that `posts` already point at).
- Aliases must be **suffix-stripped but readable** (`Karol Bagh`, not `Karol Bagh SO`). Reuse
  `strip_office_suffix` from `backend/scripts/seed_areas.py`; it is already unit-tested.
- Every alias must belong to that same PIN — no cross-PIN leakage — and the area's own `name` must stay
  searchable (it is the display name).
- Escape `%`, `_` and `\` in the user's `q` before it reaches `ILIKE`, or switch to a non-pattern
  comparison. Today `q=%` returns rows because Prisma's `contains` does not escape.
- The alias list must be **re-derivable from the CSV**, not pasted into the code: the raw dataset is only in
  the gitignored cache `backend/.cache/pincode.csv`.
- The `Area.officeCount` column counts distinct office names — keep it consistent with the alias rows.
- `docs/API.md` §3 still lists `GET /areas/{id}` ("one area with post counts"), which does not exist yet.
  T-015 owns that one.

## Research notes

- The 103 Delhi PINs, their office names and the dataset quirks: `docs/GEO_DATA.md`. The seed script already
  groups the CSV by PIN (1–23 offices per PIN); PIN 110005 is the worked example — its offices include
  `Desh Bandhu Gupta Road SO` (the chosen area name) and `Karol Bagh SO`.
- `strip_office_suffix`, `Office`, `build_area` and the PIN grouping live in
  `backend/scripts/seed_areas.py`; `haversine_meters`, `AreaPoint` and `nearest_area` in
  `backend/app/services/geo.py`; the endpoints in `backend/app/api/v1/areas.py`.
- T-013's main-office rule: first `PO` row in file order, else `HO`, else the most common name. The alias
  task must **not** change which name is displayed — only which names are searchable.

## Work log

- 2026-11-01 s-20261101-0813: task opened by the manager after verifying T-014 — `?q=karol` returned `[]`
  because only one name per PIN is stored (see the T-014 manager review).
- 2026-11-01 s-20261101-0810: added the `AreaName` model + migration, seeded 549 aliases, matched them in
  search, escaped LIKE wildcards; 41 tests pass.

## Report

### 2026-11-01 · worker s-20261101-0810

- changed:
  - `backend/prisma/schema.prisma` — new `AreaName` model (`areaId`, `name`, `createdAt`), cascade delete,
    `@@unique([areaId, name])`, `@@index([name])`; `Area.names` relation.
  - `backend/prisma/migrations/20261101084500_area_names/migration.sql` — creates `area_names` + indexes +
    FK with `ON DELETE CASCADE`.
  - `backend/scripts/seed_areas.py` — `alias_names()` (distinct, suffix-stripped), `build_areas()` returns
    aliases per PIN, `seed_areas()` reconciles them: delete stale names, `create_many(skip_duplicates=True)`;
    output now includes `549 area-name aliases present`.
  - `backend/app/api/v1/areas.py` — search now matches `Area.name`, `Area.district` **and**
    `AreaName.name` via `names.some`; `_escape_like()` makes `%`, `_`, `\` literal.
  - `backend/tests/test_areas.py` — fixture aliases + tests for alias match, literal `%`/`_`/`\`/`alias%`.
  - `backend/tests/test_seed_areas.py` — alias derivation/dedup/one-PIN-only test.
  - `docs/API.md` §3, `docs/GEO_DATA.md` §2, `docs/DATA_MODEL.md` — alias storage, counts and search
    semantics (17 → 18 tables).
- verified (real output):
  - `migrate deploy` → applied `20261101084500_area_names`; `prisma generate` → client regenerated.
  - seed → `103 Delhi PINs upserted`, `0 without coordinates`, `0 skipped`, **`549 area-name aliases
    present`**, `103 areas present`. Second run identical; SQL: `aliases=549`, `unique_pairs=549`,
    `orphans=0`.
  - `GET /areas/search?q=karol` → `110005 / Desh Bandhu Gupta Road / CENTRAL` (matched alias `Karol Bagh`).
  - `GET /areas/search?q=janakpuri` → exactly one: `110058 / Janakpuri A 3`.
  - `GET /areas/search?q=%25` → `{"data": []}`; `q=_` → `{"data": []}`; `q=\` → `{"data": []}`.
  - `python -m pytest -q` → **41 passed**; `ruff check .` → all checks passed;
    `ruff format --check .` → all files already formatted.
- issues / notes:
  - I also updated `docs/DATA_MODEL.md` (17 → 18 tables + an `AreaName` section) because that document says
    it is updated in the same task when the schema changes. `AGENTS.md` §11 still says "17 models" — that is
    the manager's snapshot to refresh.
  - One suffix collision exists across office names (549 rows, 547 distinct names); the unique constraint is
    `(area_id, name)`, so this is a non-issue within a PIN.
  - Search still treats six digits as an exact PIN and never joins aliases for that path.
- next: T-015 (post CRUD) depends on T-011 + T-014/T-014b; T-020 will consume the expanded name search.

## Manager review

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**. Every done-when check passes when I re-run it, and the alias set is exactly what the
  dataset implies — I re-derived all 549 rows from the CSV with my own script (own suffix regex, no import of
  `scripts.seed_areas`) and got **0 mismatches**. One explanation in `docs/GEO_DATA.md` was wrong and I
  corrected it myself; the code is right.
- checked (re-run by the manager; nothing taken from the worker's report):
  - `docker compose exec api python scripts/seed_areas.py` → `103 Delhi PINs upserted`, `0 without
    coordinates`, `0 skipped`, **`549 area-name aliases present`**, `103 areas present in the database`.
    I ran it twice more: the alias snapshot `md5(string_agg(area_id||'|'||name))` stayed
    `f43e8b6ca8da23801d966999ec35119b` and the area snapshot stayed `e31905ef5b21a45892e2a7ad7ad5d7fe` —
    idempotent, no churn.
  - **SQL:** `aliases=549`, `distinct names=547`, `orphan_aliases=0`, `unique (area_id,name) pairs=549`,
    `within-PIN duplicate pairs=0`.
  - **Independent re-derivation (the strong check).** My own script re-read the cached CSV, applied its own
    suffix regex and rebuilt the expected alias set for every PIN, then compared it with `area_names`:
    `expected alias rows: 549` = the DB's 549, **`mismatches: 0`**, no orphans, and every area's display
    name is searchable. So there is no cross-PIN leakage and nothing is missing.
  - **Live endpoints.** `GET /areas/search?q=karol` → `110005 / Desh Bandhu Gupta Road / CENTRAL` — the
    done-when's target, matched through the alias `Karol Bagh` (SQL confirms `Karol Bagh` → 110005 and
    `Saket` → 110017). `q=janakpuri` → exactly one row, `110058`. `q=KAROL` → the same row (case-insensitive
    on aliases). `q=desh bandhu` → the display name still matches. `q=anand parbat` → 110005 via an alias.
    `q=110019` → the exact PIN, unchanged.
  - **The wildcards are literal now.** `q=%25` → `{"data":[]}`, `q=_` → `{"data":[]}`, `q=\` →
    `{"data":[]}`. Before this task `q=%` returned arbitrary rows.
  - **Migration.** `python -m prisma migrate status` → `2 migrations found`, `Database schema is up to date!`.
    The new `20261101084500_area_names/migration.sql` creates `area_names` (PK, `created_at` default), the
    `name` index, the unique `(area_id, name)` index and the FK with `ON DELETE CASCADE ON UPDATE CASCADE` —
    so deleting an area takes its aliases with it, and `Area.id` is untouched.
  - **Tests.** `docker compose exec api python -m pytest -q` → `41 passed, 1 warning` (the pre-existing
    Starlette `httpx` deprecation). The new tests cover the alias match, the literal `%`/`_`/`\`/`alias%`
    cases, and the alias derivation (stripped, deduplicated, same PIN only).
  - **Lint / format.** `ruff check .` → `All checks passed!`; `ruff format --check .` → `30 files already
    formatted`.
  - **Nothing generated was committed:** `backend/prisma/generated/` is gitignored and does not appear in
    `git status`.
  - **Docs.** `docs/API.md` §3 now states the alias match and the literal-wildcard rule; `docs/DATA_MODEL.md`
    has the `AreaName` section and the corrected "18 tables"; `docs/GEO_DATA.md` §2 documents the alias
    derivation and the counts.
- correction I made (manager owns the docs):
  - `docs/GEO_DATA.md` explained the 549-vs-547 gap as "one collision after suffix stripping … which the
    `@@unique([areaId, name])` constraint absorbs". That is wrong on both counts: there are **no** within-PIN
    duplicate pairs (the `set()` in `alias_names` removes them before insert), and the gap is **cross-PIN** —
    `Sant Nagar` belongs to 110065 *and* 110084, `Shivaji Park` to 110026 *and* 110032. Those are two
    genuinely different Delhi localities that share a name, so each area must keep its own row; a per-area
    constraint must not merge them. I rewrote the paragraph with the measured numbers.
  - `AGENTS.md` §11 still said the schema holds "17 models" (the worker flagged it as the manager's job) —
    updated to 18 with the `AreaName` table, and the areas-API bullet now describes the alias search.
- notes (no action required, carried forward):
  - **The alias reconcile has one unreachable edge case.** It deletes stale rows with
    `delete_many(areaId=…, name: {notIn: names})`; Prisma turns `notIn: []` into "matches nothing", so a PIN
    with **zero** alias names would keep its old rows. Every PIN in the dataset has at least one office name,
    so it cannot happen today; `delete_many(areaId)` + re-create would remove the special case.
  - The seed reconciles only the 103 PINs present in the CSV — an area whose PIN leaves the dataset keeps its
    aliases.
  - `docs/API.md` §3 still advertises `GET /areas/{id}` ("one area with post counts"), which does not exist.
    T-015 owns it (already flagged in the T-014 review).
  - The frontend's generated `types.ts` is still stale (it knows only `/api/v1/health`). Re-run
    `npm run api:types` **on the host** before T-020 consumes the areas endpoints.
  - The alias table gives the search a `names.some` relation filter, so the query plan now joins
    `area_names`; with 549 rows that is free, and the `(name)` index is there if it ever is not.
- next: **T-015** (post CRUD) — it needs T-011 and T-014/T-014b, must implement `GET /areas/{id}`, and must
  pin the `owner_key` encoding and the DELETE transport in `docs/API.md` (still open from T-012).
