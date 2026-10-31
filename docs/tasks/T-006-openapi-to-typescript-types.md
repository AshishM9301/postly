# T-006 · OpenAPI → TypeScript types + typed fetch client

- status: done
- quest: Q0
- depends: T-003, T-004
- owner: s-20261031-1044
- updated: 2026-10-31T13:36
- files: apps/web/package.json, apps/web/src/lib/api/types.ts, apps/web/src/lib/api/client.ts, apps/web/src/lib/api/index.ts, apps/web/scripts/generate-api-types.ts, apps/web/src/app/page.tsx, apps/web/src/env.js, apps/web/README.md, apps/web/tsconfig.json, backend/app/api/v1/health.py, docs/API.md, docs/research/00-versions.md

## Goal

Give the frontend a single typed door to the API. The FastAPI app publishes an OpenAPI spec; a script turns
that spec into TypeScript types; a thin client wraps `fetch` with those types, one method per endpoint
group, one place for the base URL and the auth header. No tRPC — this replaces it.

## Done when

- [x] `npm run api:types` regenerates `apps/web/src/lib/api/types.ts` from the running API's OpenAPI spec and
      fails loudly if the API is not reachable.
- [x] `apps/web/src/lib/api/client.ts` exposes typed methods (`health()`, later `posts.list()`, `votes.cast()`…)
      and is the **only** place that calls `fetch` — `grep -rn "fetch(" apps/web/src/` must match **only**
      `apps/web/src/lib/api/client.ts`. The codegen script in `apps/web/scripts/` is exempt (it talks to the
      spec, not to the API).
- [x] `npm run typecheck` passes, and a deliberately wrong call to a typed method fails to compile (prove it
      once, then revert).
- [x] `npm run build` passes.
- [x] `docs/API.md` lists the base URL, the auth header and the error envelope — and the client matches it.
- [x] The client lives under `apps/web/src/lib/api/` so the `~/*` alias reaches it, and the home page
      (`apps/web/src/app/page.tsx`) calls the API **through the client**, using a **trusted** server-side base
      URL. `docs/research/00-versions.md` §2 records `openapi-typescript` at its actually-installed version.

## Notes / gotchas

- Use `openapi-typescript` (pin an exact stable version). The generated file is committed; the script is
  re-runnable.
- **Codegen runs on the host, not in the production image.** The API is published on host port `8000`, so
  `npm run api:types` on the host reaches `http://localhost:8000/openapi.json` out of the box. The Docker
  `web` image is a slim runtime: it carries only `.next`, `public`, `node_modules`, `package.json`,
  `next.config.js` and `src/env.js`, so `npm run api:types` **fails inside the container**
  (`MODULE_NOT_FOUND` — `scripts/` is not copied). Do not add the codegen tool to the runtime image; a
  container that has the source tree can point at the spec with `API_INTERNAL_URL=http://api:8000`.
- The client must handle the envelope: `{ data, meta }` on success, `{ error: { code, message } }` on
  failure. One error type, thrown as a typed `ApiError`.
- The auth header is `Authorization: Bearer <token>`. The token source is decided in T-011 — for now the
  client accepts an optional token getter function so it does not need rewriting later.
- Do not add `any` anywhere. If a type is missing, fix the API model, not the type assertion.
- Keep the client framework-agnostic (no React hooks inside it) so a future mobile client can copy the shape.
- **A Server Component cannot use the relative default base URL.** `fetch("/api/v1/health")` throws in Node
  ("Failed to parse URL"). Server code must pass an **absolute** `baseUrl`.
- **Never build the upstream URL from the request's `host` / `x-forwarded-host` headers.** Those headers are
  client-controlled, so a server that fetches them will fetch whatever host the caller names — a blind
  SSRF / host-header-poisoning vector. Use a trusted server-side value (`API_INTERNAL_URL`).

## Research notes

The endpoint contract this task codes against: `docs/API.md`. Versions: `docs/research/00-versions.md` §2.

If the OpenAPI generator has trouble with FastAPI's schema (multipart endpoints, unions), record the
workaround here — later tasks hit the same thing.

### Findings (2026-10-31, s-20261031-0944)

- `openapi-typescript` pinned to **7.13.0** (npm `dist-tags`: `latest: 7.13.0`, `next: 7.0.0-rc.1`; 7.13.0
  is stable). Programmatic API used: `openapiTS(spec)` + `astToString(ast)`.
