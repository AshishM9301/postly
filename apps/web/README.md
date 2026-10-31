# Postly · web

The Next.js frontend. It is a **pure REST client** for the FastAPI backend — there is no tRPC, no
NextAuth and no Prisma in the browser. All data goes through the API over plain HTTP.

## Stack

- Next.js 15.5.28 (App Router, `src/`) · React 19.3.1 · TypeScript 5.9.3
- Tailwind CSS 4.3.3 (CSS-first config, `src/styles/globals.css`)
- ESLint 9 · Prettier 3
- Zod 3.25.76 + `@t3-oss/env-nextjs` for env validation

Exact versions live in [`apps/web/package.json`](package.json) (pinned, no `^`/`~`) and are mirrored in
[`docs/research/00-versions.md`](../../docs/research/00-versions.md) §2.

## How it talks to the API

`next.config.js` rewrites `/api/:path*` to `${API_INTERNAL_URL}/api/:path*`:

| Where | `API_INTERNAL_URL` | Resolves to |
|---|---|---|
| Docker Compose (`docker compose up -d`) | `http://api:8000` | the `api` service on the compose network |
| Host `npm run dev` | *(unset → `http://localhost:8000`)* | the API published on the host port |

One base URL, read from config — never hardcoded in a component. The proxy means the browser never
talks to the API cross-origin, so no CORS headers and no API URL leaks into the client bundle.

## Commands

```bash
npm run dev        # next dev --turbo   (http://localhost:3000)
npm run build      # production build
npm run start      # serve the production build
npm run lint       # next lint
npm run typecheck  # tsc --noEmit
npm run check      # lint + typecheck
```

## Docker

`Dockerfile` is a three-stage build (`deps` → `builder` → `runner`) on `node:24.18.0-alpine`. The runner
copies only `.next`, `public`, `node_modules`, `package.json`, `next.config.js` and `src/env.js`, and runs
as the non-root `nextjs` user (uid 1001).

```bash
docker compose up -d web     # or just `docker compose up -d` for the whole stack
```

## Home page

`src/app/page.tsx` is a server component with `export const dynamic = "force-dynamic"`. It fetches its own
`/api/v1/health` so the request travels through the rewrite above (no CORS, no API URL in the browser) and
renders the API + database status. Fetch errors are caught and rendered as `unreachable` instead of throwing.

## Coming later

- T-006 — OpenAPI-generated TypeScript types + a typed fetch client.
- T-020 — TanStack Query, shadcn/ui, feed UI, composer, vote buttons.
