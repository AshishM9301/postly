# T-025 · Frontend sign-in: pseudonymous session, session restore, sign-out

- status: ready
- quest: Q1
- depends: T-011, T-020
- owner: -
- updated: 2026-11-02 08:50
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

- [ ] The app can create a pseudonymous identity on the device (a client secret is generated and kept
      **only** on the device) and sign in with it.
- [ ] The session survives a reload: the same alias is shown and the token is reused until it is cleared.
- [ ] Sign-out warns what is lost (the alias and the session) and then clears the local identity; the app
      falls back to the ghost identity and says so.
- [ ] The signed-in alias is shown in the header (or the rail) and the rotate-alias action still works.
- [ ] The token is stored where the rest of the app expects it and is **never** written to a URL, a log
      or an error message.
- [ ] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`; `npm run test:ghost` → all pass.
- [ ] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts`.

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

## Report

## Manager review
