# T-002 · Repo skeleton + Docker Compose

- status: done
- quest: Q0
- depends: T-001
- owner: s-20261030-1914
- updated: 2026-10-30T20:10
- files: docker-compose.yml, backend/Dockerfile, backend/.dockerignore, backend/app/main.py, backend/app/__init__.py, backend/pyproject.toml, .gitignore, .dockerignore

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

- [x] `backend/.dockerignore` exists and excludes `.venv`, `__pycache__`, `media`, `.env`, `*.pyc`.
- [x] The API image runs as a **non-root user** (create it in the Dockerfile, `chown` the media dir) and the
      stack still comes up healthy afterwards.
- [x] `docker compose down -v` followed by `docker compose up -d` works from scratch, and the volume is
      recreated empty with the migrations re-applied automatically.
- [x] `docker compose exec api python -m prisma generate` succeeds **inside the running container**.
- [x] `docker compose exec api python -m prisma migrate status` reports the database is up to date.
- [x] `docker compose exec api python -m pytest -q` runs inside the container (0 tests is fine here, but the
      command must work — T-003 adds the first real test). *Runs, reports `no tests ran`, exit 5 (pytest's
      documented "no tests collected" code).*
- [x] `docker compose exec api ruff check .` and `ruff format --check .` are clean.
- [x] `git init` has been run, `.gitignore` covers `.env`, `.venv`, `node_modules`, `backend/media/` and the
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

Non-root fix (2026-10-30, worker s-20261030-1914) — later tasks will hit this:

- The Prisma cache lives in `$HOME/.cache/prisma-python`. Set `HOME=/home/appuser` in the image, create the
  home dir and `chown` it **before** `USER appuser`, then run `python -m prisma generate` as `appuser` in the
  build. The build-time cache is therefore owned by the runtime user and `migrate deploy` at boot does not
  re-download Node.
- `prisma generate` writes into `site-packages/prisma`, which `pip` creates root-owned. The Dockerfile
  `chown -R appuser:appuser /usr/local/lib/python3.13/site-packages/prisma` so
  `docker compose exec api python -m prisma generate` still works as the non-root user.
- `/app/media` is `mkdir`-ed and `chown`-ed before `USER appuser`; the named volume copies that ownership on
  first creation (`docker compose exec api ls -ld /app/media` → `appuser appuser`).
- Package decision: `backend/pyproject.toml` now declares `packages = ["app"]` and `backend/app/__init__.py`
  exists. The Dockerfile copies `app/` before `pip install .` so the wheel can be built. At runtime the
  `./backend:/app` bind mount is first on `sys.path` (`PYTHONPATH=/app`), so **the mounted source wins** over
  the copy in site-packages — edit code on the host and uvicorn sees it without a rebuild. The site-packages
  copy only exists to satisfy the build/install step.
- `.dockerignore` excludes `media/`, so the image does not carry local uploads; the Dockerfile creates
  `/app/media` itself.
- Port 5432 is shared with the unrelated `coursehub-postgres` container; it is stopped, not deleted. If it
  is ever restarted, set `POSTGRES_PORT` in `.env` to avoid the clash.

## Work log

- 2026-10-30 (manager, during T-001 review): built the compose stack, api image and health skeleton at the
  owner's request. Recorded here so the worker does not redo it.
- 2026-10-30 s-20261030-1914: added the two `.dockerignore` files, made the image non-root (with the Prisma
  cache/site-packages ownership fix), declared the `app` package, fixed the one ruff `UP035` error, and ran
  the full `down -v` → `up -d` proof.

## Report

### 2026-10-30 · worker s-20261030-1914

- changed:
  - `backend/.dockerignore` — new; excludes `.venv`, `__pycache__`, `media`, `.env`, `build`, `*.egg-info`.
  - `.dockerignore` — new root-context guard (not used by the `./backend` build context, but future-proof).
  - `backend/Dockerfile` — non-root `appuser` (uid/gid 10001), `HOME=/home/appuser`, `chown` of the Prisma
    cache home, `/app/media` and `site-packages/prisma`; copies `app/` before `pip install .`; generates the
    client as `appuser`.
  - `backend/pyproject.toml` — `packages = ["app"]` (was `[]`), per this task's notes.
  - `backend/app/__init__.py` — new, so `app` is a real installable package.
  - `backend/app/main.py` — ruff `UP035` fix (`AsyncIterator` from `collections.abc`).
  - `.gitignore` — added `build/`, `dist/`, `*.whl`.
- verified (real output):
  - `docker compose down -v; docker compose up -d` → volumes and network recreated from scratch;
    `api health: healthy`.
  - `docker compose exec -T api whoami` → `appuser`; `id` → `uid=10001(appuser)`.
  - `curl /api/v1/health` → `{"status":"ok","db":"ok","version":"0.1.0"}`.
  - `docker compose exec -T api python -m prisma generate` → `✔ Generated Prisma Client Python (v0.15.0)`
    (exit 0).
  - `docker compose exec -T api python -m prisma migrate status` → `Database schema is up to date!` (exit 0).
  - `docker compose exec -T api python -m pytest -q` → `no tests ran in 0.08s`, exit 5 (expected with 0
    tests; command itself works).
  - `docker compose exec -T api ruff check .` → `All checks passed!`; `ruff format --check .` → `3 files
    already formatted`.
  - fresh DB has `SpikeRow` + `_prisma_migrations`; `/app/media` owned by `appuser:appuser`.
  - `git check-ignore` confirms `.env`, `.venv`, `node_modules`, `backend/media/`, the generated Prisma
    client, `build/` and `*.egg-info/` are ignored. No commit made.