- The script runs with plain `node` — **Node 24.18.0 strips TypeScript types natively**, so no `tsx` /
  `ts-node` dependency was added.
- The OpenAPI document lives at **`/openapi.json` (root)**, not under `/api/v1`. The script reads
  `API_INTERNAL_URL` (default `http://localhost:8000`) and appends `/openapi.json`.
- **FastAPI endpoints that return `JSONResponse` have no response schema in the spec** unless the decorator
  declares one. `/health` was returning an empty schema, so `health.py` now declares
  `response_model=HealthResponse` (plus the `503` model). Any later `JSONResponse` endpoint needs the same
  or the generated types will be `unknown`.
- The generated file needs `/* eslint-disable */`: `@typescript-eslint/consistent-indexed-object-style`
  rejects openapi-typescript's `[name: string]: unknown` index signatures. The header is injected by the
  generator, so regeneration keeps it.
- Uvicorn in compose runs **without `--reload`**; restart the `api` service after changing a route before
  re-running `npm run api:types`.
- **The client cannot be imported by plain Node.** `client.ts` / `index.ts` use extensionless relative
  imports (`./client`, `./types`), which Node's ESM resolver rejects (`ERR_MODULE_NOT_FOUND`). It works
  inside Next.js (`moduleResolution: "Bundler"`), so the app is fine — but a plain-Node unit test would
  need explicit `.ts` extensions or a loader. There is no test runner in `apps/web` yet.

### Addendum (2026-10-31, manager s-20261031-1005)

- The runtime `web` image carries only `.next`, `public`, `node_modules`, `package.json`, `next.config.js`
  and `src/env.js`. `scripts/` and `lib/` are **not** copied, so `npm run api:types` inside the container
  dies with `MODULE_NOT_FOUND`. Codegen is a host-side command; the API is published on host port `8000`.
- `openapi-typescript` 7.13.0 is not yet written into `docs/research/00-versions.md` §2 (line 45 still says
  "latest stable", line 83 still lists it as "not installed yet").

### Addendum (2026-10-31, manager s-20261031-1336)

- **Next.js App Router treats `_`-prefixed folders as *private* — they are not routable.** A temporary probe
  route placed in `src/app/__probe/route.ts` answered **404** (`GET /__probe 404`), even though the file was
  valid. Renaming the folder to `src/app/probeTmp/` made it routable at once. When you need a temporary
  route for a runtime probe, do **not** prefix the folder with `_` (and do not prefix it with `(`/`@`).
- **A deleted route leaves stale type references in `.next/types/validator.ts`.** After deleting the probe
  route, `npm run typecheck` failed with
  `.next/types/validator.ts(62,39): error TS2307: Cannot find module '../../src/app/probeTmp/route.js'`.
  `tsconfig.json` includes `.next/types/**/*.ts`, so the stale artifact is type-checked. Fix: delete `.next`
  (or rebuild) — the source was fine. This bites whenever a route is removed, not only for probes.
- **`grep`/`rg` are not installed on this Windows host**; the "only fetch call site" check was done with the
  Grep tool, and the file-hash idempotency check with `Get-FileHash -Algorithm SHA256`.

## Work log

- 2026-10-31 s-20261031-0944: pinned `openapi-typescript@7.13.0`, added the generator script, generated
  `lib/api/types.ts`, added the typed `ApiClient` (`health()`, envelope handling, `ApiError`, token getter),
  added a response model to `/health`, verified typecheck/build/lint and the failure path.
- 2026-10-31 s-20261031-1044: rework — moved the client to `src/lib/api/`, made the home page use it with a
  trusted absolute `API_INTERNAL_URL`-derived base, added `API_INTERNAL_URL` to env validation, recorded
  `openapi-typescript` 7.13.0 in the versions doc, documented host-side codegen, and re-verified the full
  stack including Docker and host `next dev`.

## Report

### 2026-10-31 · worker s-20261031-0944

