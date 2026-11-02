# T-025 · Frontend sign-in: pseudonymous session, session restore, sign-out

- status: done
- quest: Q1
- depends: T-011, T-020
- owner: s-20261102-1039
- updated: 2026-11-02 11:15
- files: apps/web/src/components/**, apps/web/src/lib/**, apps/web/src/app/**

## Goal

The web app is **ghost-only**: there is no sign-in, so every session is anonymous, the *For You* tab
cannot be personalised and nobody can reach their own account screen. This task adds the missing sign-in
surface for the **pseudonymous** identity (alias + client secret, both generated on the device) with a
session that survives a reload, plus a sign-out that warns what is lost.

Google sign-in stays out of scope: it needs Firebase credentials in `.env` (`FIREBASE_ADMIN_CREDENTIALS`),
which this environment does not have. The backend already supports it (`POST /auth/google`) — a later task
adds the button once the credentials exist.

## Done when

- [x] The app can create a pseudonymous identity on the device (a client secret is generated and kept
      **only** on the device) and sign in with it.
- [x] The session survives a reload: the same alias is shown and the token is reused until it is cleared.
- [x] Sign-out warns what is lost (the alias and the session) and then clears the local identity; the app
      falls back to the ghost identity and says so.
- [x] The signed-in alias is shown in the header (or the rail) and the rotate-alias action still works.
- [x] The token is stored where the rest of the app expects it and is **never** written to a URL, a log
      or an error message.
- [x] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`; `npm run test:ghost` → all pass.
- [x] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts`.

## Notes / gotchas

- `POST /auth/pseudo` takes `{ "secret": "32+ chars" }` and returns `{ alias, token, mode }`. Reusing the
  same secret reopens the identity — the secret **is** the account.
- The secret is the credential: it must live in the local vault (IndexedDB), never in `localStorage` in
  clear text, never in the query string. `docs/SECURITY.md` §3 is the rule.
- The token is a bearer token; it goes in the `Authorization` header only. The typed client already
  supports it — check `src/lib/api/client.ts` before adding a second path.
- The API's `mode` is `google` / `pseudonymous` / `ghost`; the UI must show which one is active.
- Sign-out is not "delete": the account and its content live on the server. Deleting is T-024.

## Research notes

- The contract: `docs/API.md` §2. The three identity modes: `docs/SECURITY.md` §1–§2 and `docs/PLAN.md` §2.

## Work log

- 2026-11-02 s-20261102-1039: added pseudonymous sign-in/create/restore/sign-out, vault-backed
  account secret, session-aware API writes and account-alias rotation; lint/typecheck/build and
  ghost tests pass, API sign-in/rotate/reopen smoke passes.

## Report

### 2026-11-02 · worker s-20261102-1039

- changed:
  - `src/lib/ghost/vault.ts` + `index.ts` — account-secret records (`saveAccountSecret`,
    `getAccountSecret`, `deleteAccountSecret`) stored in IndexedDB, separate from ghost post/comment
    keys; one new vault test.
  - `src/lib/session.ts` — `ActiveSession` type for the token/alias/mode store added in T-024.
  - `src/lib/api/client.ts` — the main `api` now carries the bearer token; added tokenless `ghostApi`
    for owner-key operations (`sessionApi` aliases the main client).
  - `src/lib/api/ghost.ts` — ghost post deletion uses `ghostApi`; `src/lib/api/endpoints.ts` — sign-in,
    rotate-alias, tokenless purge and ghost-comment delete, optional media `owner_key`.
  - `src/components/session-provider.tsx` (new) — restores the stored session, validates it with
    `GET /me`, creates/signs in with a generated/stored/pasted secret, rotates the alias through
    `POST /auth/rotate-alias`, and signs out (clears token/alias, keeps the vault secret, resets personal
    queries and says it fell back to ghost).
  - `src/components/sign-in-dialog.tsx` (new), `session-button.tsx` (new) — sign-in/create/restore UI,
    mode display, sign-out warning, inline API errors.
  - `src/components/app-header.tsx` — shows the active session alias (or ghost alias), rotates the
    right identity, and exposes the sign-in/account button on mobile; `rail-footer.tsx` exposes it on
    desktop.
  - `src/components/composer.tsx`, `comment-form.tsx`, `comment-item.tsx`, `comment-thread.tsx`,
    `vote-buttons.tsx`, `account-deletion.tsx` — session-aware posts/comments/votes/deletes; session
    comments are recognised by author id, ghost comments still use their vault key; account deletion now
    removes the vault secret and refreshes the provider state.
- verified (real output):
  - `npm run lint` → `✔ No ESLint warnings or errors`.
  - `npm run typecheck` → exit 0, no output.
  - `npm run build` → `✓ Compiled successfully`; `/` 23.9 kB, 228 kB First Load JS.
  - `npm run test:ghost` → `tests 19`, `pass 19`, `fail 0`.
  - `Select-String ... '\bfetch\('` → only `src/lib/api/client.ts:159`.
  - API smoke **through the Next proxy**: `POST /auth/pseudo` → **200 pseudonymous**, `GET /me` →
    alias matches, `POST /auth/rotate-alias` → **200**, `GET /me` → new alias, `POST /auth/pseudo` with
    the same secret → **200 same alias** (reopen), `GET /me` → pseudonymous, cleanup `DELETE /me` →
    **204**.
  - Rebuilt/recreated `postly-web`; healthy, `/` returns 200 and the SSR HTML contains `Sign in`.
- issues / notes:
  - Sign-in/session restore is implemented via the `postly.session.token`/`alias`/`mode` keys and the
    vault secret; there is still no browser automation for a real reload/sign-out click-through.
  - Sign-out keeps the account secret in the vault (the warning says the alias and session are lost, not
    the secret) so the same device can sign back in. Deleting the account removes the secret.
  - The secret is **not yet included in the vault JSON export/import**; that belongs with T-041's key
    export work.
  - Google sign-in remains out of scope (Firebase credentials are absent).
  - The main transport is now session-aware, so signed-in feeds are personalised and writes are
    attributed to the account. Ghost owner-key operations deliberately use the tokenless `ghostApi`.
  - T-026 may move the sign-in/account control with the other rail controls.
- next: manager verification; T-026 is the last shell placement task.

## Manager review

### 2026-11-02 · manager s-20261102-1110

- verdict: **accepted**. The sign-in is real, the secret never leaves the device except to the two calls
  that need it, and — the part I checked hardest — the ghost paths still behave when a session exists.
- checked (re-run by me; nothing taken from the worker's report):
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
    `✓ Compiled successfully` (`/` 23.9 kB, 228 kB First Load JS); `npm run test:ghost` → **19 pass**,
    0 fail (the new vault case included).
  - **The single-fetch-door invariant holds**: the only real `fetch(` under `apps/web/src/` is
    `src/lib/api/client.ts:159`.
  - **The live sign-in flow through the Next proxy, driven by me**:
    - `POST /auth/pseudo` with a 43-char secret → **200** `{alias, token, mode: pseudonymous}`;
    - the **same secret** again → **200** with the **same alias** (the identity reopens) ✓;
    - `GET /me` → the alias matches, the mode is `pseudonymous`, a `user_id` comes back ✓;
    - `POST /auth/rotate-alias` → **200**, and `GET /me` then shows the **new** alias ✓;
    - a **short** secret → **422 `validation_error`** (the UI refuses it client-side too) ✓;
    - a **bogus token** → **401 `unauthorized`** — the provider clears the session and says the app fell
      back to ghost ✓;
    - `DELETE /me` with the secret → **204** ✓.
  - **The session write paths** (the riskiest part of making the main transport session-aware), driven by
    me:
    - `POST /posts` with the token and **no** `owner_key` → **201**, `author` = the account ✓;
    - `POST /media` with the token and **no** `owner_key` field → **201** — the ownership gate passes on
      the session alone ✓;
    - `DELETE /posts/{id}` with the token and **no body** → **204**, the post is then **404** ✓;
    - a **ghost** comment by the same device (its own `owner_key`, **no** token) → **201** with
      `author: null`, and the ghost delete with that `owner_key` → **204** ✓ — the two identities do not
      collide.
  - **Code read** (the privacy-critical part):
    - `lib/session.ts` holds only the opaque bearer token, the alias and the mode; the **pseudonymous
      secret is not in `localStorage`** — it goes into the **IndexedDB vault** under its own `account`
      record, never mixed with the post/comment keys ✓;
    - the vault **export** includes only the `post` records → the account secret does **not** leak into a
      downloaded JSON file ✓, and `resetVault()` drops the whole database, the secret included ✓;
    - the **main transport now carries the token**, and every ghost owner-key call uses the new
      tokenless `ghostApi` (the post delete, the comment delete, the ghost purge) — a ghost operation can
      never be attributed to the account ✓;
    - the composer, the comment form and the vote buttons **branch on the session**: signed in → no alias
      and no `owner_key` (the account owns it); signed out → the per-item vault key, exactly as before ✓.
      `uploadMedia` omits the `owner_key` form field when there is none ✓;
    - the account deletion now also deletes the vault secret ✓;
    - the sign-out warning says exactly what is lost (the token and the alias) and what is kept (the secret
      in the vault), and the app falls back to ghost ✓.
  - **The live app**: `docker compose build web` (every layer cached → the running image already contains
    this tree) and `GET http://localhost:3000/` → **200, 36,533 bytes**, with `Sign in` in the SSR HTML ✓.
- notes (carried forward):
  - **The secret is still not in the vault export/import** — that is T-041's key-export work; until then
    an exported vault does not carry the account secret.
  - **Google sign-in is still out of scope** (no Firebase credentials in this environment).
  - The session is a bearer token in `localStorage`: standard, but a token in `localStorage` is readable
    by any script on the page. The real credential (the secret) is in IndexedDB ✓.
  - The vote buttons send `voter_key: null` when signed in, so the server keys the vote to `u:<userId>`;
  - the remembered "my vote" is still `localStorage`-only until `GET /me/votes` exists.
  - **No browser automation**: the sign-in dialog was not clicked through here, so the *visual* result is
    unproven. The calls behind it are verified.
  - **My own mistake, logged**: my first media check used a hand-written base64 PNG that Pillow rejected
    (`invalid_image`) — my blob, not the app; the retry with a real PNG returned 201.
- environment left clean: 0 posts, 0 comments, 0 media rows, 0 files in the media volume, 1 pre-existing
  user + session and 1 pre-existing orphan vote.
- next: **T-026** (the shell placement refinement) is the last frontend screen; **T-027** and the
  "simple post" line (T-028 → T-029 → T-038) follow.
