# T-002 · Repo skeleton + Docker Compose

- status: ready
- quest: Q0
- depends: T-001
- owner: -
- updated: 2026-10-30
- files: docker-compose.yml, backend/Dockerfile, backend/.dockerignore, backend/app/main.py, .gitignore, .dockerignore

## Goal

Finish the container stack so it is safe to develop against every day: a non-root API image, a clean build
context, a reproducible `down -v` → `up -d` cycle, and a repo that is a git repository with the right
ignores.

## Manager notes (2026-10-30, during the T-001 review)

Most of this task was **already built by the manager during T-001 verification**, at the owner's request
("why not create compose stack and put it in there"). Do not rebuild it. What exists today:

- `docker-compose.yml` — services `db` (`postgres:16.15-alpine`, named volume `postly_pgdata`, healthcheck,
  published on 5432) and `api` (built from `backend/`, `migrate deploy` then uvicorn on 8000, healthcheck,
  named volume for media).
- `backend/Dockerfile` — `python:3.13-slim`, installs **`libatomic1`** (required by Prisma's prebuilt Node),
  `pip install .` from the pinned `pyproject.toml`, `prisma generate` at build time.
- `backend/app/main.py` — a minimal skeleton with a real `/api/v1/health` that queries the database.
- `.env` (gitignored, real secrets) and `.env.example` (empty secrets) exist.
- Verified working: `docker compose up -d` → both services healthy → `GET /api/v1/health` →
  `{"status":"ok","db":"ok","version":"0.1.0"}`; migrations apply automatically on boot.

**Host port note:** port 5432 was previously taken by an unrelated container (`coursehub-postgres`,
`postgres:18-alpine`). It was stopped at the owner's instruction — its data is intact and
`docker start coursehub-postgres` restores it. Do not delete that container.

## Done when

- [ ] `backend/.dockerignore` exists and excludes `.venv`, `__pycache__`, `media`, `.env`, `*.pyc`.
- [ ] The API image runs as a **non-root user** (create it in the Dockerfile, `chown` the media dir) and the
      stack still comes up healthy afterwards.
- [ ] `docker compose down -v` followed by `docker compose up -d` works from scratch, and the volume is
      recreated empty with the migrations re-applied automatically.
- [ ] `docker compose exec api python -m prisma generate` succeeds **inside the running container**.
- [ ] `docker compose exec api python -m prisma migrate status` reports the database is up to date.
- [ ] `docker compose exec api python -m pytest -q` runs inside the container (0 tests is fine here, but the
      command must work — T-003 adds the first real test).
- [ ] `docker compose exec api ruff check .` and `ruff format --check .` are clean.
- [ ] `git init` has been run, `.gitignore` covers `.env`, `.venv`, `node_modules`, `backend/media/` and the
      generated Prisma client, and **no commit is made** (the owner commits).

## Notes / gotchas

- The `web` service is **not** in compose yet — T-004 adds it. Do not add a placeholder that fails to build.
- `pip install .` currently installs dependencies only, because `pyproject.toml` has
  `[tool.setuptools] packages = []` (there was no `app/` package when it was written). Now that
  `backend/app/` exists, set the packages properly — and make sure the mounted source (`./backend:/app`) and
  the installed package do not fight each other. Decide and document which one wins.
- The generated Prisma client lives in **site-packages**, not in `/app`, so the bind mount does not shadow
  it. Keep it that way.
- `prisma migrate status` exits 1 when migrations are pending. Do not chain commands with `&&` after it.
- Secrets come from `.env` via `env_file`; the compose file must not contain any secret value.
- The image is ~1.1 GB (Node + Prisma engines + Python deps). That is expected; do not "optimise" it by
  installing the npm Prisma CLI.

## Research notes

Versions: `docs/research/00-versions.md` §3 and §7. Prisma CLI behaviour: `docs/research/00-versions.md` §4
and §10.

If the non-root user change breaks the Prisma cache (`~/.cache/prisma-python`) or the media volume, write
the fix here — later tasks will hit it too.

## Work log

- 2026-10-30 (manager, during T-001 review): built the compose stack, api image and health skeleton at the
  owner's request. Recorded here so the worker does not redo it.

## Report

## Manager review
