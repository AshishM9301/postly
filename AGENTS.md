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

**If you hit an error or a blocker** (the stack breaks, a dependency fights back, the task turns out to be
impossible): do **not** fix it outside the task's scope and do **not** fake a pass. Append a `## Blocker`
section instead (template in §6 and in §12), set `status: blocked`, update the board row, and stop. The
blocker report *is* your deliverable. The manager will diagnose it and create a follow-up task.

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
6. When a task comes back `blocked`, run the **error escalation loop (§12)**: reproduce the failure
   yourself, write your own diagnosis next to the worker's, then create a new task for the fix.
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

## Blocker                        (only when the worker is stuck — see §12)
### 2026-10-30 · worker s-1412
- failed: `command` → the actual error, pasted
- worker diagnosis: what the worker thinks is wrong
- tried: what was attempted
- needs: a decision | a new task | more info

## Manager diagnosis              (manager only — see §12)
### 2026-10-30 · manager s-1500
- reproduced: yes | no  → `command` → output
- worker said: their diagnosis in one line
- manager found: the manager's own diagnosis
- combined conclusion: where they agree, where they differ, and the truth
- root cause: one paragraph
- fix approach: what the fix is
- new task: T-0xx

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

- **Q0 Foundation is done** (T-001 … T-006). Q1 · Core posting loop is next — see `docs/tasks/README.md`.
- The **compose stack exists and runs**: `db` (`postgres:16.15-alpine`) + `api` (`python:3.13-slim` with
  `libatomic1`) + `web` (`node:24.18.0-alpine`), all healthy, migrations applied on boot,
  `GET /api/v1/health` → `{"status":"ok","db":"ok"}`, `http://localhost:3000` serves the web app.
- `backend/app/main.py` is a **minimal skeleton** (health endpoint only). T-002 hardens the image and T-003
  turns it into the real structure.
- `apps/web` **exists** (T-004): Next.js 15.5.28 App Router, Tailwind 4, TypeScript 5.9.3, pure REST client
  — no tRPC, no NextAuth, no Prisma. It proxies `/api/:path*` → `API_INTERNAL_URL` (compose: `http://api:8000`,
  host dev: `http://localhost:8000`). Details in `docs/research/00-versions.md` §2.
- **The frontend's typed API door** (T-006): `apps/web/src/lib/api/` holds the generated `types.ts` (from the
  live OpenAPI spec, regenerate with `npm run api:types` **on the host**) and `client.ts` — the **only** file
  under `src/` allowed to call `fetch`. Server code must pass an absolute base URL built from the trusted
  server-only `API_INTERNAL_URL`; never from the request's `host` / `x-forwarded-host` headers.
  **This is machine-enforced since T-012**: `apps/web/eslint.config.js` bans `fetch(` in `src/**` outside
  `client.ts`, so `npm run lint` fails on a second call site. Use `ApiClient` (or an injected
  `fetchImpl` seam) instead.
- **The ghost vault exists** (T-012): `apps/web/src/lib/ghost/` holds the framework-agnostic crypto
  (`deriveOwnerKey = HMAC-SHA256(secret, targetId)`, base64url, WebCrypto), the alias generator and the
  IndexedDB key vault (post keys + session key, export/import, `deleteOwnPost` through the typed client).
  Tests: `npm run test:ghost` (node:test, 17 cases). The secret never leaves the browser — the server only
  ever sees `owner_key`. The **encoding and the DELETE transport are still unpinned in `docs/API.md`**; T-015
  and T-021 must settle them before a mobile client can interoperate.
- The Prisma stack is **verified**: prisma-client-py 0.15.0 + Prisma CLI 5.19.0 works on `python:3.13-slim`
  and on local Python 3.14.7. Details in `docs/research/00-versions.md` §4 and §10.
- **The real data model exists** (T-010): `backend/prisma/schema.prisma` holds the **18** models and **7** enums
  from `docs/DATA_MODEL.md` (the doc's "19 tables" header was stale — the body always listed 17, plus the
  `AreaName` alias table added in T-014b), with
  migration `20261031060611_init` applied on boot and the 9 categories seeded by
  `backend/scripts/seed_categories.py` (idempotent). The frontend does **not** use the database schema:
  it codes against the OpenAPI spec. Prisma TS declarations under `apps/web/src/generated/` are
  **gitignored** — never import them, never commit them.
- **The 103 Delhi areas are seeded** (T-013): `backend/scripts/seed_areas.py` streams the CC0 India Post
  `pincode.csv` (cached in `backend/.cache/`, gitignored), normalises names and districts, drops dirty
  coordinates and upserts one `Area` row per PIN. Run it **in the container**:
  `docker compose exec api python scripts/seed_areas.py` (`--offline` forbids the 21 MB download). The
  dataset's quirks and the cleaning rules are documented in `docs/GEO_DATA.md`. The seed is **not** part of
  the container boot — a fresh database has no areas.
