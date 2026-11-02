# T-024 · Frontend deletion UI: delete my post, delete my account, ghost purge, removal request

- status: ready
- quest: Q1
- depends: T-021, T-012, T-020
- owner: -
- updated: 2026-11-02 08:50
- files: apps/web/src/components/**, apps/web/src/lib/**, apps/web/src/app/**

## Goal

T-021 made deletion real on the server; **the app still cannot delete anything**. This task puts the four
deletion paths in front of the person who needs them, with the warnings the privacy promise needs:

1. **Delete my post** — on a post I own (session or ghost `owner_key`).
2. **Delete my account** — for a signed-in pseudonymous account the client secret is required; the screen
   must warn that this is permanent and that the posts, comments and votes go with it.
3. **Purge my ghost session** — wipe everything made with this browser's session key, with a confirmation
   that spells out what is deleted.
4. **Request removal** — for content whose key was lost: a form that asks for the details a moderator needs.

Every path must also clear the **local** state: the key vault entry, the cached feed and the "my vote"
memory, so a deleted post cannot come back from a cache.

## Done when

- [ ] A post I own shows a delete action; confirming it removes the post and it disappears from the feed
      immediately (the card is dropped from the cache, not just hidden).
- [ ] A post I do **not** own does not show the delete action; the API still refuses a wrong `owner_key`
      with `403 not_owner`.
- [ ] The account screen offers "delete my account" and states what goes with it; a pseudonymous account
      is asked for its secret, and a wrong secret is reported as `403 invalid_secret`.
- [ ] The ghost vault screen offers "purge everything from this device" and reports what the server
      deleted (`posts` / `comments` / `votes` counts from `POST /ghost/purge`).
- [ ] A post whose key is lost offers "ask a moderator to remove it" and posts the removal request with
      the details the user types.
- [ ] After any deletion the local key vault entry, the cached feed and the "my vote" memory are cleared.
- [ ] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`; `npm run test:ghost` → all pass.
- [ ] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts`.

## Notes / gotchas

- The vault already has `deleteOwnPost` (T-012) and an export/import; extend it rather than writing a
  second implementation. The vault keeps the secret when the delete call fails — keep that behaviour.
- `DELETE /posts/{id}` for a ghost takes `{ "owner_key": "…" }` in the **body**; the Next rewrite proxy
  forwards DELETE bodies (T-020 proved it).
- `POST /ghost/purge` takes `{ "session_key": "base64url(32-byte session secret)" }` — the **raw secret**,
  base64url encoded, not the ASCII of an owner key.
- Per-post ghost keys are **not** swept by the session purge; the post's own `owner_key` is the only way to
  delete it. Say so in the UI.
- `GET /me/votes` still does not exist, so "my votes" stays in `localStorage` (T-020).
- The web app has **no sign-in UI** yet, so the account screen can only be reached in a pseudonymous
  session — T-025 may land first and change this.

## Research notes

- The contract: `docs/API.md` §2 (`DELETE /me`, `POST /ghost/purge`) and §4 (`DELETE /posts/{id}`,
  `POST /posts/{id}/removal-request`). The deletion matrix: `docs/SECURITY.md` §4.

## Work log

## Report

## Manager review