- changed:
  - `apps/web/package.json` — added `api:types` script + exact `openapi-typescript@7.13.0` devDependency.
  - `apps/web/scripts/generate-api-types.ts` — fetches the spec from `API_INTERNAL_URL`, generates the types,
    exits 1 with a clear message when unreachable.
  - `apps/web/lib/api/types.ts` — generated from the live spec (committed, 80 lines).
  - `apps/web/lib/api/client.ts` — the only `fetch` call site: default base `/api/v1`, `Authorization: Bearer`,
    `{ data, meta }` unwrapping, one `ApiError` type, optional `getToken`, `health()`.
  - `apps/web/lib/api/index.ts` — barrel export.
  - `backend/app/api/v1/health.py` — `HealthResponse` response model so the spec has a real health type.
  - `docs/API.md` — corrected the `/health` example to the actual body (no `version` field).
- verified:
  - `npm run api:types` → `[api:types] wrote ...\apps\web\lib\api\types.ts`
  - `API_INTERNAL_URL=http://localhost:9999 npm run api:types` → printed `could not reach the API at
    http://localhost:9999/openapi.json: fetch failed` and exited `1`.
  - deliberate wrong call `health.does_not_exist` → `error TS2339: Property 'does_not_exist' does not exist
    on type '{ status: "ok" | "degraded"; db: "ok" | "down"; }'`; file deleted, typecheck clean again.
  - `npm run typecheck` → exit 0, no output.
  - `npm run lint` → `✔ No ESLint warnings or errors`.
  - `npm run build` → `✓ Compiled successfully`, `✓ Generating static pages (3/3)`.
  - `docker compose exec -T api ruff check .` → `All checks passed!`; `ruff format --check .` → `12 files
    already formatted`.
  - `docker compose exec -T api python -m pytest -q` → `1 passed, 1 warning`.
  - `GET http://localhost:8000/api/v1/health` → `{"status": "ok", "db": "ok"}`.
