# 00 · VERSIONS (pinned 2026-10-30)

**Do not re-derive these.** If something does not work, fix the code — do not bump versions. A version bump
is its own task with a build + test run.

---

## 1. The rule

Before pinning any npm package:

```bash
npm view <pkg> dist-tags
```

If `latest` contains a prerelease suffix (`-rc`, `-beta`, `-dev`, `-alpha`, `-integration`), **do not use
it** — pick the newest stable explicitly and write the exact version.

Real example: `npm view prisma dist-tags` returns
`latest: 8.0.0-rc.29` — the `latest` tag is a release candidate. The newest stable is `7.10.1`.

Pin exact versions everywhere: `package.json` has no `^`/`~`, Python deps use `==`, Docker images use an
exact tag.

---

## 2. Frontend (apps/web)

Scaffolded by `create-t3-app@7.40.0`, which is built and tested against the versions below. Let the
scaffold choose; do not force newer.

| Package | Version | Note |
|---|---|---|
| `create-t3-app` | 7.40.0 | run once, `npx create-t3-app@7.40.0` |
| `next` | 15.x | scaffold default (`^15.2.3` upstream). Node `>=18.18` |
| `typescript` | 5.8.x | scaffold default (`^5.8.2` upstream). **Not 7.x** — TS 7 is the new Go compiler and is not what the scaffold is tested against |
| `tailwindcss` | 4.x | v4, CSS-first config |
| `eslint` | 9.x | npm `latest` is 10.x, but the scaffold ships 9.x |
| `prettier` | 3.x | |
| `@tanstack/react-query` | 5.x | server state for the REST client |
| `zod` | 4.x | client-side validation of API payloads |
| `firebase` | 13.1.0 | web SDK (Google sign-in) |
| `blurhash` | 2.0.5 | blurred placeholder for images |
| `shadcn` | 4.x | CLI only, components are copied into the repo |
| `openapi-typescript` | 7.13.0 | generates TS types from the FastAPI spec (installed in T-006) |

