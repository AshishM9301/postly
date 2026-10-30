# T-006 · OpenAPI → TypeScript types + typed fetch client

- status: ready
- quest: Q0
- depends: T-003, T-004
- owner: -
- updated: -
- files: apps/web/package.json, apps/web/lib/api/types.ts, apps/web/lib/api/client.ts, apps/web/lib/api/index.ts, apps/web/scripts/generate-api-types.ts, apps/web/.gitignore

## Goal

Give the frontend a single typed door to the API. The FastAPI app publishes an OpenAPI spec; a script turns
that spec into TypeScript types; a thin client wraps `fetch` with those types, one method per endpoint
group, one place for the base URL and the auth header. No tRPC — this replaces it.

## Done when

- [ ] `npm run api:types` regenerates `apps/web/lib/api/types.ts` from the running API's OpenAPI spec and
      fails loudly if the API is not reachable.
- [ ] `apps/web/lib/api/client.ts` exposes typed methods (`health()`, later `posts.list()`, `votes.cast()`…)
      and is the **only** place that calls `fetch`.
- [ ] `npm run typecheck` passes, and a deliberately wrong call to a typed method fails to compile (prove it
      once, then revert).
- [ ] `npm run build` passes.
- [ ] `docs/API.md` lists the base URL, the auth header and the error envelope — and the client matches it.

## Notes / gotchas

- Use `openapi-typescript` (pin an exact stable version). The generated file is committed; the script is
  re-runnable.
- The spec source is `http://api:8000/openapi.json` inside Docker, `http://localhost:8000/openapi.json` on
  the host. Make it configurable through the same env var the app uses.
- The client must handle the envelope: `{ data, meta }` on success, `{ error: { code, message } }` on
  failure. One error type, thrown as a typed `ApiError`.
- The auth header is `Authorization: Bearer <token>`. The token source is decided in T-011 — for now the
  client accepts an optional token getter function so it does not need rewriting later.
- Do not add `any` anywhere. If a type is missing, fix the API model, not the type assertion.
- Keep the client framework-agnostic (no React hooks inside it) so a future mobile client can copy the shape.

## Research notes

The endpoint contract this task codes against: `docs/API.md`. Versions: `docs/research/00-versions.md` §2.

If the OpenAPI generator has trouble with FastAPI's schema (multipart endpoints, unions), record the
workaround here — later tasks hit the same thing.

## Work log

## Report

## Manager review
