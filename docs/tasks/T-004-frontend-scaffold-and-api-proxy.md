# T-004 · Frontend scaffold + API proxy + health page

- status: ready
- quest: Q0
- depends: T-002
- owner: -
- updated: -
- files: apps/web/**, docker-compose.yml, apps/web/Dockerfile

## Goal

Create the Next.js app the way the T3 ecosystem does it, but with the pieces that belong to FastAPI turned
off. The web app must be a **pure REST client**: no tRPC, no NextAuth, no Prisma in the browser. Finish with
a page that proves the frontend can talk to the API.

## Done when

- [ ] `npx create-t3-app@7.40.0` produced `apps/web` with TypeScript, Tailwind 4, ESLint, Prettier, App
      Router and `src/` — and **without** tRPC, Prisma or NextAuth.
- [ ] `cd apps/web && npm run lint && npm run typecheck && npm run build` all pass.
- [ ] The home page renders the API's `/api/v1/health` response (server-side fetch through the proxy, so it
      works without CORS and without exposing secrets).
- [ ] `docker compose up -d` also starts the `web` service and `http://localhost:3000` serves the page.
- [ ] The versions actually installed are recorded in `docs/research/00-versions.md` §2 (the scaffold's
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

Add the exact scaffold command, any prompts you answered, and the flag list to this task's
`## Research notes` so later frontend tasks do not repeat the discovery.

## Work log

## Report

## Manager review
