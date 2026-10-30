# T-003 · FastAPI skeleton + Prisma client + health

- status: done
- quest: Q0
- depends: T-002
- owner: s-20261030-1934
- updated: 2026-10-30T20:40
- files: backend/app/main.py, backend/app/core/config.py, backend/app/core/__init__.py, backend/app/db/client.py, backend/app/db/__init__.py, backend/app/api/__init__.py, backend/app/api/v1/__init__.py, backend/app/api/v1/health.py, backend/app/api/v1/router.py, backend/tests/test_health.py, backend/pyproject.toml, docker-compose.yml

## Manager notes (2026-10-30, during the T-001 review)

A minimal skeleton already exists — do not start from zero:

- `backend/app/main.py` — FastAPI app with a lifespan that connects the Prisma client, and
  `/api/v1/health` that really queries the database (returns `{"status":"ok","db":"ok"}`).
- `docker-compose.yml` runs it; `GET http://localhost:8000/api/v1/health` works today.

This task is about making that skeleton **production-shaped**: settings from the environment, the Prisma
client in its own module, a proper `/api/v1` router tree, tests, and honest error handling.

## Goal

Stand up the FastAPI application with the structure every later task will grow into: a settings module
reading `.env`, a Prisma client singleton connected in the lifespan, a `/api/v1` router tree, and a health
endpoint that reports the database status honestly (not a hardcoded `ok`).

## Done when

- [x] `GET http://localhost:8000/api/v1/health` returns `200` with `{"status":"ok","db":"ok"}`.
- [x] `GET http://localhost:8000/api/v1/health` returns `503` with `db: "down"` when the database is
      unreachable (stop the db container and check — then start it again).
- [x] `docker compose exec api python -m pytest -q` passes with at least one real test.
- [x] `docker compose exec api ruff check .` and `ruff format --check .` are clean.
- [x] `docker compose exec api python -m prisma generate` still succeeds after the changes (the generated
      client must not be broken by imports).
- [x] The app starts and stops cleanly (no "event loop is closed" or "client not disconnected" warnings).

## Notes / gotchas

- Follow the folder layout in `AGENTS.md` §9 exactly — later tasks assume those paths.
- One Prisma client per process. Create it in `app/db/client.py`, connect in the lifespan
  (`await db.connect()`), disconnect on shutdown. Do not create clients per request.
- Settings come from `pydantic-settings`. Read `DATABASE_URL`, `SECRET_KEY`, `PEPPER`, `APP_ENV` and the
  moderation/rate-limit knobs from `.env.example`. Fail fast if `SECRET_KEY` is missing in a non-dev env.
- The API prefix comes from config (`API_PREFIX=/api/v1`), not hardcoded in two places.
- CORS: allow the web origin from config (`http://localhost:3000` in dev).
- The health route must actually query the database (e.g. `SELECT 1` through Prisma), otherwise it is a
  lie and every later smoke test trusts it wrongly.
- Keep the first test fast and hermetic — it should not need a migration to have run beyond what T-001 did.

## Research notes

Prisma client usage (async, `auto_register`, connect/disconnect) is documented in
`docs/research/00-versions.md` §4 and the prisma-client-py quickstart. Versions: `docs/research/00-versions.md` §3.

Learned in T-003 (2026-10-30):

- `prisma-client-py` 0.15.0 exposes `query_raw`, `execute_raw` and `query_first` on the `Prisma` client.
  `await db.query_raw("SELECT 1")` works with no model and no migration, which is why the health check uses it
  instead of `spikerow.count()`.
- One client (`app/db/client.py`) connected in the lifespan works under `TestClient` too. After the db
  container was stopped, `query_raw` raised and the route returned 503; after the db came back the **same**
  client recovered without restarting the API. No per-request clients are needed.
- Graceful shutdown requires the API to be PID 1. `sh -c "migrate && uvicorn"` leaves `sh` as PID 1, so
  uvicorn never sees SIGTERM and the lifespan shutdown never runs. The compose command uses
  `... && exec python -m uvicorn ...`; logs then show `Shutting down` / `Application shutdown complete`.
- `fastapi.testclient.TestClient` emits a `StarletteDeprecationWarning` about httpx/httpx2 (upstream, not our
  code). It does not fail the run.
- Settings: pydantic-settings 2.16.2 reads the compose-injected env vars; `env_file=".env"` is harmless in the
  container (no `.env` under `/app`) and helps local runs. `get_settings()` is cached with `lru_cache`, so the
  non-dev secret check runs once at import.

Add anything later T-010/T-015 learn about nested includes, transactions or raw SQL here.

## Work log

- 2026-10-30 s-20261030-1934: split the skeleton into `core/config.py`, `db/client.py`, `api/v1/{health,router}.py`,
  wired settings/CORS/lifespan in `main.py`, added a real health test, pinned pydantic-settings, added
  `exec` to the compose command for graceful shutdown, and ran the full verification (including db-down 503).

## Report

### 2026-10-30 · worker s-20261030-1934