Node on this machine: **v24.18.0** (satisfies Next 15 and Next 16's `>=20.9`).

### Verified installed in `apps/web` (T-004, 2026-10-30)

Scaffold command (non-interactive; `apps/web` did not exist beforehand):

```
npx create-t3-app@7.40.0 apps/web --CI --noGit \
  --tailwind true --nextAuth false --betterAuth false --prisma false \
  --drizzle false --trpc false --appRouter true --eslint true --biome false \
  --import-alias "@/*"
```

The CLI scaffolded the files but aborted during install with `TypeError: i.replace is not a function`;
`npm install` in `apps/web` completed the setup. Versions are pinned exactly in `package.json`
(`package-lock.json` is committed):

| Package | Version | Note |
|---|---|---|
| `next` | 15.5.28 | resolved from the scaffold's `^15.2.3` |
| `react` / `react-dom` | 19.3.1 | |
| `typescript` | 5.9.3 | scaffold resolved `^5.8.2` to 5.9.3; lint/typecheck/build pass |
| `tailwindcss` / `@tailwindcss/postcss` | 4.3.3 | v4, CSS-first config |
| `eslint` | 9.39.5 | npm deprecation warning, still what the scaffold ships |
| `eslint-config-next` | 15.5.28 | |
| `prettier` | 3.9.10 | |
| `prettier-plugin-tailwindcss` | 0.6.14 | |
| `zod` | 3.25.76 | **scaffold ships zod 3.x**, not the plan's 4.x; `@t3-oss/env-nextjs` 0.12.0 expects it |
| `@t3-oss/env-nextjs` | 0.12.0 | env validation |
| `postcss` | 8.5.32 | |
| `typescript-eslint` | 8.72.1 | |
| `@eslint/eslintrc` | 3.3.7 | |
| `@types/node` | 20.19.43 | |
| `@types/react` / `@types/react-dom` | 19.3.0 | |

Not installed yet (later tasks): `@tanstack/react-query` (T-020), `firebase` (T-011), `blurhash` (T-016),
`shadcn` (T-020). `npm install` reports 5 advisories in the scaffold's transitive tree; they were not
force-fixed because that changes pinned versions.

`openapi-typescript` 7.13.0 was installed in T-006 as an exact devDependency (npm `latest: 7.13.0`,
`next: 7.0.0-rc.1` — the pin is stable, not a prerelease).

The web image uses `node:24.18.0-alpine` (multi-stage: deps → builder → non-root `nextjs` runner).
The `/api/:path*` rewrite target comes from `API_INTERNAL_URL` (`http://api:8000` in compose,
`http://localhost:8000` fallback for host `next dev`).

---

## 3. Backend (backend/)

Python **3.13** in Docker (`python:3.13.x-slim`), local venv may be 3.13 or 3.14 (all deps require
`>=3.11`, except `torch`/`transformers` which want `>=3.11`).

| Package | Version | Note |
|---|---|---|
| `prisma` | 0.15.0 | **the whole Prisma story** — see §4 |
| `fastapi` | 0.162.0 | |
| `uvicorn` | 0.54.0 | |
| `pydantic` | 2.14.2 | pydantic v2 |
| `httpx` | 0.28.1 | async HTTP client (also a prisma dependency) |
| `python-multipart` | 0.0.32 | file uploads |
| `pyjwt` | 2.15.1 | session tokens |
| `firebase-admin` | 7.7.0 | verifies Firebase ID tokens server-side |
| `argon2-cffi` | 25.1.0 | only if a user ever picks a human-readable passphrase; we use 256-bit random secrets instead |
| `pillow` | 13.0.0 | thumbnails, blurHash, image validation |
| `pywebpush` | 2.5.0 | Web Push (VAPID) delivery |
| `pytest` | 9.2.0 | |
| `transformers` | 5.22.1 | optional extra: local moderation worker |
| `torch` | 2.15.0 | optional extra: local moderation worker |

Dev tools: `ruff` (latest stable, pinned) for lint + format.

---

## 4. Prisma — how it actually works here

`prisma-client-py` 0.15.0 ships its own Prisma CLI and Rust query engine. From the package source
(`src/prisma/_config.py`):

```
PRISMA_VERSION                   = 5.19.0                  # stable release
PRISMA_EXPECTED_ENGINE_VERSION   = 5fe21811a6ba0b952a3bc71400666511fe3b902f
use_global_node                  = true                    # uses your Node 24.18.0
use_nodejs_bin                   = true
```

- **The npm `prisma` package is never installed.** No `prisma`, no `@prisma/client` in `package.json`.
- The pip `prisma` package provides the CLI: `python -m prisma generate`, `python -m prisma migrate dev`,
  `python -m prisma migrate status`, `python -m prisma db push`.
- At **runtime** the Rust query engine does the work — Node is only needed for the CLI commands.
- Pin explicitly in `backend/pyproject.toml` so a future pip release cannot drift us to an RC:

```toml
[tool.prisma]
prisma_version = "5.19.0"
expected_engine_version = "5fe21811a6ba0b952a3bc71400666511fe3b902f"
```

- npm's Prisma tags for reference: `latest 8.0.0-rc.29` (RC), `prev 7.10.1` (newest stable),
  `6.19.3` (last 6.x). We deliberately stay on 5.19.0 because the Python generator targets that protocol.
- **Fallback plan** if prisma-client-py cannot express something: keep `schema.prisma` as the source of
  truth and swap the Python data layer to SQLAlchemy + Alembic. Record it in `docs/DECISIONS.md`.

### T-010 schema findings (2026-10-31, verified)

- The real 17-model / 7-enum schema generates cleanly on prisma-client-py 0.15.0. Enums become `StrEnum`
  classes in `prisma.enums`; `Json`/`Json?` become `JSONB`; `@updatedAt` is handled by the client;
  `onDelete: Cascade` is emitted as real Postgres FKs; nested `include` works.
- `prisma migrate dev` needs to write `prisma/migrations/`, but the bind-mounted `backend/` is root-owned
  while the container runs as `appuser` (uid 10001). Run migration creation as root and regenerate as the
  app user:
  `docker compose exec -u root -T api python -m prisma migrate dev --name <name> --skip-generate`
  then `docker compose exec -T api python -m prisma generate`.
- `prisma-client-js` (frontend types) requires the npm `@prisma/client`, which AD-004 forbids in the
  project. It is generated in a throwaway `/tmp` project pinned to `prisma`/`@prisma/client` 5.19.0, with
  `--no-engine`, and only the `.d.ts` files are copied to `apps/web/src/generated/prisma`. Never run
  the Python wrapper from a directory that has its own `node_modules/prisma` — it can overwrite the
  Python client with a different engine version. Details in T-010's research notes.
  **The `.d.ts` output is gitignored and is NOT committed** (manager decision, 2026-10-31): the web app
  codes against the OpenAPI spec, not the database schema, so these ~1.3 MB of vendored declarations are
  never a build input and must never be imported. Regenerate them only if a task really needs DB-shaped
  types in the frontend.

---

## 5. Moderation models (HuggingFace)

All verified to exist, ungated:

| Model | Task | Licence | Size |
|---|---|---|---|
| `KoalaAI/Text-Moderation` | multi-label text (deberta), trained on `mmathys/openai-moderation-api-evaluation` — i.e. it mirrors OpenAI's category set | openrail | ~180M |
| `unitary/toxic-bert` | binary toxicity (bert) | apache-2.0 | 109M |
| `martin-ha/toxic-comment-model` | binary toxicity (distilbert), fastest | — | 67M |
| `facebook/roberta-hate-speech-dynabench-r4-target` | hate speech (roberta) | — | 125M |
| `unitary/multilingual-toxic-xlm-roberta` | multilingual toxicity (XLM-R) → Hindi/other | apache-2.0 | 278M |
| `Falconsai/nsfw_image_detection` | image `normal`/`nsfw` (ViT) | apache-2.0 | 86M |

Caveat: the local classifiers are weak on Indian languages. Hindi leans on the OpenAI endpoint when a key
exists.

---

## 6. External services

| Service | Cost | Policy/limits |
|---|---|---|
| OpenAI `omni-moderation-latest` | **free endpoint** (needs `OPENAI_API_KEY`) | images ≤ 20 MB, sent as base64 data URLs |
| Nominatim (OSM) | free | ≤ 1 req/s, real User-Agent, **no autocomplete**, no bulk postcode queries, cache results |
| Overpass API | free, no key | thin coverage for Delhi PINs (verified: 18 PINs) — enrichment only |
| `pincode.csv` (ghousekw/india-pincodes) | free, **CC0 1.0** | the area dataset — see `docs/GEO_DATA.md` |
| Firebase Auth | free tier | Google sign-in; email never stored in our DB |
| Cloudflare Turnstile | free | **removed from the MVP** — added at public launch |

---

## 7. Infra

| Image | Tag |
|---|---|
| postgres | `postgres:16.x-alpine` |
| api | `python:3.13.x-slim` |
| web | `node:24.x-alpine` |
| moderation worker | `python:3.13.x-slim` + torch/transformers |

---

## 8. Verified combination (T-001, 2026-10-30)

Proven end to end inside a pristine `python:3.13-slim` container against `postgres:16-alpine`:
`pip install .` from `backend/pyproject.toml` → `python -m prisma generate` → `python -m prisma migrate dev --name init_probe` → `python scripts/spike_env.py` printed `SPIKE OK: wrote and read row 1`.

Everything in §3–§4 held. Things a later session must know:

- **`python:3.13-slim` needs `libatomic1`.** Prisma Python downloads a prebuilt Node (`26.13.0`) into
  `~/.cache/prisma-python/nodeenv` when no global node exists; that Node fails to start with
  `libatomic.so.1: cannot open shared object file`. The T-002 Dockerfile must
  `apt-get install -y libatomic1` (or install a system Node) **before** running `python -m prisma ...`.
- Inside the container the CLI used prebuilt Node **26.13.0**, not the host's 24.18.0 (no global node in the
  slim image). Still worked with Prisma CLI 5.19.0.
