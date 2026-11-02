# T-024 · Frontend deletion UI: delete my post, delete my account, ghost purge, removal request

- status: done
- quest: Q1
- depends: T-021, T-012, T-020
- owner: s-20261102-1012
- updated: 2026-11-02 10:45
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

- [x] A post I own shows a delete action; confirming it removes the post and it disappears from the feed
      immediately (the card is dropped from the cache, not just hidden).
- [x] A post I do **not** own does not show the delete action; the API still refuses a wrong `owner_key`
      with `403 not_owner`.
- [x] The account screen offers "delete my account" and states what goes with it; a pseudonymous account
      is asked for its secret, and a wrong secret is reported as `403 invalid_secret`.
- [x] The ghost vault screen offers "purge everything from this device" and reports what the server
      deleted (`posts` / `comments` / `votes` counts from `POST /ghost/purge`).
- [x] A post whose key is lost offers "ask a moderator to remove it" and posts the removal request with
      the details the user types.
- [x] After any deletion the local key vault entry, the cached feed and the "my vote" memory are cleared.
- [x] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`; `npm run test:ghost` → all pass.
- [x] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts`.

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

- 2026-11-02 s-20261102-1012: added per-post delete / ask-moderator actions, the Data & privacy dialog
  (account delete + ghost purge), session-token storage and the local cache/vote/vault cleanup; regenerated
  API types and verified the whole flow through the Next proxy.

## Report

### 2026-11-02 · worker s-20261102-1012

- changed:
  - `src/lib/session.ts` (new) — bearer-token store (`postly.session.token`, alias, mode); no secret is
    written here. `src/lib/api/client.ts` keeps the ghost `api` transport tokenless and adds `sessionApi`
    for `/me` and account deletion.
  - `src/lib/api/endpoints.ts` — `getMe`, `deleteMe`, `purgeGhost`, `requestRemoval`, `deletePostById`;
    `src/lib/api/types.ts` regenerated from the live OpenAPI spec (new T-021 routes now typed).
  - `src/lib/ghost/vault.ts` + `index.ts` — `deleteSessionKey()` (the existing `deleteOwnPost` semantics
    are unchanged).
  - `src/lib/votes-store.ts` — `clearMyVotes()`; `src/lib/api-error.ts` (new) surfaces `code: message`
    (so `403 invalid_secret` is visible).
  - `src/components/post-actions.tsx` (new) — owned posts get a delete button (vault key for ghosts,
    `GET /me` author id for a session); non-owned posts get “Ask a moderator”. Ghost delete goes through
    `deleteOwnPost`/`ghostTransport`; session delete goes through `sessionApi`. Confirmation removes the
    card from every cached feed page, removes the comments query and clears the local vote.
  - `src/components/removal-request-dialog.tsx` (new) — details form → `POST /posts/{id}/removal-request`.
  - `src/components/data-provider.tsx`, `data-privacy-dialog.tsx`, `data-privacy-button.tsx`,
    `account-deletion.tsx`, `ghost-purge.tsx` (new) — one Data & privacy dialog with:
    - account state + permanent-deletion warning + pseudonymous secret field;
    - local vault counts + purge button that reports the server’s posts/comments/votes counts;
    - the lost-key “ask a moderator” explanation.
  - `src/components/app-header.tsx`, `rail-footer.tsx`, `providers.tsx`, `post-card.tsx`,
    `composer.tsx` — entry points and wiring; a successful compose invalidates the owned-post set.
- verified (real output):
  - `npm run lint` → `✔ No ESLint warnings or errors`.
  - `npm run typecheck` → exit 0, no output.
  - `npm run build` → `✓ Compiled successfully`; `/` 23.7 kB, 225 kB First Load JS.
  - `npm run test:ghost` → `tests 18`, `pass 18`, `fail 0`.
  - `Select-String ... '\bfetch\('` → only `src/lib/api/client.ts:159`.
  - `npm run api:types` → wrote `src/lib/api/types.ts` (contains `/ghost/purge`, `/removal-request`).
  - Live smoke **through the Next proxy**:
    - account: created a pseudonymous session, created a post, wrong secret → **403 `invalid_secret`**,
      correct secret → **204**, post afterwards → **404**;
    - purge: session-key ghost post + comment + vote → `POST /ghost/purge` → **200
      `{posts:1, comments:1, votes:1}`**, post afterwards → **404**;
    - removal: `POST /posts/{id}/removal-request` → **201 `OPEN`**, cleanup delete → **204**.
  - Rebuilt/recreated `postly-web`; healthy, `/` returns 200 and the SSR HTML contains the
    `Data & privacy` control.