- issues:
  - `pytest` exits 5 when zero tests are collected (pytest's documented behaviour); the task allows 0 tests.
    T-003 adds the first test.
  - `pyproject.toml` and `app/__init__.py` are outside the task's `files:` list but both are required by the
    task's own notes ("set the packages properly"). Flagging in case the manager wants the list widened.
- next: T-003 (FastAPI skeleton + Prisma client + health).

## Manager review

### 2026-10-30 · manager (independent verification, session s-20261030-2010)
- verdict: **accepted**
- checked (re-run by me from scratch, not trusting the report):
  - `docker compose exec -T api whoami` → `appuser`; `id` → `uid=10001(appuser) gid=10001(appuser)`
  - health from inside the container → `{"status":"ok","db":"ok","version":"0.1.0"}`
  - `docker compose exec -T api python -m prisma generate` → `✔ Generated Prisma Client Python (v0.15.0)` (exit 0)
  - `docker compose exec -T api python -m prisma migrate status` → `Database schema is up to date!` (exit 0)
  - `docker compose exec -T api python -m pytest -q` → `no tests ran in 0.08s`, exit **5** (pytest's code for
    zero collected tests — the task allows 0 tests, T-003 adds the first one)
  - `docker compose exec -T api ruff check .` → `All checks passed!`; `ruff format --check .` → `3 files already
    formatted`
  - **destructive check**: `docker compose down -v` (both volumes + the network removed) → `docker compose up -d`
    → both services healthy; api logs show `Applying migration 20261030125856_init_probe` →
    `All migrations have been successfully applied.` → the **fresh** volume contains `SpikeRow` +
    `_prisma_migrations` → health `{"status":"ok","db":"ok"}`
  - image contents: `/app` contains no `.env`, no `.venv`, no stray media; `/app/media` is owned by
    `appuser:appuser`
  - git: `git log` still shows only 2 commits → **the worker did not commit**; `.env` is not tracked;
    `git check-ignore` confirms `.env`, `backend/.venv/`, `node_modules/`, `backend/media/`,
    `backend/prisma/generated/`, `build/`, `dist/`, `*.whl` are all ignored — verified by creating real
    directories on disk and confirming `git status` stays clean
  - read the full diff: `.gitignore`, `backend/Dockerfile`, `backend/pyproject.toml`, `backend/app/main.py`,
    new `backend/.dockerignore`, new `.dockerignore`, new `backend/app/__init__.py`
- notes:
  - **Scope flag accepted.** `backend/pyproject.toml` and `backend/app/__init__.py` were outside the task's
    `files:` list, but the task's own notes said "set the packages properly — now that `backend/app/`
    exists". That is exactly what was done. `files:` widened below to match reality.
  - The non-root user needed `HOME=/home/appuser` **and** a writable `site-packages/prisma`, because the
    client is regenerated inside the running container. Both handled — this is the kind of detail that
    breaks a non-root image if it is missed.
  - `pip install .` leaves `build/` and `postly_api.egg-info/` in `/app` at build time. Harmless, and now
    excluded by `.dockerignore` so they can never be copied in from the host.
  - **CI note:** `pytest` exits 5 when zero tests are collected. Do not treat exit 5 as a crash in scripts.
- next: T-003 — `docs/tasks/T-003-fastapi-skeleton-and-prisma-client.md` is ready for the worker.

### 2026-10-30 · manager follow-up (owner request: "set the packages properly")
The worker set `packages = ["app"]`, which satisfies the literal words of the task but not its intent — a
literal package list installs **only** the top-level package, so `app.core`, `app.db`, `app.api.v1` and
friends would be silently excluded from the install the moment T-003 creates them. Fixed:

- `backend/pyproject.toml` → `[tool.setuptools.packages.find]` with `where = ["."]`, `include = ["app*"]`.
- `backend/Dockerfile` → `pip install --no-cache-dir -e .` (editable) instead of a second copy in
  site-packages. The Dockerfile comment records the dev/production split.
- `docs/ARCHITECTURE.md` §10 and `docs/DECISIONS.md` AD-010 document the decision.

Verified after rebuilding the image:
- `docker compose exec -T -w /tmp api python -c "import app, app.main; ..."` → `/app/app/__init__.py`,
  `/app/app/main.py` → **one** copy of the source, resolved through the editable finder.
- editable markers present: `__editable__.postly_api-0.1.0.pth` + `__editable___postly_api_0_1_0_finder.py`.
- wheel built from a throwaway copy with a probe subpackage contains `app/__init__.py`, `app/core/__init__.py`,
  `app/main.py` → subpackages **are** discovered (the old literal list would have dropped `app/core`).
- a probe subpackage dropped into the live bind mount imports immediately, with **no rebuild**:
  `import app._probe.mod` → `IMPORT OK -> 42 from /app/app/_probe/mod.py` → so T-003 can add
  `app/core/`, `app/db/`, `app/api/v1/` and use them straight away.
- stack still healthy after the rebuild: `{"status":"ok","db":"ok"}`, `Database schema is up to date!`,
  `ruff check .` → `All checks passed!`, `3 files already formatted`, `whoami` → `appuser`.
- probe removed; `git status` shows only the three intended edits.