- **The areas API is live** (T-014, T-014b): `GET /api/v1/areas/search?q=&limit=` (six digits = exact PIN,
  otherwise a case-insensitive substring over the area's display name, its **aliases** — every office name of
  that PIN, so "Karol Bagh" finds 110005 — and its district; `%`, `_` and `\` are literal characters) and
  `GET /api/v1/areas/detect?lat=&lng=` (nearest area, **always** — no distance cut-off — with
  `distance_meters`), plus `GET /api/v1/categories`. No external calls; the nearest-area scan is cached
  in-process for 60 s.
- **Post CRUD is live** (T-015): `POST /api/v1/posts` (201), `GET|PATCH|DELETE /api/v1/posts/{id}` for Google,
  pseudonymous and ghost callers. The id may be client-generated (ghosts need it to pre-compute the
  `owner_key`), the alias is snapshotted on the row, coordinates are rounded to 3 decimals, and the response
  is an explicit allow-list — `ghostOwnerKey`, `secretHash` and `tokenHash` never appear. The `owner_key`
  encoding is now pinned in `docs/API.md` §4 (base64url, body transport). `GET /areas/{id}` returns the area
  with its `post_count`.
- **Media is live** (T-016): `POST /api/v1/media` (multipart, 20 MB cap, Pillow content sniffing, 4×3
  blurHash), `GET /api/v1/media/{id}/signed` (300 s) and `GET /api/v1/media/{id}/file?expires=&sig=` (the only
  reader — there is **no** static mount of `backend/media/`). The signature is
  `HMAC-SHA256(SECRET_KEY, "{media_id}:{expires}")`, separate from the ownership `PEPPER`; deleting the row
  revokes a live URL. `blurhash==1.1.5` is pinned — **rebuild the `api` image** (`docker compose build api`)
  so the image has it, not just the running container.
- **Votes are live** (T-017): `PUT|DELETE /api/v1/votes/{target_type}/{target_id}` for `POST` and `COMMENT`
  targets, counters updated in the same transaction as the vote row. Session voters are keyed server-side
  as `u:<userId>`; ghosts send `a:<base64url HMAC-SHA256(sessionKey, targetId)>` (per target, so one ghost's
  votes cannot be joined across posts). The response carries the fresh counters. `BLAME` is T-050.
  The `Vote` table has **no timestamp** and **no FK to its target** — deleting a post orphans its votes
  (T-021 must sweep them).
- **Comments are live** (T-018): `POST|GET /api/v1/posts/{id}/comments`, `PATCH|DELETE /api/v1/comments/{id}`
  for all three identity modes. Threads nest to `depth ≤ 3` (a deeper reply is a 422, not flattened), the
  listing is flat + cursor-paginated (`parent_id`/`depth` rebuild the tree), and **deleting a comment keeps
  its replies** — the children are promoted to top level and the subtree shifts up. `Post.comment_count` is
  maintained in the same transaction.
- **The feed tabs are live** (T-019): `GET /api/v1/feed/{new,trending,for-you,nearby}` with
  `area_id`/`category_id`/`limit`/`cursor`. The ranking is computed in Python from the post counters —
  `engagement * exp(-age_hours / half_life) * area_boost * affinity_boost` (half-lives 12 h / 18 h, env
  configurable). The cursor pins `now` so page 2 reproduces page 1's scores; HIDDEN posts never appear.
  The formula and the boost rules are in `docs/API.md` §7.
- Versions are already pinned and researched in `docs/research/00-versions.md` — do not re-derive them.
- The repo is a git repository on branch `main`. **The manager may commit**; workers must not.

## 12. Error escalation loop (worker error → manager diagnosis → new task)

Nothing gets hand-waved. When something breaks, it goes through this loop. It is the same loop the manager
already used once, for the T-001 database confusion.

### Step 1 — Worker reports the failure
The worker does **not** fix it outside the task's scope and does **not** fake a pass. It appends to the
task file:

```markdown
## Blocker
### 2026-10-30 · worker s-1412
- failed: `command` → the actual error, pasted
- worker diagnosis: what the worker thinks is wrong
- tried: what was attempted
- needs: a decision | a new task | more info
```

Then sets `status: blocked`, updates the board row to `[!]`, and **stops**. The blocker report is the
deliverable this time — a clean blocker beats a messy half-fix.

### Step 2 — Manager reproduces it, independently
Never accept the worker's diagnosis on trust. Run the failing command yourself, read the actual code, and
form your own diagnosis. If you cannot reproduce it, say so — do not guess.

### Step 3 — Manager writes the combined diagnosis
In the same task file:

```markdown
## Manager diagnosis
### 2026-10-30 · manager s-1500
- reproduced: yes | no  → `command` → output
- worker said: their diagnosis in one line
- manager found: the manager's own diagnosis
- combined conclusion: where they agree, where they differ, and the truth
- root cause: one paragraph
- fix approach: what the fix is
- new task: T-0xx
```

### Step 4 — Manager creates a new task for the fix
- A **real file**: `docs/tasks/T-0xx-<slug>.md`, created from `docs/tasks/_TEMPLATE.md`.
- It has a goal, runnable `## Done when` checks, a `files:` list, and `depends:` pointing at the task that
  exposed the bug.
- Link it from `docs/tasks/README.md` (board row + error log) and from the original task file.
- The original task stays `blocked`, or is closed as `done` if the bug turned out to be outside its scope.
  It is never silently left `ready`.

### Step 5 — Worker fixes it
The worker picks up the new task, fixes the bug, appends its report, and sets `status: review`. The manager
verifies it like any other task — and then closes the loop by appending the outcome to the original task's
`## Manager diagnosis` section.

### Rules
- The worker's diagnosis is **input**, not truth. The manager's own reproduction decides.
- Where the two disagree, the manager says so explicitly and shows the evidence.
- "Not reproduced" is a legitimate outcome — record what was tried and move on. Guessing is not allowed.
- Every failure gets a task id, so the error log in `docs/tasks/README.md` stays countable.
- The same loop applies when the *manager's own* verification fails: the manager writes the diagnosis and
  creates the fix task.
