# ARCHITECTURE

## 1. Shape

```
┌──────────────────────────┐        REST / JSON        ┌────────────────────────────┐
│  apps/web                │  ───────────────────────► │  backend (FastAPI)         │
│  Next.js 15 App Router   │   /api/v1/*               │  routers → services → ORM  │
│  Tailwind 4 + shadcn/ui  │   Bearer <token>          │                            │
│  TanStack Query          │                           │  providers/                │
└──────────────────────────┘                           │   moderation (4 providers) │
        ▲                                               │   storage (local → S3)    │
        │                                               └─────────────┬──────────────┘
        │ localStorage / IndexedDB                                  │ prisma-client-py
        │ ghost keys (never sent, only HMACs are)                   ▼
        │                                                   ┌────────────────────┐
        │                                                   │ PostgreSQL 16      │
        │                                                   └────────────────────┘
        │                                                           ▲
        │                                            local disk media/ (signed URLs)
        └──────────────────────────────────────────────────────────┘
```

There is **no tRPC and no NextAuth**. The web app is a plain REST client of FastAPI. That is deliberate:
one API surface for the web, the future Kotlin app and the future Swift app.

## 2. Why Prisma from Python

`backend/prisma/schema.prisma` is the single source of truth for the database. The Python side uses
`prisma-client-py` (pip package `prisma`), which ships its **own** Prisma CLI (5.19.0) and Rust query
engine — the npm `prisma` package is never installed. The frontend can generate a TypeScript Prisma client
from the same schema for **types only**; the browser never touches the database.

## 3. Backend layout

```
backend/
  pyproject.toml          pinned deps + [tool.prisma] version pins
  prisma/schema.prisma    source of truth
  prisma/migrations/      generated
  app/
    main.py               FastAPI app, CORS, router mounting, lifespan (prisma connect)
    core/
      config.py           pydantic-settings, env parsing
      security.py         token issue/verify, HMAC helpers, pepper usage
      deps.py             FastAPI dependencies (current principal, pagination)
    db/client.py          Prisma singleton + lifespan connect/disconnect
    schemas/              pydantic v2 request/response models (one module per domain)
    api/v1/               routers: auth, me, posts, comments, votes, feed, areas,
                          categories, users, follows, reports, notifications, push,
                          media, reveals, admin, health
    services/
      feed.py             ranking + feed queries
      moderation.py       orchestration across providers, policy mapping
      notifications.py    fan-out + delivery
      expiry.py           ghost post expiry sweep
      ratelimit.py        rotating-IP-hash limits
    providers/
      moderation/         rule, openai, local_hf, llm, null
      storage/            local, (s3 later)
    scripts/              seed_areas.py, seed_categories.py
  media/                  local uploads (gitignored)
```

Rule of thumb: routers validate and delegate; services own business rules; providers wrap the outside
world behind an interface so they can be swapped by env var.

## 4. Request lifecycle

1. `Bearer` token → `core/deps.py` resolves the principal:
   - **Google** → Firebase ID token verified by `firebase-admin`, mapped to a `User` row by `firebaseUid`.
   - **Pseudonymous** → our own opaque session token → `User` row by `session.tokenHash`.
   - **Ghost** → no session record; the request carries an `ownerKey`/HMAC that is *verified per row*.
2. Router validates the body with a pydantic model.
3. Service applies business rules + moderation + rate limits.
4. Provider layer talks to the outside world (OpenAI, disk, HF models).
5. Response is a pydantic model; envelope is `{ "data": ..., "meta": ... }`.

## 5. Identity modes (summary)

| Mode | Server state | Proof of ownership |
|---|---|---|
| Google | `User.firebaseUid` | Firebase ID token |
| Pseudonymous | `User.alias` + `Session.tokenHash` + `User.secretHash` | session token (delete account also wants the secret) |
| Ghost | **none** — no `User` row, no `Session` row | client-held secret; server stores `HMAC(secret, targetId)` only |

Full detail and threat model: `docs/SECURITY.md`.

## 6. Media flow

1. Client `POST /api/v1/media` (multipart) → server validates mime/size → writes to `media/<yyyy>/<mm>/<uuid>.<ext>`.
2. Server computes a **blurHash** for images and writes a thumbnail.
3. Moderation runs on the media (image model, or sampled frames for video).
4. Serving is **never** a public static mount. `GET /api/v1/media/{id}/signed` checks the caller and the
   reveal state, then returns a short-lived HMAC-signed URL. Without it, the original file is unreachable
   even if its path leaks.

## 7. Feed flow

Counters (`upvote_count`, `comment_count`, `view_count`, …) live on `Post` and are updated inside the same
transaction as the vote/comment. Ranking is computed in SQL at query time from those counters plus
`created_at`, `area_id` and the principal's follows. Cursor pagination on `(score, id)`; the exact cursor
strategy is decided in T-019.

## 8. Moderation flow

`providers/moderation/` exposes one protocol with four implementations. `MODERATION_CHAIN` decides the
order (`rules,openai,local-hf`). Results are normalised into categories + severity, mapped to a policy in
`docs/MODERATION.md`, and stored on the target (`moderation_state`) plus a `ModerationRecord` audit row.
The heavy local models run in a **separate worker process/container** so inference never blocks the API.

## 9. Environments

| | Local (now) | Later |
|---|---|---|
| API | `docker compose` → `localhost:8000` | same image on any VPS / container host |
| Web | `docker compose` → `localhost:3000` | Vercel or the same container |
| DB | `postgres:16-alpine` container | managed Postgres |
| Media | local disk volume | S3/R2 via `StorageProvider` |

Everything is localhost-only for now. Turnstile/captcha is deliberately absent; a captcha is added at
public launch when there is a real domain to protect.

## 10. How the source reaches the container

**One copy of the source, always.** The api image installs the package **editable** (`pip install -e .`),
so `site-packages` holds a pointer to `/app` rather than a second copy of the code.

- In dev, `/app` is the bind mount of `./backend`, so editing a file on the host is instantly the code
  that runs. No rebuild, and no stale copy.
- Running the image standalone (no bind mount), `/app` is the source copied into the image — the editable
  pointer resolves to it and everything still works.
- For a **production** image, swap the editable install for a normal `pip install .` so the package is
  baked in and `/app` is not bind-mounted.

Package discovery is `setuptools.packages.find` with `include = ["app*"]`, so `app` and every subpackage
(`app.core`, `app.db`, `app.api.v1`, `app.schemas`, …) are always installed. A literal package list would
silently drop subpackages as the tree grows.

The Prisma client is the one thing that is **not** in `/app`: it is generated into `site-packages/prisma`,
which is why that directory is chowned to the runtime user — `python -m prisma generate` has to be runnable
inside the live container.