- `python:3.13-slim` result is the one that counts; it passed.
- **Local Windows Python 3.14.7 also worked** (pip install, generate, migrate, spike). Two quirks:
  the venv's `Scripts` directory must be on `PATH` (otherwise `spawn prisma-client-py ENOENT`), and the
  local venv lives in `backend/.venv` once created correctly.
- `prisma generate` prints a warning about `recursive_type_depth`. It is informational; the placeholder
  schema in T-001 leaves the default. If later code needs the full recursive types, set
  `recursive_type_depth = -1` in the generator block.
- `backend/pyproject.toml` uses `[tool.setuptools] packages = []` because `app/` does not exist yet (T-002
  creates it). `pip install .` therefore installs only dependencies; revisit when `app/` lands.
- The T-001 placeholder migration `backend/prisma/migrations/20261030125856_init_probe/` creates the
  `SpikeRow` table. T-010 owns the real schema and adds its own migration; do not edit `schema.prisma`
  without a new migration.

## 9. Verify command reference

```bash
npm view <pkg> dist-tags                      # before any pin
python -c "import json,urllib.request as u; print(json.load(u.urlopen('https://pypi.org/pypi/<pkg>/json'))['info']['version'])"
docker compose exec api python -m prisma generate
docker compose exec api python -m prisma migrate status
```

