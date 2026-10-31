# Q0 · Foundation

**Goal:** `docker compose up` gives a running Postgres + FastAPI + Next.js, and any fresh session can pick
up work without re-researching anything.

**Status:** done

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
| T-002 | Repo skeleton + Docker Compose | done |
| T-003 | FastAPI skeleton + Prisma client + health | done |
| T-004 | Frontend scaffold + API proxy + health page | done |
| T-005 | Docs set + AGENTS.md contract | done |
| T-006 | OpenAPI → TypeScript types + typed fetch client | done |

**Notes**
- T-001 is the gate. If the pinned Prisma/Python combination fails, the fallback (keep `schema.prisma`,
  SQLAlchemy + Alembic for Python) is decided here, written into `docs/DECISIONS.md`, and every later task
  is written against it. **It passed** — prisma-client-py 0.15.0 with Prisma CLI 5.19.0 works on
  `python:3.13-slim` and on local Python 3.14.7.
- Development happens **inside Docker** so the Python version is identical everywhere. A local venv is
  optional and must match `docs/research/00-versions.md`.
- The compose stack (`db` + `api` + `web`) is running and healthy. `web` joined in T-004 and serves
  `http://localhost:3000`, proxying `/api/:path*` to the API.
- **Every "Done when" above was re-verified on 2026-10-31** during the T-006 review: all three services
  healthy from a cold `docker compose up -d`, `GET /api/v1/health` → `{"status":"ok","db":"ok"}`,
  `pytest -q` → `1 passed`, and `lint` + `typecheck` + `build` all green.
- T-006 added the typed API door: `apps/web/src/lib/api/` holds the generated `types.ts` (from the live
  OpenAPI spec, via `npm run api:types`) and the only `fetch` call site in `src/`. The home page now talks
  to the API through it, using the trusted server-side `API_INTERNAL_URL` — never request headers.
