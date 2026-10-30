# T-003 · FastAPI skeleton + Prisma client + health

- status: ready
- quest: Q0
- depends: T-002
- owner: -
- updated: -
- files: backend/app/main.py, backend/app/core/config.py, backend/app/core/__init__.py, backend/app/db/client.py, backend/app/db/__init__.py, backend/app/api/__init__.py, backend/app/api/v1/__init__.py, backend/app/api/v1/health.py, backend/app/api/v1/router.py, backend/tests/test_health.py, backend/pyproject.toml

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

- [ ] `GET http://localhost:8000/api/v1/health` returns `200` with `{"status":"ok","db":"ok"}`.
- [ ] `GET http://localhost:8000/api/v1/health` returns `503` with `db: "down"` when the database is
      unreachable (stop the db container and check — then start it again).
- [ ] `docker compose exec api python -m pytest -q` passes with at least one real test.
- [ ] `docker compose exec api ruff check .` and `ruff format --check .` are clean.
- [ ] `docker compose exec api python -m prisma generate` still succeeds after the changes (the generated
      client must not be broken by imports).
- [ ] The app starts and stops cleanly (no "event loop is closed" or "client not disconnected" warnings).

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

Add anything you learn about Prisma-from-Python ergonomics (query syntax, nested includes, transactions,
raw SQL) to this task's `## Research notes` — T-010 and T-015 will need it.

## Work log

## Report

## Manager review