- changed:
  - `backend/app/core/config.py` — `Settings` (pydantic-settings) for app/db/secrets/CORS/moderation/rate-limit
    knobs; non-dev runs fail fast without `SECRET_KEY`/`PEPPER`.
  - `backend/app/db/client.py` — single `Prisma()` client; `core/`, `db/`, `api/`, `api/v1/` `__init__.py` files.
  - `backend/app/api/v1/health.py` — real `SELECT 1` probe; 200 `{"status":"ok","db":"ok"}` / 503
    `{"status":"degraded","db":"down"}`.
  - `backend/app/api/v1/router.py` — v1 router tree; mounted with `settings.api_prefix` in `main.py`.
  - `backend/app/main.py` — lifespan connect/disconnect, CORS from settings, no hardcoded prefix/health.
  - `backend/tests/test_health.py` — one real test through `TestClient` against the database.
  - `backend/pyproject.toml` — pinned `pydantic-settings==2.16.2`, `testpaths = ["tests"]`.
  - `docker-compose.yml` — `exec` before uvicorn so SIGTERM reaches it (clean lifespan shutdown).
- verified (real output):
  - `curl /api/v1/health` → `{"status":"ok","db":"ok"}` / `HTTP 200`.
  - `docker compose stop db` then curl → `{"status":"degraded","db":"down"}` / `HTTP 503`;
    `docker compose start db` → `{"status":"ok","db":"ok"}` / `HTTP 200` without restarting the API.
  - `docker compose exec -T api python -m pytest -q` → `1 passed, 1 warning` (exit 0).
  - `ruff check .` → `All checks passed!`; `ruff format --check .` → `12 files already formatted`.
  - `python -m prisma generate` → `✔ Generated Prisma Client Python (v0.15.0) ...` (exit 0).
  - `docker compose stop api` → logs show `Shutting down` / `Waiting for application shutdown` /
    `Application shutdown complete` / `Finished server process`; no event-loop or disconnect warnings.
- issues:
  - `TestClient` emits an upstream `StarletteDeprecationWarning` (httpx/httpx2); harmless, not acted on.
  - `docker-compose.yml` is outside this task's `files:` list but the `exec` change is required by the
    clean-shutdown checkbox — flagging for the manager.
- next: T-004 (frontend scaffold + API proxy + health page) or T-010 once Q1 opens.

## Manager review

### 2026-10-30 · manager (independent verification, session s-20261030-2035)
- verdict: **accepted**
- checked (re-run by me, not trusting the report):
  - `GET /api/v1/health` → `HTTP 200` `{"status":"ok","db":"ok"}`
  - **database really down**: `docker compose stop db` → `HTTP 503` `{"status":"degraded","db":"down"}` (body
    captured from inside the container, not assumed)
  - **recovery**: `docker compose start db` → `HTTP 200` `{"status":"ok","db":"ok"}` **without restarting the
    API** — `StartedAt` unchanged and `RestartCount=0`, so the connection pool genuinely recovers
  - `docker compose exec -T api python -m pytest -q` → `1 passed, 1 warning`, exit **0**
  - `ruff check .` → `All checks passed!`; `ruff format --check .` → `12 files already formatted`
  - `python -m prisma generate` → `✔ Generated Prisma Client Python (v0.15.0)`
  - **clean shutdown**: `docker compose stop api` → `Shutting down` / `Waiting for application shutdown` /
    `Application shutdown complete.` / `Finished server process [1]`; no "event loop is closed" and no
    "client not disconnected" anywhere in the log
  - the health probe is a **real** query, not a stub: `db.query_raw('SELECT 1')` → `[{'?column?': 1}]`
  - **the image was genuinely rebuilt, not hot-patched**: a *fresh* container from `postly-api:latest` has
    `pydantic-settings 2.16.2` baked in and imports `app.core.config`, `app.db.client`, `app.api.v1.router`
    cleanly; the running container's image id equals the built image id
  - read the full diff: `backend/app/main.py`, `backend/pyproject.toml`, `docker-compose.yml`, plus the new
    `app/core/`, `app/db/`, `app/api/v1/`, `tests/` files
- notes:
  - **Scope flag accepted.** `docker-compose.yml` was outside `files:`, but the `exec` change was required
    by the clean-shutdown checkbox: with `sh -c "… && uvicorn …"`, `sh` is PID 1 and SIGTERM never reaches
    uvicorn, so the lifespan's `db.disconnect()` never runs and the container always dies mid-shutdown.
    With `exec`, uvicorn *is* PID 1 — confirmed by `Finished server process [1]`. `files:` widened.
  - `pydantic-settings` was added as an exact pin (`==2.16.2`); it is genuinely in the image, so a rebuild
    will not lose it.
  - `Settings` fails fast when `APP_ENV` is not a dev value and `SECRET_KEY`/`PEPPER` are missing — correct
    for the privacy guarantees in `docs/SECURITY.md`.
  - The editable install from the previous turn paid off here: the new subpackages were importable in the
    running container with no second copy of the source anywhere.
  - Known, harmless: pytest reports 1 warning — an upstream `StarletteDeprecationWarning` from FastAPI's
    `TestClient`. Left unsuppressed on purpose; silencing upstream warnings hides real ones. Revisit if it
    becomes noise.
- next: T-004 (frontend scaffold) and T-010 (the real schema) are both unblocked.