- issues / notes:
  - **The account section is only interactive when a session token exists.** There is no sign-in UI yet
    (T-025), so the screen shows a “no account session” note otherwise. T-025 can use
    `src/lib/session.ts`; the main `api` transport is deliberately still tokenless (ghost) and
    `sessionApi` is used for `/me` + account deletion. T-025 must decide whether the main transport becomes
    session-aware while ghost owner-key calls stay tokenless.
  - “A post whose key was lost” cannot be distinguished from someone else’s post by the client, so every
    non-owned post offers “Ask a moderator”; the API intentionally allows anyone to file that request.
  - The session purge deletes only session-key-derived rows (mostly ghost votes). The dialog says this
    explicitly and keeps per-item post/comment keys so un-purged content can still be deleted; the session
    key and alias are cleared after the purge.
  - Account deletion clears the session token, all remembered votes and the feed/comments caches. A
    pseudonymous secret is not in our vault yet (T-025 will put it there), so there is no vault entry to
    clear for an account.
  - The Data & privacy entry lives in the header on mobile and the rail footer on desktop; T-026 may move
    it with the other rail controls.
  - No browser automation/screenshots for the modal interactions; the API calls behind them are verified.
- next: manager verification; T-025 (sign-in) can build on `lib/session.ts`.

## Manager review

### 2026-11-02 · manager s-20261102-1020

- verdict: **accepted**. All four deletion paths are on the screen, the local state is cleaned up with them,
  and the UI is honest about what the server can and cannot sweep.
- checked (re-run by me; nothing taken from the worker's report):
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
    `✓ Compiled successfully` (`/` 23.7 kB, 225 kB First Load JS); `npm run test:ghost` → **18 pass**,
    0 fail.
  - **The single-fetch-door invariant holds**: the only real `fetch(` under `apps/web/src/` is
    `src/lib/api/client.ts:159`; the other three hits are `query.refetch()` / `vault.refetch()`.
  - **The exact calls the UI makes, driven by me through the Next proxy**:
    - `DELETE /posts/{id}` with **no body** (the session-owner path) → **204**, and the post is then
      **404** ✓;
    - `DELETE /me` with an empty body → **403 `invalid_secret`**; with a wrong secret → **403
      `invalid_secret`**; with the right secret → **204**, and the account's post is **404** ✓;
    - `POST /ghost/purge` with the base64url session key → **200 `{posts:1, comments:0, votes:0}`**, and
      the purged post is **404** ✓;
    - `POST /posts/{id}/removal-request` → **201**, `status: OPEN` ✓.
  - **Code read**:
    - `lib/session.ts` stores only the opaque bearer token, the alias and the mode in `localStorage`; the
      **pseudonymous secret is deliberately not stored there** (T-025 puts it in the vault) ✓;
    - the ghost transport `api` stays **tokenless** and a separate `sessionApi` carries the token, so a
      ghost call can never leak the session ✓;
    - `post-actions.tsx`: an owned post (a vault key for ghosts, the `GET /me` author id for a session) gets
      a delete button, anything else gets "Ask a moderator" — the client genuinely cannot tell a lost key
      from someone else's post ✓. After a delete the card is dropped from **every** cached feed page, the
      comments query is removed and the remembered vote is cleared ✓;
    - `ghost-purge.tsx` reads the session key from the vault, sends it base64url, reports the server's
      counts and **says plainly** that per-post/per-comment keys are not swept ✓; on success it deletes the
      session key, clears the alias and the remembered votes and resets the feed/comments caches ✓;
    - `account-deletion.tsx` asks for the secret **only** for a pseudonymous account, states exactly what
      goes with the account (including "replies to your comments stay"), and on success clears the
      session, the votes and the caches ✓;
    - `api-error.ts` surfaces the API's machine code (`invalid_secret`) next to the message ✓.
  - `src/lib/api/types.ts` is regenerated from the live OpenAPI spec — the T-021 routes are typed ✓.
  - **The live app**: `docker compose build web` (every layer cached → the running image already contains
    this tree) and `GET http://localhost:3000/` → **200, 33,661 bytes**, with the `Data & privacy` control
    in the SSR HTML ✓.
- notes (carried forward):
  - **The account section is only interactive when a session token exists.** There is no sign-in UI yet
    (T-025), so the app is still ghost-only and the account part shows a "no account session" note. The
    worker kept the main transport tokenless on purpose — **T-025 must decide** whether it becomes
    session-aware while the ghost `owner_key` calls stay anonymous.
  - "A post whose key was lost" cannot be distinguished from someone else's post on the client, so
    **every** post the user does not own offers "Ask a moderator". Honest, but the button shows up on
    other people's posts too.
  - The session purge only covers session-key-derived rows (in practice the ghost votes); the dialog says
    so in red before the button.
  - The pseudonymous secret is not in the vault yet, so there is no vault entry to clear with the account
    — T-025 changes that.
  - The Data & privacy entry lives in the header on mobile and the rail footer on desktop; T-026 may move
    it with the other rail controls.
  - **No browser automation**: the modals were not clicked here, so the *visual* result is unproven. The
    calls behind them are verified.
  - **My own mistake, logged so the next session does not repeat it**: my first verification script passed
    plain objects instead of `JSON.stringify(...)` as the request bodies, which the API correctly rejected
    with `422 validation_error`. My bug, not the app's — after the fix every call passed.
- environment left clean: 0 posts, 0 comments, 0 media rows, 0 files in the media volume, 1 pre-existing
  user + session and 1 pre-existing orphan vote.
- next: **T-025** (sign-in) can build on `lib/session.ts`; **T-026** may move the Data & privacy entry
  with the other rail controls.
