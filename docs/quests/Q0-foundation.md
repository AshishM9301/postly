# Q0 · Foundation

**Goal:** `docker compose up` gives a running Postgres + FastAPI + Next.js, and any fresh session can pick
up work without re-researching anything.

**Status:** in progress

**Done when**
- `docker compose up -d` brings up db, api and web with healthy status.
- `GET /api/v1/health` returns `{"status":"ok","db":"ok"}`.
- `docker compose exec api python -m pytest -q` runs a real test (not zero tests).
- `cd apps/web && npm run lint && npm run typecheck && npm run build` all pass.
- `docs/research/00-versions.md` matches the versions actually installed.

**Tasks**

| ID | Task | Status |
|---|---|---|
| T-001 | Version lock + environment proof | done |
| T-002 | Repo skeleton + Docker Compose | ready (mostly built during T-001 review — see the task's manager notes) |
| T-003 | FastAPI skeleton + Prisma client + health | ready (skeleton exists; this task makes it production-shaped) |
| T-004 | Frontend scaffold + API proxy + health page | ready |
| T-005 | Docs set + AGENTS.md contract | done |
| T-006 | OpenAPI → TypeScript types + typed fetch client | ready |

**Notes**
- T-001 is the gate. If the pinned Prisma/Python combination fails, the fallback (keep `schema.prisma`,
  SQLAlchemy + Alembic for Python) is decided here, written into `docs/DECISIONS.md`, and every later task
  is written against it. **It passed** — prisma-client-py 0.15.0 with Prisma CLI 5.19.0 works on
  `python:3.13-slim` and on local Python 3.14.7.
- Development happens **inside Docker** so the Python version is identical everywhere. A local venv is
  optional and must match `docs/research/00-versions.md`.
- The compose stack (`db` + `api`) is already running and healthy; `web` joins in T-004.
