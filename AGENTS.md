# AGENTS.md — Operating contract for Postly

**Read this file completely before doing anything.** You may be a fresh session with zero conversation
context. Everything you need is in this repo. Never rely on memory of a previous session — if it isn't
written down here or in `docs/`, it doesn't exist.

---

## 1. What this project is

**Postly** — a local community problems app.

- People post real problems in their locality (pothole, water supply, garbage, streetlight) with photos/videos.
- Every post belongs to an **area = a Delhi PIN code** (or the area you set your GPS to).
- The community **votes**; a time-decayed ranking makes the "trending" panel (For You / Trending / New / Nearby).
- Posts also carry a **blame target** (municipality, contractor, utility, police…) — the debate happens in threaded comments.
- **Flagged content is blurred** (abusive language, NSFW) with a warning banner; the reader can click *Accept & show* to reveal it (recorded per user).
- **Backend is FastAPI + PostgreSQL + Prisma.** `backend/prisma/schema.prisma` is the single source of truth for the data model.
- **Frontend is Next.js** (T3-style folder structure, TypeScript, Tailwind, shadcn/ui) and talks **REST** to FastAPI.
- The API is the contract: a future **Kotlin / Swift** mobile app must be able to use it unchanged.

## 2. Non-negotiable rules

1. **One task per session.** Pick one task from `docs/tasks/README.md`, do it, report, stop.
2. **Never widen your own scope.** If a task needs more work, write it in the report and stop. The manager re-splits.
3. **Read only what your task lists.** `files:` in the task file + the research file it links. Do not read the whole repo, do not read `docs/PLAN.md` top-to-bottom.
4. **Never re-research.** If `docs/research/` has the topic, read that file instead of searching the web. If you learn something new, **write it into the task file's `## Research notes`** so the next session doesn't repeat you.
5. **Pin exact versions.** No `^`/`~`/`>=` ranges in `package.json` or `pyproject.toml`. Before pinning any npm package, run `npm view <pkg> dist-tags` and confirm `latest` is not a prerelease (`-rc`, `-beta`, `-dev`, `-alpha`). See `docs/research/00-versions.md`.
6. **Never commit secrets.** `.env` is gitignored. Only `.env.example` with empty values goes in the repo.
7. **Privacy invariants** (breaking these breaks the product's core promise):
   - Never store email, phone, IP, or User-Agent for any user.
   - Ghost posts/comments/votes are stored **salted** (`HMAC-SHA256(clientSecret, targetId)`) — never as a plain identifier. See `docs/SECURITY.md`.
   - Deletion is **hard delete** (rows + files on disk), never soft delete.
8. **Report honestly.** If a verification failed, say so in the report with the actual output. A false "verified" costs more than a failed task.
9. **Finish the session properly:** board updated, `## Report` appended, `status` set. A session that ends without a report is wasted work.

## 3. Which role am I?

| The user says | You are |
|---|---|
| "plan", "break this down", "verify the work", "change task T-0xx", "create a task", "what's next" | **Manager** |
| "do the next task", "implement T-0xx", "work on the next task" | **Worker** |
| anything else | Read `docs/tasks/README.md`; if a task is `ready` → **Worker**; if a task is at `review` → **Manager** (verify it). |

Manager and worker run in **separate sessions**. All handoff happens through files.

## 4. Worker procedure

```
1. Read AGENTS.md (this file) → docs/tasks/README.md
2. Pick the FIRST task with status "ready" whose depends are all "done".
   If nothing is ready → say so and stop.
3. Open that task file. Read it fully. Read only the files in its `files:` list
   and the research doc it references.
4. Claim it: set `status: in-progress`, `owner: <your session label>`, `updated: <timestamp>`.
5. Implement. Keep the change inside the task's stated scope and file list.
6. Run EVERY checkbox under `## Done when`. Record the real output.
7. Append a `## Report` section (template in §6).
8. Set `status: review`. Stop. Do not mark it done — the manager does that.
```

**Session label:** `s-<yyyymmdd-hhmm>` (e.g. `s-20261030-1412`). Put it in `owner:`.

## 5. Manager procedure

```
1. Read AGENTS.md → docs/tasks/README.md → docs/quests/<quest>.md
2. If a task is at "review": VERIFY IT. Don't trust the report.
   - Read the diff / changed files.
   - Re-run every `## Done when` check yourself.
   - Append `## Manager review` with `verdict: accepted | rework` and notes.
   - accepted → set `status: done` in the task file AND the board → release the next task.
   - rework   → set `status: ready` and append the fix list to the task file.
3. If the user asks for a change to an existing task → edit that task file in place.
   If it splits the work → create a NEW task file (e.g. T-014b-…) and mark the original superseded.
4. If the user gives a new idea → add it to `docs/tasks/BACKLOG.md` as a one-liner, then promote it
   into a quest/task when it is worth doing.
5. Keep quests honest: update `docs/quests/Q*.md` status + task table.
```

**The manager must be able to verify a task it never saw built.** That is why every task states
`## Done when` as runnable commands. If a task has no runnable check, fix the task file first.

## 6. Task file format

```markdown
# T-0xx · Short title

- status: ready            # ready | in-progress | review | done | blocked
- quest: Qx
- depends: T-0yy, T-0zz   # or: none
- owner: -                 # session label
- updated: -
- files: path/a.py, path/b.tsx

## Goal
One paragraph. What "good" looks like.

## Done when
- [ ] `command` → expected result
- [ ] `command` → expected result

## Notes / gotchas
Anything the next session must not trip over.

## Research notes
Findings cached while working (versions, URLs, quirks, licence facts).
DO NOT re-research these.

## Work log
- 2026-10-30 s-1412: did X, blocked on Y

## Report
### 2026-10-30 · worker s-1412
- changed: files touched, in one line each
- verified: command → actual result (paste the real output line)
- issues: what broke, what's left
- next: suggested next task

## Manager review
### 2026-10-30 · manager s-1500
- verdict: accepted | rework
- checked: what the manager re-ran
- notes: required changes, if any
```

## 7. Status values

| status | meaning |
|---|---|
| `ready` | dependencies done, can be claimed |
| `in-progress` | a worker owns it right now |
| `review` | worker finished, **manager must verify** |
| `done` | manager verified, checks passed |
| `blocked` | can't proceed — reason must be written in the task file |

## 8. Canonical verification commands

Dev runs inside Docker so the Python version is identical everywhere.

```bash
# infra
docker compose up -d
docker compose ps
docker compose logs -f api

# backend (inside the api container)
docker compose exec api python -m pytest -q
docker compose exec api ruff check .
docker compose exec api ruff format --check .
docker compose exec api python -m prisma generate
docker compose exec api python -m prisma migrate status

# backend (local venv, Windows PowerShell)
cd backend
.\.venv\Scripts\python -m pytest -q

# frontend
cd apps/web
npm run lint
npm run typecheck
npm run build

# smoke
curl http://localhost:8000/api/v1/health
```

A task's `## Done when` must use commands from this table (or a new one added to this file).

## 9. Repo map

```
postly/
├── AGENTS.md                <- you are here
├── README.md
├── docker-compose.yml
├── .env.example
├── docs/
│   ├── PLAN.md              <- product spec + scope
│   ├── ARCHITECTURE.md      <- how the pieces fit
│   ├── DATA_MODEL.md        <- the 19 models, fields, indexes
│   ├── API.md               <- endpoint contract
│   ├── SECURITY.md          <- anonymity design + threat model
│   ├── MODERATION.md        <- providers, policy matrix, thresholds
│   ├── GEO_DATA.md          <- Delhi PIN data: source, licence, seed rule
│   ├── DECISIONS.md         <- ADRs (why we chose X)
│   ├── BACKLOG.md           <- raw ideas inbox
│   ├── research/            <- cached research (read, don't re-search)
│   │   ├── README.md
│   │   └── 00-versions.md
│   ├── quests/              <- Q0..Q5 milestone files
│   └── tasks/               <- one file per task + README.md board
├── apps/
│   └── web/                 <- Next.js (created in T-004)
└── backend/
    ├── pyproject.toml       <- pinned deps + [tool.prisma] pins
    ├── prisma/schema.prisma <- single source of truth for the DB
    ├── app/
    │   ├── main.py
    │   ├── core/            <- config, security, deps
    │   ├── db/              <- prisma client singleton
    │   ├── schemas/         <- pydantic request/response models
    │   ├── api/v1/          <- routers
    │   ├── services/        <- feed ranking, moderation, notifications
    │   └── providers/       <- moderation + storage provider interfaces
    ├── scripts/             <- seed scripts
    └── media/               <- local media storage (gitignored)
```

## 10. Where the truth lives

| Question | File |
|---|---|
| What are we building? | `docs/PLAN.md` |
| How is it put together? | `docs/ARCHITECTURE.md` |
| What are the tables? | `docs/DATA_MODEL.md` |
| What endpoints exist? | `docs/API.md` |
| How does anonymity work? | `docs/SECURITY.md` |
| How is bad content handled? | `docs/MODERATION.md` |
| Where does area data come from? | `docs/GEO_DATA.md` |
| Why did we choose this? | `docs/DECISIONS.md` |
| Which versions? | `docs/research/00-versions.md` |
| What should I work on? | `docs/tasks/README.md` |

## 11. Current state

- **Q0 Foundation is in progress.** See `docs/tasks/README.md`.
- The **compose stack exists and runs**: `db` (`postgres:16.15-alpine`) + `api` (`python:3.13-slim` with
  `libatomic1`), both healthy, migrations applied on boot, `GET /api/v1/health` → `{"status":"ok","db":"ok"}`.
- `backend/app/main.py` is a **minimal skeleton** (health endpoint only). T-002 hardens the image and T-003
  turns it into the real structure.
- `apps/web` does not exist yet — T-004 scaffolds it.
- The Prisma stack is **verified**: prisma-client-py 0.15.0 + Prisma CLI 5.19.0 works on `python:3.13-slim`
  and on local Python 3.14.7. Details in `docs/research/00-versions.md` §4 and §10.
- Versions are already pinned and researched in `docs/research/00-versions.md` — do not re-derive them.