## 10. Compose stack (verified 2026-10-30)

| Thing | Value |
|---|---|
| Postgres image | `postgres:16.15-alpine` (tag confirmed to exist; `postgres:16-alpine` resolves to 16.15) |
| API image | `python:3.13-slim` + `apt-get install -y libatomic1` |
| Services | `db` (5432), `api` (8000), `web` (3000) |
| Volumes | `postly_pgdata` (database), `postly_postly_media` (uploads) |
| Startup | the api container runs `python -m prisma migrate deploy` before uvicorn, so migrations apply on boot |
| Health | `GET /api/v1/health` → `{"status":"ok","db":"ok"}` (no `version` field — see `backend/app/api/v1/health.py`) |
| Web image | `node:24.18.0-alpine`, 3 stages, runs as `nextjs` (uid 1001); proxy target `API_INTERNAL_URL` |

### Prisma CLI behaviours worth remembering
- `prisma migrate status` **exits 1 when migrations are pending** — never chain `&&` after it in a script.
- `prisma migrate dev` flags: `--name`, `--create-only`, `--skip-generate`, `--skip-seed`. All verified.
- `prisma migrate dev` on a **fresh** database applies the existing migration folder and then reports
  "Your database is now in sync with your schema" — no new migration is created.
- `prisma generate` prints a `recursive_type_depth` advisory every time. It is informational. Set
  `recursive_type_depth = -1` in the generator block when the real schema needs full recursive types (T-010).
- The generated client lands in **site-packages**, not next to `schema.prisma`, so a bind mount of the
  project over `/app` does not shadow it.
- The CLI installs a prebuilt **Node 26.13.0** when no global Node exists in the image. On slim images that
  Node needs `libatomic1`.

### Host port conflicts on this machine
Port 5432 was held by `coursehub-postgres` (image `postgres:18-alpine`). It was stopped at the owner's
instruction — **its data is intact**, restore it with `docker start coursehub-postgres`. Postly now uses
5432 for its own `postgres:16.15-alpine`.

### Verified end to end
```
docker compose up -d
→ postly-postgres  Up (healthy)  0.0.0.0:5432->5432/tcp
→ postly-api       Up (healthy)  0.0.0.0:8000->8000/tcp
→ postly-web       Up (healthy)  0.0.0.0:3000->3000/tcp
api logs: "All migrations have been successfully applied." → "Uvicorn running on http://0.0.0.0:8000"
GET http://localhost:8000/api/v1/health → {"status":"ok","db":"ok"}
GET http://localhost:3000/api/v1/health → {"status":"ok","db":"ok"}   (via the Next rewrite)
GET http://localhost:3000              → 200, home page renders API=ok / Database=ok
```

Verified again on 2026-10-31 by the manager during the T-004 review, from a cold
`docker compose down` → `docker compose up -d`, including `docker compose build --no-cache web`.
