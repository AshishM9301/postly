# T-004 · Frontend scaffold + API proxy + health page

- status: done
- quest: Q0
- depends: T-002
- owner: s-20261030-2003
- updated: 2026-10-31T09:20
- files: apps/web/**, docker-compose.yml, apps/web/Dockerfile

## Goal

Create the Next.js app the way the T3 ecosystem does it, but with the pieces that belong to FastAPI turned
off. The web app must be a **pure REST client**: no tRPC, no NextAuth, no Prisma in the browser. Finish with
a page that proves the frontend can talk to the API.

## Done when

- [x] `npx create-t3-app@7.40.0` produced `apps/web` with TypeScript, Tailwind 4, ESLint, Prettier, App
      Router and `src/` — and **without** tRPC, Prisma or NextAuth.
- [x] `cd apps/web && npm run lint && npm run typecheck && npm run build` all pass.
- [x] The home page renders the API's `/api/v1/health` response (server-side fetch through the proxy, so it
      works without CORS and without exposing secrets).
- [x] `docker compose up -d` also starts the `web` service and `http://localhost:3000` serves the page.
- [x] The versions actually installed are recorded in `docs/research/00-versions.md` §2 (the scaffold's
      choices win over the plan if they differ).

## Notes / gotchas

- Run the scaffolder non-interactively if it supports flags; check `npx create-t3-app@7.40.0 --help` first
  and record the exact command you used in this task's `## Research notes`.
- Decline: tRPC, Prisma, NextAuth (and any auth/db option it offers). Keep: TypeScript, Tailwind, ESLint,
  Prettier, App Router, `src/` directory.
- **Do not force TypeScript 7.** The scaffold is tested against TS 5.8.x; if it offers a newer TS, take what
  it gives and verify `npm run typecheck` and `npm run build` both pass.
- Pin exact versions in `apps/web/package.json` after the scaffold (no `^`/`~`).
- API calls go through a Next.js rewrite/proxy at `/api/:path*` → `http://api:8000` in Docker,
  `http://localhost:8000` when running `next dev` on the host. One base URL from config, never hardcoded in
  components.
- shadcn/ui is added later (T-020); do not install it now unless the scaffold expects it.
- Keep the page dead simple. This task proves the wiring, not the design.

## Research notes

Versions and the dist-tag rule: `docs/research/00-versions.md` §2. If the scaffold offers different versions
than the plan, the scaffold wins **provided** lint, typecheck and build pass — record the difference.

Scaffold command (see `docs/research/00-versions.md` §2 for the full version table):

```
npx --yes create-t3-app@7.40.0 apps/web --CI --noGit --tailwind true --nextAuth false \
  --betterAuth false --prisma false --drizzle false --trpc false --appRouter true \
  --eslint true --biome false --import-alias "@/*"
```

- `--CI` is what makes the feature flags take effect; every boolean feature must be given explicitly or the
  CLI ignores the flag. `--noGit` avoids a nested repo. There is no `--src` flag — the scaffold always uses
  `src/`.
- The CLI scaffolded files but aborted with `TypeError: i.replace is not a function` while installing. Running
  `npm install` in `apps/web` finished the job; nothing was missing afterwards.
- Scaffold resolved TypeScript to **5.9.3** and zod to **3.25.76** (not 4.x). Both are fine; lint, typecheck
  and build pass. Do not force TS 7.
- `npm install` prints `npm warn allow-scripts ... unrs-resolver` and 5 audit advisories in the scaffold's tree.
  Left alone: fixing them means changing pinned versions.
- The `next lint` script is deprecated (removed in Next 16) but still works on Next 15.5.28.
- Proxy: `next.config.js` rewrites `/api/:path*` to `${API_INTERNAL_URL}/api/:path*`. Compose sets
  `API_INTERNAL_URL=http://api:8000`; host `next dev` falls back to `http://localhost:8000`.
- The home page is a server component with `export const dynamic = "force-dynamic"`. It reads the incoming
  `host`/`x-forwarded-host` headers and fetches its **own** `/api/v1/health`, so the request goes through the
  Next rewrite (no CORS, no API URL in the browser). It catches fetch errors and renders `unreachable`
  instead of throwing.
- The web image is `node:24.18.0-alpine`, multi-stage, and runs as `nextjs` (uid 1001). `api` must be healthy
  before `web` starts (`depends_on`).

## Work log

- 2026-10-30 s-20261030-2003: scaffolded `apps/web` non-interactively, finished `npm install` after the CLI
  abort, pinned all versions, added the `/api/:path*` rewrite, replaced the landing page with a live
  server-rendered health card, added the multi-stage `apps/web/Dockerfile` + `.dockerignore`, added the
  `web` compose service, and verified lint/typecheck/build + the running stack.

## Report

### 2026-10-30 · worker s-20261030-2003

- changed:
  - `apps/web/**` — create-t3-app 7.40.0 scaffold (Next 15.5.28, React 19.3.1, Tailwind 4.3.3, TS 5.9.3),
    no tRPC/Prisma/NextAuth.
  - `apps/web/package.json` — every dependency pinned to the exact installed version (no `^`/`~`).
  - `apps/web/next.config.js` — `/api/:path*` rewrite to `API_INTERNAL_URL` (default localhost:8000).
  - `apps/web/src/app/page.tsx` — server component, `force-dynamic`, fetches its own `/api/v1/health`
    through the rewrite and renders API + DB status.
  - `apps/web/Dockerfile` + `apps/web/.dockerignore` — multi-stage `node:24.18.0-alpine`, non-root `nextjs`.
  - `docker-compose.yml` — new `web` service on `${WEB_PORT:-3000}`, waits for `api` healthy, healthcheck.
  - `docs/research/00-versions.md` — §2 records the scaffold command and the exact installed versions.
- verified (real output):
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0;
    `npm run build` → `✓ Compiled successfully`, `/` is `ƒ (Dynamic)`.
  - `docker compose up -d --build web` → `postly-web ... Up ... (healthy)`, ports `0.0.0.0:3000->3000`.
  - `curl http://localhost:3000/api/v1/health` → `{"status":"ok","db":"ok"}` / HTTP 200 (proxy works).
  - `curl http://localhost:3000` → HTTP 200; rendered HTML contains
    `<dd class="text-emerald-400">ok</dd>` for both API and Database.
  - `docker compose exec -T web id` → `uid=1001(nextjs) gid=1001(nodejs)`.
  - no `^`/`~` left in `apps/web/package.json`.
- issues:
  - The scaffolder aborted during dependency installation (`TypeError: i.replace is not a function`); manual
    `npm install` completed it (recorded in research notes).
  - 5 npm audit advisories in the scaffold's transitive deps; not force-fixed (would change pinned versions).
  - The plan said zod 4.x; the scaffold pins zod 3.25.76. Recorded as "scaffold wins".
- next: T-006 (OpenAPI → TypeScript types) once T-003 is accepted, or Q1 T-010.

## Manager review

### 2026-10-31 · manager s-20261031-0920

- verdict: **accepted**
- checked (every `## Done when` re-run by the manager, not taken from the report):
  - Scaffold shape — `apps/web/package.json` has `ct3aMetadata.initVersion: 7.40.0`; `src/app/` (App Router),
    `tsconfig.json`, `tailwindcss` 4.3.3, `eslint.config.js` + `eslint` 9.39.5, `prettier.config.js`.
    Grep over `package.json` + `src/` + every config file for `trpc|prisma|nextauth|next-auth|drizzle|better-auth`
    → **zero hits**. Confirmed no tRPC / Prisma / NextAuth.
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0;
    `npm run build` → `✓ Compiled successfully in 8.7s`, route table shows `/` as `ƒ (Dynamic)`.
  - `GET http://localhost:3000` → 200; the HTML contains exactly **2** × `<dd class="text-emerald-400">ok</dd>`
    (API + Database) and no `unreachable`.
  - `GET http://localhost:3000/api/v1/health` → 200 `{"status":"ok","db":"ok"}` — the rewrite works.
  - `docker compose down` → `docker compose up -d` (cold) → `db`, `api`, `web` all **healthy**;
    `docker compose build --no-cache web` rebuilt the image from scratch without error.
  - `docker compose exec -T web id` → `uid=1001(nextjs) gid=1001(nodejs)` — non-root confirmed.
  - `docs/research/00-versions.md` §2 → the `### Verified installed in apps/web (T-004)` table matches
    `npm ls --depth=0` exactly.
- extra checks the worker did not run:
  - `Select-String '[\^~]' apps/web/package.json` → **empty**; every dependency is pinned exactly.
  - `git check-ignore` → `.env`, `.next/`, `node_modules`, `*.tsbuildinfo`, `next-env.d.ts` are all ignored;
    `git status --untracked-files=all apps/web` lists exactly **17** files to track. No secret or build
    artefact would enter the repo.
  - Host fallback: with `API_INTERNAL_URL` unset, `npm run dev` on the host proxied to
    `http://localhost:8000` → `{"status":"ok","db":"ok"}` and the page rendered `ok`/`ok`. Both runtime
    paths (compose + host dev) work.
  - `docker compose exec api python -m pytest -q` → `1 passed` (the Q0 "runs a real test" gate still holds).
- notes (fixed by the manager during this review, all inside the task's `files:` scope):
  - `apps/web/src/app/layout.tsx` still carried the scaffold metadata `title: "Create T3 App"` /
    `description: "Generated by create-t3-app"` — visible in the served `<title>`. → set to
    `Postly` / `Local problems, community answers.`
  - `apps/web/README.md` was the untouched T3 boilerplate and advertised NextAuth / Prisma / Drizzle / tRPC,
    none of which exist in this project. → replaced with a Postly-specific README (stack, proxy contract,
    commands, Docker layout, what T-006/T-020 add).
  - `docs/research/00-versions.md` §10 claimed the health payload is `{"status":"ok","db":"ok","version":"0.1.0"}`.
    The real payload (verified against `backend/app/api/v1/health.py:20`) has **no** `version` field.
    → corrected in §10 and the "Verified end to end" block now includes the `web` service.
  - `AGENTS.md` §11 still said "`apps/web` does not exist yet" → updated.
  - `README.md` said "Status: pre-implementation" and "Run it (once T-002 lands)" → updated.
- observations (no action required, carried forward):
  - `apps/web/src/app/page.tsx:12-16` derives the upstream URL from the **client-controllable**
    `x-forwarded-host` / `host` headers, so the server will fetch whatever host the caller names — a blind
    host-header/SSRF vector. Harmless for a loopback health page, but **T-006 must not copy this pattern**:
    use a server-side base URL from config for real API calls.
  - `next lint` is deprecated and is removed in Next 16. It still works on 15.5.28; the migration to the
    ESLint CLI is a T-020 chore.
  - The T3 scaffold gitignores `next-env.d.ts`; it is regenerated by `next build`, so a fresh clone needs a
    build before `npm run typecheck` — `npm run build` handles it.
  - 5 npm audit advisories remain in the scaffold's transitive tree; not force-fixed, because that would
    change pinned versions. Revisit when T-006/T-020 add dependencies anyway.
- next: **T-006** is now unblocked (depends on T-003 + T-004, both done).
