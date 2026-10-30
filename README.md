# Postly

Local community problems app. Post a pothole or a broken water line with a photo, your area (Delhi PIN code)
decides who sees it, the community votes decide what trends, and anything abusive or NSFW is blurred until
you choose to look.

**Status:** pre-implementation. The plan, the task board and the design docs live in `docs/`.

## Stack

| | |
|---|---|
| Frontend | Next.js 15 (App Router, TS, Tailwind 4, shadcn/ui, TanStack Query) — `apps/web` |
| Backend | FastAPI + Prisma (`prisma-client-py`) + PostgreSQL 16 — `backend` |
| Auth | Firebase Auth (Google) + our own pseudonymous & ghost modes |
| Media | Local disk now, `StorageProvider` interface so S3/R2 can slot in later |
| Moderation | Rules → OpenAI `omni-moderation-latest` (free) → local HuggingFace models as fallback |

The API is the contract. A future Kotlin / Swift client must work against it without changes.

## Run it (once T-002 lands)

```bash
cp .env.example .env
docker compose up -d
docker compose exec api python -m pytest -q
open http://localhost:3000
```

## Working on it

This repo uses a **manager / worker** flow with one Markdown file per task.

- Read [`AGENTS.md`](AGENTS.md) — the operating contract for every session.
- The board is [`docs/tasks/README.md`](docs/tasks/README.md).
- Each task lives in `docs/tasks/T-0xx-*.md`; the worker appends a report to the same file and the manager
  appends a verification verdict before the next task is released.

```bash
# manager session
"verify the finished task and release the next one"

# worker session
"do the next task from docs/tasks/README.md"
```

## Docs

| File | What it covers |
|---|---|
| [`docs/PLAN.md`](docs/PLAN.md) | Product scope and the full feature list |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How the pieces fit together |
| [`docs/DATA_MODEL.md`](docs/DATA_MODEL.md) | The 19 tables, fields and indexes |
| [`docs/API.md`](docs/API.md) | Endpoint contract |
| [`docs/SECURITY.md`](docs/SECURITY.md) | The anonymity design and threat model |
| [`docs/MODERATION.md`](docs/MODERATION.md) | Moderation providers and policy |
| [`docs/GEO_DATA.md`](docs/GEO_DATA.md) | Delhi PIN data: source, licence, seeding |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Why each big decision was made |
| [`docs/BACKLOG.md`](docs/BACKLOG.md) | Ideas inbox |
| [`docs/research/`](docs/research/) | Cached research — read it, don't re-search |