- issues:
  - Adding `openapi-typescript` raised the tree's audit count from 5 to 22 advisories (18 moderate, 4 high),
    all transitive devDependencies of `@redocly/openapi-core`. Nothing was force-fixed.
  - `docs/API.md` was already describing the envelope/auth/base URL, so only the health example needed a fix.
  - The client default base URL is relative (`/api/v1`) for the browser/Next proxy. Server Components must
    pass an absolute `baseUrl` (e.g. the request origin) when they start using it — the current health page
    still fetches directly and was intentionally left alone (outside this task's file list).
- next: T-010 (Prisma schema), then T-011 can wire `getToken` into `createApiClient`.

## Manager review

### 2026-10-31 · manager s-20261031-1005

- verdict: **rework** — the client is good, the wiring around it is not finished.
- checked (re-run by the manager, not taken from the report):
  - `npm run api:types` → `[api:types] wrote ...\apps\web\lib\api\types.ts`; re-running it produced a
    **byte-identical** file (deterministic).
  - `API_INTERNAL_URL=http://localhost:9999 npm run api:types` → `[api:types] could not reach the API at
    http://localhost:9999/openapi.json: fetch failed`, exit **1**. Fails loudly. ✓
  - `npm run typecheck` → exit 0. Deliberate wrong call reproduced independently:
    `src/__probe.ts(5,12): error TS2339: Property 'does_not_exist' does not exist on type
    '{ status: "ok" | "degraded"; db: "ok" | "down"; }'`, exit 2. Probe deleted, typecheck clean again. ✓
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run build` → `✓ Compiled successfully`. ✓
  - `docs/API.md` → base URL `/api/v1` (line 3), `Authorization: Bearer <token>` (line 17), error envelope
    `{ error: { code, message, details } }` (line 14). The client matches all three. ✓
  - `openapi.json` really carries `HealthResponse` (enum `status`/`db`) and both the 200 and 503 responses.
  - `docker compose exec -T api ruff check .` → `All checks passed!`; `ruff format --check .` →
    `12 files already formatted`; `python -m pytest -q` → `1 passed`. ✓
  - `npm view openapi-typescript dist-tags` → `latest: 7.13.0`, `next: 7.0.0-rc.1` — the pin is the current
    stable release and not a prerelease. ✓
  - No `any` in `lib/api/**` or `scripts/**`. ✓ `npm audit` → 22 advisories (18 moderate, 4 high), all in
    transitive devDependencies — matches the report.
  - `types.ts` is **not** gitignored, so the generated file will be committed. ✓
  - **Runtime proof of the client** (the report had none, and nothing in the repo calls the client): I added
    a temporary Next route that exercised it and then deleted it —
    `health()` → `{"status":"ok","db":"ok"}`; a 404 → `ApiError{status:404}`;
    an unreachable host → `ApiError{status:0, code:"network_error"}`;
    `Authorization: Bearer probe-token` sent when `getToken` is supplied and **absent** when it is not;
    `Accept: application/json` always. The client behaves exactly as specified. ✓
- why rework (the blocking item):
  - **Done-when #2 is not met: `client.ts` is not the only place that calls `fetch`.**
    `grep -rn "fetch(" apps/web/src/` matches **two** files:
    `src/app/page.tsx:19` and `src/lib/api/client.ts`. The home page — the app's only API consumer — still
    fetches `/api/v1/health` directly, so the "single typed door" has a door around it. The worker flagged
    this honestly in the report, but the task's own `files:` list excluded `page.tsx`, so the done-when could
    not be satisfied as written. **That was a defect in the task file, not in the work.** The fix list below
    widens the scope.
  - **`apps/web/lib/api/` is outside `src/`**, so the scaffold's `~/*` alias (`→ ./src/*`) does not reach it.
    Every consumer inside `src/` would have to import it with a relative path (`../../lib/api`). Manager
    decision: the client moves to `apps/web/src/lib/api/` so one alias covers the whole app.
- fix list (worker):
  1. **Move the client under `src/`.** `apps/web/lib/api/{types,client,index}.ts` → `apps/web/src/lib/api/`.
     Update the generator's output path (`apps/web/scripts/generate-api-types.ts` → `../src/lib/api/types.ts`)
     and every import. `apps/web/tsconfig.json` should need no change (`~/*` already maps to `./src/*`, and
     `include` already covers `**/*.ts`).
  2. **Make the home page use the client.** `apps/web/src/app/page.tsx` must call
     `createApiClient({ baseUrl: <absolute> })` instead of `fetch`.
     - The base URL **must** come from a trusted server-side value — `API_INTERNAL_URL` — **never** from the
       request's `host` / `x-forwarded-host` headers. Those are client-controlled, so building the upstream
       URL from them is a blind SSRF / host-header-poisoning vector (the same one flagged in the T-004
       review). The worker's report suggested "the request origin" — do **not** do that.
     - The relative default `/api/v1` **cannot** be used from a Server Component (Node cannot parse a
       relative URL). Pass an absolute base.
     - Add `API_INTERNAL_URL` to `apps/web/src/env.js` (server schema) if you use it there.
     - The page must still render `ok` / `ok` in Docker **and** in host `next dev`, and must still degrade to
       `unreachable` instead of throwing when the API is down.
  3. **Prove the "only fetch call site" claim**: `grep -rn "fetch(" apps/web/src/` must match exactly one
     file, `apps/web/src/lib/api/client.ts`. (The codegen script in `apps/web/scripts/` is exempt — it talks
     to the spec, not to the API. Say so in the report.)
  4. **Record the pinned version.** `docs/research/00-versions.md` §2: `openapi-typescript` → `7.13.0`, and
     remove it from the "not installed yet" list on line 83 (line 45 still says "latest stable").
  5. **Document codegen as a host-side command.** `apps/web/README.md` gains a "Regenerate API types"
     section: run it on the host (the API is published on `:8000`); it does **not** work inside the
     production `web` image (the image has no `scripts/`). Do not add the codegen tool to the runtime image.
  6. **Re-verify everything** and paste the real output: `npm run api:types` (idempotent), the
     unreachable-API failure path, `npm run typecheck`, `npm run lint`, `npm run build`,
     `docker compose up -d --build web`, `GET http://localhost:3000` → 200 with `ok`/`ok`, and the grep in
     point 3.
- notes (no action required, carried forward):
  - `client.ts` cannot be imported by **plain Node** (extensionless `./client` / `./types` imports fail under
    Node's ESM resolver). Fine inside Next.js. If a unit-test runner is added later, either use explicit
    `.ts` extensions or add a loader.
  - The live API still returns FastAPI's default `{"detail": ...}` for 404/422, **not** the documented
    `{ error: { code, message } }` envelope, so the client's `internal_error` fallback is what actually
    fires today. The client matches the *documented* contract (which is what this task asks for); the API
    side needs real exception handlers when the first business endpoints land (T-015+). Not a T-006 defect.
  - `health.py` declares `response_model=HealthResponse` but returns a raw `JSONResponse`, so FastAPI skips
    response validation — the model is documentation + schema only. Works; noted.
  - `openapi-typescript` adds 17 audit advisories, all in transitive devDependencies of
    `@redocly/openapi-core`. Not force-fixed (that would change pinned versions).
  - The exported singleton `api = createApiClient()` carries the relative default base, so it is unusable
    from a Server Component. Consider not exporting it until T-011 wires up `getToken`.
- next: after the rework, **T-006** can be accepted and **T-010** released.

## Report

### 2026-10-31 · worker s-20261031-1044 (rework)

- changed:
  - `apps/web/src/lib/api/{types,client,index}.ts` — moved from `apps/web/lib/api/`; `~/*` now reaches the
    client. `apps/web/lib/` is gone.
  - `apps/web/scripts/generate-api-types.ts` — output is now `../src/lib/api/types.ts`.
  - `apps/web/src/app/page.tsx` — no longer calls `fetch`; builds the client from
    `${API_INTERNAL_URL}/api/v1` (trusted env, never request headers) and catches failures as before.
  - `apps/web/src/env.js` — `API_INTERNAL_URL` added to the server schema (URL, default
    `http://localhost:8000`).
  - `apps/web/README.md` — added "Regenerate API types" (host-only; not in the runtime image) and updated the
    home-page description.
  - `docs/research/00-versions.md` §2 — `openapi-typescript` → `7.13.0` (line 45); removed from "not
    installed yet" and recorded the exact pin (line 86).
- verified:
  - `npm run api:types` → `[api:types] wrote ...\apps\web\src\lib\api\types.ts`.
    SHA-256 before/after re-run: `E4867F2E...A0FF19` both times → **identical=True** (idempotent).
  - `API_INTERNAL_URL=http://localhost:9999 npm run api:types` → `[api:types] could not reach the API at
    http://localhost:9999/openapi.json: fetch failed`, exit **1**.
  - deliberate wrong call `health.does_not_exist` → `src/__probe.ts(5,43): error TS2339: Property
    'does_not_exist' does not exist on type '{ status: "ok" | "degraded"; db: "ok" | "down"; }'`, exit **2**.
    Probe deleted → `npm run typecheck` exit **0**.
  - `grep -rn "fetch(" apps/web/src/` (run through the Grep tool — this Windows host has no GNU `grep`) →
    **1 match**: `apps/web/src/lib/api/client.ts:204`. The `scripts/` codegen is outside `src/` and is exempt.
  - `npm run lint` → `✔ No ESLint warnings or errors`.
  - `npm run build` → `✓ Compiled successfully`, `✓ Generating static pages (3/3)`.
  - `docker compose up -d --build web` → web image built, web recreated; it also rebuilt/recreated `api`
    because of the dependency. Final `docker compose ps`: `postly-postgres`, `postly-api`, `postly-web` all
    `Up (healthy)`.
  - `GET http://localhost:3000` → **200**, page shows `ok` / `ok`.
  - Host `next dev` on `:3001` (port 3000 held by Docker) → **200**, `ok` / `ok`.
  - API-down degradation: `docker compose stop api` → `GET http://localhost:3000` still **200** with
    `unreachable` / `unknown`; `docker compose start api` → **200** with `ok` / `ok` again.
- issues:
  - First Docker attempt after the move rendered `unreachable`: the page passed `API_INTERNAL_URL`
    (`http://api:8000`) as the client base without `/api/v1`, so it fetched `/health` → 404. Fixed by
    appending `/api/v1`; verified in Docker afterwards. The base URL is still trusted config only.
  - `grep`/`rg` are not installed on this Windows host; the only-fetch-site check was done with the Grep tool.
- next: manager re-review → accept T-006, release T-010.

## Manager review

### 2026-10-31 · manager s-20261031-1120 (re-review of the rework)

- verdict: **accepted**. The rework closed the blocking item and everything else held up.
- checked (every item re-run by the manager from a clean state, not taken from the report):
  - **The "only fetch call site" claim now holds.** `fetch(` under `apps/web/src/` matches exactly one file:
    `apps/web/src/lib/api/client.ts:204`. The only other call site in the whole app is
    `apps/web/scripts/generate-api-types.ts:31`, which talks to the OpenAPI document, not to the API — the
    exemption the task file allows. `apps/web/lib/` is gone (`Test-Path` → `False`) and no stale reference to
    the old path survives in any file. ✓
  - **The base URL is trusted config, not request headers.** `src/app/page.tsx` imports `env` from `~/env`
    and builds `${env.API_INTERNAL_URL}/api/v1`. `src/env.js` adds
    `API_INTERNAL_URL: z.string().url().default("http://localhost:8000")` to the **server** schema with
    `runtimeEnv: { API_INTERNAL_URL: process.env.API_INTERNAL_URL }`. The `headers()` / `x-forwarded-host`
    code is gone — the blind-SSRF vector flagged in the T-004 review is **closed**. ✓
  - `npm run api:types` → `[api:types] wrote ...\apps\web\src\lib\api\types.ts`; SHA-256 before and after a
    re-run is identical (`E4867F2E40056E8EF08C8557219057B5E313DB5A2FD218FFF805423068A0FF19` both times) →
    idempotent. ✓
  - `API_INTERNAL_URL=http://localhost:9999 npm run api:types` → `could not reach the API at
    http://localhost:9999/openapi.json: fetch failed`, exit **1**. Fails loudly. ✓
  - `npm run typecheck` → exit 0. Deliberate wrong call reproduced independently:
    `src/__probe.ts(6,12): error TS2339: Property 'does_not_exist' does not exist on type
    '{ status: "ok" | "degraded"; db: "ok" | "down"; }'`, exit 2; probe deleted → typecheck exit 0 again. ✓
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run build` → `✓ Compiled successfully`, `/` is
    `ƒ (Dynamic)`. ✓
  - `docker compose up -d --build web` → web image rebuilt and recreated; `db`, `api`, `web` all
    `Up (healthy)`. `GET http://localhost:3000` → **200**, exactly 2 × `text-emerald-400">ok</dd>`, no
    `unreachable`. `GET http://localhost:3000/api/v1/health` → 200 `{"status":"ok","db":"ok"}` (the proxy
    still works for browser-side calls). ✓
  - **Live-call proof** (that the page really goes through the client, not a cached render):
    `docker compose stop api` → `GET http://localhost:3000` still **200** but renders `unreachable` /
    `unknown`; `docker compose start api` → **200** again with `ok` / `ok`. ✓
  - Host `next dev` on `:3001` → **200**, `ok` / `ok`, with `API_INTERNAL_URL` unset (so the
    `http://localhost:8000` default is what works). ✓
  - **Runtime proof of the client** (temporary Next route, since nothing else exercises the error paths):
    `health()` → `{"status":"ok","db":"ok"}`; 404 → `ApiError{status:404}`; unreachable host →
    `ApiError{status:0, code:"network_error"}`; `Authorization: Bearer probe-token` sent when `getToken` is
    supplied and **absent** when it is not; `Accept: application/json` always. Route deleted afterwards. ✓
  - `docker compose exec api ruff check .` → `All checks passed!`; `ruff format --check .` →
    `12 files already formatted`; `python -m pytest -q` → `1 passed`. ✓
  - `openapi.json` still carries `HealthResponse` (enum `status`/`db`) with both the 200 and 503 responses. ✓
  - `docs/API.md` → base URL `/api/v1`, `Authorization: Bearer <token>`, error envelope
    `{ error: { code, message, details } }`; the client matches all three. ✓
  - `docs/research/00-versions.md` §2 → `openapi-typescript | 7.13.0 | ... (installed in T-006)` and it is
    no longer in the "not installed yet" list. ✓
  - `apps/web/README.md` → has a "Regenerate API types" section that states codegen is **host-only** and
    explicitly does not work in the runtime image, plus the "only file under `src/` that may call `fetch`"
    rule for future contributors. ✓
  - No `any` in `src/lib/api/**` or `scripts/**`. Every dependency still pinned exactly (no `^`/`~`).
    `npm audit` → 22 advisories (18 moderate, 4 high), all transitive devDeps — matches the report.
    `src/lib/api/types.ts` is **not** gitignored, so the generated file will be committed. ✓
  - **Bonus check — the base URL is read at runtime, not baked at build time.** The built bundle contains no
    `http://api:8000` literal; `.next/server/app/page.js` carries
    `runtimeEnv:{NODE_ENV:"production",API_INTERNAL_URL:process.env.API_INTERNAL_URL}`. So the compose
    `environment:` override really takes effect and the value can differ per environment. ✓
- notes (no action required, carried forward):
  - `client.ts` still cannot be imported by **plain Node** (extensionless `./client` / `./types` imports fail
    under Node's ESM resolver). Fine inside Next.js; a plain-Node unit test would need explicit `.ts`
    extensions or a loader. There is still no test runner in `apps/web`.
  - The live API returns FastAPI's default `{"detail": ...}` for 404/422, **not** the documented
    `{ error: { code, message } }` envelope, so the client's `internal_error` fallback is what fires today.
    The client matches the *documented* contract (which is what this task asks); the API side needs real
    exception handlers when the first business endpoints land (T-015+).
  - `health.py` declares `response_model=HealthResponse` but returns a raw `JSONResponse`, so FastAPI skips
    response validation — the model is documentation + schema only.
  - `openapi-typescript` adds 17 audit advisories, all in transitive devDependencies of
    `@redocly/openapi-core`. Not force-fixed (that would change pinned versions).
  - The exported singleton `api = createApiClient()` still carries the relative default base, so it is
    unusable from a Server Component. T-011 should either give it an absolute base or stop exporting it.
- next: **T-006 accepted → Q0 is complete.** Release **T-010** (Prisma schema, 19 models, migration, seed
  categories) — it is the next `ready` task with all dependencies done.

## Manager review

### 2026-10-31 · manager s-20261031-1336 (re-verification of an accepted task)

- verdict: **accepted — re-verified independently.** T-006 stays `done`; the board row stays `[x]`.
- why this review exists: the task was already accepted on 2026-10-31 at 11:20. This session re-ran **every**
  `## Done when` check from scratch (no result taken from the earlier report) to confirm the acceptance still
  holds on the current tree.
- checked (every item re-run by the manager):
  - **Done-when #1 — codegen.** `npm run api:types` → `[api:types] wrote
    E:\projects\endev\postly\apps\web\src\lib\api\types.ts`, exit 0. SHA-256 before and after the re-run is
    identical (`E4867F2E40056E8EF08C8557219057B5E313DB5A2FD218FFF805423068A0FF19` both times) → idempotent. ✓
    `API_INTERNAL_URL=http://localhost:9999 npm run api:types` → `[api:types] could not reach the API at
    http://localhost:9999/openapi.json: fetch failed` + the "start the API" hint, exit **1**. Fails loudly. ✓
  - **Done-when #2 — single fetch call site.** `fetch(` under `apps/web/src/` matches **exactly one** file:
    `apps/web/src/lib/api/client.ts:204`. Across the whole app there are two: `client.ts:204` and
    `apps/web/scripts/generate-api-types.ts:31` (the exempt codegen — it talks to the OpenAPI document, not to
    the API). `apps/web/lib/` is gone. ✓
  - **Done-when #3 — typecheck + negative proof.** `npm run typecheck` → exit **0**. Deliberate wrong call
    (temporary `src/__probe.ts`, since deleted):
    `src/__probe.ts(5,22): error TS2339: Property 'does_not_exist' does not exist on type
    '{ status: "ok" | "degraded"; db: "ok" | "down"; }'` and `src/__probe.ts(7,16): error TS2339: Property 'posts'
    does not exist on type 'ApiClient'`, exit **2**. Probe removed → typecheck exit **0** again. ✓
  - **Done-when #4 — build.** `npm run build` → `✓ Compiled successfully`, `/` is `ƒ (Dynamic)`, exit **0**.
    `npm run lint` → `✔ No ESLint warnings or errors`, exit **0**. ✓
  - **Done-when #5 — docs ↔ client.** `docs/API.md` line 3 "Base URL `/api/v1`" ↔ `client.ts:46`
    `DEFAULT_BASE_URL = "/api/v1"`; line 17 `Authorization: Bearer <token>` ↔ `client.ts:187`
    `headers.set("Authorization", \`Bearer ${token}\`)`; line 14 error envelope
    `{ "error": { "code", "message", "details" } }` ↔ `client.ts:17-25` (`ApiErrorPayload` / `ApiErrorEnvelope`)
    and `client.ts:65-91` (`ApiError.fromResponse` + `isApiErrorEnvelope`); line 10 success envelope
    `{ "data", "meta" }` ↔ `client.ts:12-15` (`ApiEnvelope<T>`) and `client.ts:162-176` (`request<T>()` unwraps
    `data`). All three match. ✓
  - **Done-when #6 — placement + trusted base URL.** The client lives at `apps/web/src/lib/api/{client,index,
    types}.ts`; `tsconfig.json:30` maps `~/*` → `./src/*`; `src/app/page.tsx:2` imports `~/lib/api` and
    `page.tsx:11` builds the base from `${env.API_INTERNAL_URL}/api/v1`, where `src/env.js:11,29` declares
    `API_INTERNAL_URL` in the **server** schema. A search of `src/**` for `x-forwarded-host` / `forwarded` /
    `headers()` returns **0 matches** — the blind-SSRF vector is still closed. The base URL is read at runtime,
    not baked: `.next/server/app/page.js` contains **no** `api:8000` literal and carries
    `runtimeEnv:{…,API_INTERNAL_URL:process.env.API_INTERNAL_URL}`. `docs/research/00-versions.md` line 45 →
    `openapi-typescript | 7.13.0`, line 86 records the exact pin and it is **no longer** in the "not installed yet"
    list (lines 82-84). Installed version reads back `7.13.0`; `npm view openapi-typescript dist-tags` →
    `latest: 7.13.0`, `next: 7.0.0-rc.1` → the pin is the current stable, not a prerelease. ✓
  - **Runtime proof — the page really goes through the client.** `GET http://localhost:3000` → **200**, exactly
    **2** × `text-emerald-400">ok</dd>`, no `unreachable`. `GET http://localhost:3000/api/v1/health` → 200
    `{"status":"ok","db":"ok"}` (the browser-side proxy still works). `docker compose stop api` → `GET
    http://localhost:3000` still **200** but renders `unreachable` and **no** `ok`; `docker compose start api` →
    **200** with `ok` / `ok` again. ✓
  - **Runtime proof — client behaviour** (temporary probe route on host `next dev` :3001, deleted afterwards):
    `health()` → `{"status":"ok","db":"ok"}`; 404 → `ApiError{status:404}`; unreachable host →
    `ApiError{status:0, code:"network_error"}`; `Authorization: Bearer probe-token` sent when `getToken` is
    supplied and **absent** when it is not; `Accept: application/json` always; `request()` unwraps the
    `{data,meta}` envelope. ✓
  - Backend: `docker compose exec -T api ruff check .` → `All checks passed!`; `ruff format --check .` →
    `14 files already formatted` (12 in T-006, +2 from T-010's in-flight files); `python -m pytest -q` →
    `2 passed, 1 warning` (the extra test is T-010's). ✓
  - No `any` in `src/lib/api/**` or `scripts/**`. `src/lib/api/types.ts` is **tracked** in git
    (`git ls-files` lists it) and not gitignored. ✓
  - **Cleanup verified.** Probe routes and the probe log deleted, the dev server stopped, port 3001 free, the
    stale `.next/types/validator.ts` (generated for the deleted probe) removed and the build re-run clean.
    `git status --porcelain` is identical to the state before this session — nothing left behind.
- notes (no action required, carried forward):
  - The exported singleton `api = createApiClient()` (`client.ts:241`) still carries the relative default base,
    so it is unusable from a Server Component. T-011 should give it an absolute base or stop exporting it.
  - The live API still returns FastAPI's default `{"detail": …}` for 404/422, so the client's `internal_error`
    fallback fires instead of the documented envelope. The client matches the *documented* contract; the API
    side needs real exception handlers when business endpoints land (T-015+). Not a T-006 defect.
  - `health.py` declares `response_model=HealthResponse` but returns a raw `JSONResponse`, so FastAPI skips
    response validation — the model is documentation + schema only.
  - `openapi-typescript` adds 17 audit advisories, all in transitive devDependencies of `@redocly/openapi-core`.
    Not force-fixed (that would change pinned versions).
- watch item for the **T-010** review (not a T-006 defect): the in-flight T-010 work puts a vendored Prisma
  client under `apps/web/src/generated/prisma/**`. It contains **no** `fetch(` call today, so done-when #2 still
  holds, but it places third-party code inside the "only `client.ts` may call `fetch`" zone. T-010's review
  should decide whether it belongs under `src/` and whether it should be gitignored.
- next: T-006 remains closed. **T-010** is the open item and is already at `review`.
