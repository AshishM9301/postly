# TASK BOARD

The manager owns this file. Workers only touch their own task file.

**Status:** `ready` · `in-progress` · `review` · `done` · `blocked`

Legend: `[ ]` ready · `[~]` in-progress · `[>]` review · `[x]` done · `[!]` blocked

---

## Q0 · Foundation — *goal: docker compose runs the stack; sessions never re-research*

| ID | Task | Status | Owner | Depends |
|---|---|---|---|---|
| T-001 | Version lock + environment proof | [x] | s-20261030-1823 | none |
| T-002 | Repo skeleton + Docker Compose | [x] | s-20261030-1914 | T-001 |
| T-003 | FastAPI skeleton + Prisma client + health | [x] | s-20261030-1934 | T-002 |
| T-004 | Frontend scaffold + API proxy + health page | [x] | s-20261030-2003 | T-002 |
| T-005 | Docs set + AGENTS.md contract | [x] | manager | none |
| T-006 | OpenAPI → TypeScript types + typed fetch client | [ ] | - | T-003, T-004 |

## Q1 · Core posting loop — *goal: post a photo problem in a Delhi area, vote, comment*

| ID | Task | Status | Owner | Depends |
|---|---|---|---|---|
| T-010 | Prisma schema (19 models) + migration + seed categories | [ ] | - | T-003 |
| T-011 | Auth: Google + pseudonymous + ghost + session middleware | [ ] | - | T-010, T-004 |
| T-012 | Ghost crypto helpers + local key vault + export/import | [ ] | - | T-004 |
| T-013 | Delhi area seed script (pincode.csv, CC0) | [ ] | - | T-010 |
| T-014 | Areas API: PIN lookup, GPS nearest, name search | [ ] | - | T-013 |
| T-015 | Post CRUD + client-generated ids + alias snapshot | [ ] | - | T-011, T-014 |
| T-016 | Media upload + blurHash + signed-URL serving | [ ] | - | T-015 |
| T-017 | Votes (up/down) + salted voter keys + counters | [ ] | - | T-015 |
| T-018 | Comments + nested threads + comment votes | [ ] | - | T-015, T-017 |
| T-019 | Feed tabs (for-you / trending / new / nearby) + ranking | [ ] | - | T-016, T-017, T-018 |
| T-020 | Frontend: feed UI, post card, composer, vote buttons | [ ] | - | T-015, T-019 |
| T-021 | Delete flows: post, account, ghost purge, removal request | [ ] | - | T-011, T-012, T-015 |

## Q2 · Moderation & safety — *goal: blurred warnings, reveals, admin queue, no bot floods*

| ID | Task | Status | Owner | Depends |
|---|---|---|---|---|
| T-030 | Moderation provider interface + policy mapping | [ ] | - | T-003 |
| T-031 | Rule provider: EN/Hindi lexicons, PII leak, spam | [ ] | - | T-030 |
| T-032 | OpenAI provider (`omni-moderation-latest`) + thresholds | [ ] | - | T-030 |
| T-033 | Local HuggingFace provider + video frame sampling | [ ] | - | T-030 |
| T-034 | Moderation worker process + queue | [ ] | - | T-032, T-033 |
| T-035 | Blur UI + warning + reveal flow + signed media URLs | [ ] | - | T-016, T-034 |
| T-036 | Reports + admin moderation queue | [ ] | - | T-019, T-034 |
| T-037 | Rate limiting + honeypot + timing heuristic + quotas | [ ] | - | T-011, T-015 |

## Q3 · Privacy & anonymity hardening — *goal: the privacy promises are enforced and proven*

| ID | Task | Status | Owner | Depends |
|---|---|---|---|---|
| T-040 | Ghost expiry sweep + per-session expiry preference | [ ] | - | T-021 |
| T-041 | Logout warning + key export/import UI | [ ] | - | T-012, T-021 |
| T-042 | Unlinkability audit test + deletion completeness test | [ ] | - | T-021, T-040 |
| T-043 | Privacy policy + security docs pass | [ ] | - | T-042 |

## Q4 · Community layer

| ID | Task | Status | Owner | Depends |
|---|---|---|---|---|
| T-050 | Post status workflow + blame target + blame votes | [ ] | - | T-019 |
| T-051 | Public profiles + user posts + follows | [ ] | - | T-011, T-019 |
| T-052 | In-app notifications + Web Push (VAPID) | [ ] | - | T-050, T-051 |
| T-053 | Ward-level areas (OSM admin boundaries) | [ ] | - | T-014 |
| T-054 | Search + share links + Open Graph images | [ ] | - | T-019, T-020 |

## Q5 · Mobile-ready

| ID | Task | Status | Owner | Depends |
|---|---|---|---|---|
| T-060 | API versioning + exported OpenAPI spec | [ ] | - | T-006 |
| T-061 | Retrofit + SwiftGen codegen notes | [ ] | - | T-060 |
| T-062 | Refresh-token rotation + session management UI | [ ] | - | T-011 |
| T-063 | S3/R2 storage provider + presigned uploads | [ ] | - | T-016 |

---

## Notes

- **Only Q0 and Q1 have task files written.** Q2–Q5 are planned; the manager writes the task files when the
  quest opens. Do not start a planned task without a file.
- New task files are created by the manager from [`_TEMPLATE.md`](_TEMPLATE.md).
- Raw ideas go to [`../BACKLOG.md`](../BACKLOG.md), not here.
- A task is **done** only after the manager re-runs its `## Done when` checks and appends a
  `## Manager review` verdict. Workers never mark their own task done.
- A **blocked** task is a first-class outcome, not a failure: the worker writes a `## Blocker`, the manager
  reproduces it and creates a fix task. See `AGENTS.md` §12.

## Error log

One row per failure that went through the escalation loop (`AGENTS.md` §12). The manager owns this table.

| # | found in | symptom | manager's own diagnosis | fix | status |
|---|---|---|---|---|---|
| 1 | T-001 | `docker compose up` could not bind Postgres to 5432; a chained `&&` aborted at `prisma migrate status` | Two separate things: (a) host port 5432 was held by an unrelated container `coursehub-postgres` (`postgres:18-alpine`); (b) `prisma migrate status` **exits 1 when migrations are pending**, which silently broke a `&&` chain | (a) stopped that container (data intact) and gave Postly its own `postgres:16.15-alpine`; (b) documented in `docs/research/00-versions.md` §10 | closed |
| 2 | T-001 | worker could not find a database to migrate against | The task's suggested command put the spike DB on **5433** precisely because 5432 was occupied — the worker had already avoided the clash; the manager had misread the setup | none needed | closed |
