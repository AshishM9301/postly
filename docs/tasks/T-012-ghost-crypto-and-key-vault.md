# T-012 · Ghost crypto helpers + local key vault + export/import

- status: done
- quest: Q1
- depends: T-004
- owner: s-20261101-0810
- updated: 2026-11-01 08:13
- files: apps/web/src/lib/ghost/crypto.ts, apps/web/src/lib/ghost/vault.ts, apps/web/src/lib/ghost/alias.ts, apps/web/src/lib/ghost/index.ts, apps/web/src/lib/api/ghost.ts, apps/web/src/lib/api/client.ts, apps/web/src/lib/ghost/__tests__/crypto.test.ts, apps/web/src/lib/ghost/__tests__/vault.test.ts, apps/web/src/lib/ghost/__tests__/alias.test.ts, apps/web/package.json, apps/web/package-lock.json, apps/web/tsconfig.json, apps/web/eslint.config.js

## Goal

Build the client half of the anonymity design: the crypto helpers, the local key vault and the alias
generator. The browser is the only place the ghost secret ever exists. It must be correct, tested and
portable — a Kotlin or Swift client must be able to produce the same HMACs later.

## Done when

- [x] `deriveOwnerKey(secret, targetId)` returns a base64url `HMAC-SHA256(secret, targetId)` using WebCrypto
      (`crypto.subtle.importKey` + `crypto.subtle.sign`), and the test vectors match a known-good
      implementation (verify with a one-line Node script using `node:crypto`).
- [x] The secret is generated with `crypto.getRandomValues` (32 bytes) — never `Math.random`.
- [x] The vault stores secrets in IndexedDB (`postKey` per post id, `sessionKey` for votes/comments), survives
      a page reload, and can be exported to a JSON file and imported back.
- [x] `listOwnPosts()` returns the ids the user can still delete, and `deleteOwnPost(id)` computes the
      `owner_key` locally and calls the API.
- [x] `rotateAlias()` produces a new alias and stores it for the session; the previous alias stays on older
      posts.
- [x] Unit tests pass (`npm run test` if the scaffold has a runner, otherwise a `npm run test:ghost` script
      using node:test) and cover: determinism, different ids → different keys, export→import round trip,
      missing secret handling.
- [x] `npm run lint`, `npm run typecheck`, `npm run build` pass.
- [x] **Rework item (added by the manager, 2026-10-31):** the ghost vault must **not** call `fetch` itself.
      `apps/web/src/lib/api/client.ts` is the only file under `src/` allowed to call `fetch` (T-006's
      done-when, restated in `AGENTS.md` §11), and `vault.ts` currently breaks that invariant. The delete
      must go through the typed client, and the invariant must be made machine-enforced (an ESLint rule),
      not just remembered. See the manager review.

## Notes / gotchas

- **Base64url, not base64** — the values travel in JSON and must be URL-safe.
- The HMAC **key** is the secret and the **message** is the target id. Getting this backwards produces keys
  that the server cannot verify. Write the test vector down.
- The secret must never be sent to the server. The only thing that leaves the browser is
  `HMAC(secret, targetId)`.
- The vault holds secrets for posts the user may want to delete later. Warn the user before logout that
  clearing site data loses the ability to delete those posts (the logout warning UI is T-041, but the vault
  must expose the count of deletable posts now).
- Never put a secret in `localStorage` under a guessable key without understanding the exposure; IndexedDB
  is the same origin, so the real protection is "the server never sees it", not local encryption. Say so
  honestly in the docs rather than pretending.
- Keep the crypto module framework-agnostic (plain TS, no React) so it can be copied into a mobile client.

## Research notes

The scheme this implements: `docs/SECURITY.md` §2 and the HMAC worked example. The API contract:
`docs/API.md` §2.

- **Encoding:** RFC 4648 §5 base64url (`A-Za-z0-9-_`), **no `=` padding**. `crypto.ts` exposes
  `toBase64Url` / `fromBase64Url`; the vault stores every secret and the operator sends every `owner_key`
  in this form.
- **Recorded test vector** (independent `node:crypto` result, also asserted in `crypto.test.ts`):
  - secret = bytes `00 01 02 … 1f` (32 bytes); base64url `AAECAwQFBgcICQoLDA0ODxAREhMUFRYXGBkaGxwdHh8`
  - target id = `post-123`
  - `HMAC-SHA256(secret, "post-123")` base64url = `BaCamp9SDkGtI1yYKz_76ElI3Kq2QXghpcnxz0UACEI`
  - same digest hex = `05a09a9a9f520e41ad235c982b3ffbe84948dcaab6417821a5c9f1cf45000842`
  - second vector: uuid `3f2c1a4e-0000-4000-8000-123456789abc` →
    `KuKeZcKXwA4w5U3TZBDV_Mk8SK4U-pemWTvt9MQsR_c`
- **HMAC direction:** secret is the key, `targetId` is the message. `deriveOwnerKey` imports the key with
  `crypto.subtle.importKey("raw", bytes, {name:"HMAC",hash:"SHA-256"}, false, ["sign"])` then
  `crypto.subtle.sign("HMAC", key, UTF-8(targetId))`.
- **Node 24 runs `.ts` tests natively** (type stripping). ESM resolution still needs explicit extensions,
  so the ghost modules import each other as `./crypto.ts` etc. and `tsconfig.json` sets
  `allowImportingTsExtensions: true` (legal because `noEmit` is already true).
- `fake-indexeddb@6.2.7` (pinned devDependency) supplies `indexedDB` for the vault tests. The vault has no
  IndexedDB access at import time, so SSR importing the module is safe.
- **Storage is not encryption.** IndexedDB is same-origin storage; the guarantee is that the secret never
  leaves the browser (except as `owner_key`), not that a local attacker cannot read it.

## Work log

- 2026-10-31 s-20261031-1551: implemented ghost crypto, alias store, IndexedDB vault, export/import and
  delete-by-owner-key; 16 node:test cases pass; lint/typecheck/build pass.
- 2026-11-01 s-20261101-0810: rework — removed the vault's raw `fetch` (injected transport + typed-client
  wiring in `src/lib/api/ghost.ts`), added `ApiClient.requestVoid`, enforced the single-fetch-door rule in
  ESLint, removed alias modulo bias, wrapped base64url decode errors; 17 cases pass.

## Report

### 2026-11-01 · worker s-20261101-0810 (rework)

- changed:
  - `apps/web/src/lib/ghost/vault.ts` — **zero `fetch` calls**. `deleteOwnPost` now requires an injected
    `GhostDeleteTransport(postId, ownerKey)`; it derives the owner key, calls the transport, and removes the
    local key only on success. Replaced `GhostFetch`/`baseUrl`/`fetchImpl` with the transport type. Added
    `decodeStoredKey()` so malformed base64url surfaces as `GhostVaultError("invalid_vault")` from imports
    and reads.
  - `apps/web/src/lib/api/client.ts` — added `FetchLike`, an optional `fetchImpl` seam, and
    `requestVoid(path, options)` for body-carrying requests with no response body (a 204 DELETE). `fetch` is
    still called only here.
  - `apps/web/src/lib/api/ghost.ts` (new) — `createGhostTransport(client)` binds the vault to the typed
    client (`DELETE /posts/{id}`, body `{ owner_key }`); `ghostTransport` is the default wiring on the
    singleton `api`.
  - `apps/web/eslint.config.js` — machine-enforced invariant: `no-restricted-syntax` on
    `CallExpression[callee.name="fetch"]` for `src/**/*.{ts,tsx}` with `src/lib/api/client.ts` ignored.
  - `apps/web/src/lib/ghost/alias.ts` — rejection sampling (`ALIAS_UNBIASED_LIMIT = 248`) removes the
    `256 % 31` modulo bias; every character is now equally likely, matching the backend's `secrets.choice`.
  - `apps/web/src/lib/ghost/index.ts` — exports `GhostDeleteTransport` and `ALIAS_UNBIASED_LIMIT`.
  - Tests: `vault.test.ts` now drives the real `createGhostTransport(new ApiClient({ fetchImpl }))`, so it
    still proves the `DELETE /api/v1/posts/{id}` request, the locally derived `owner_key` in the body, and
    success-only key removal (500 keeps the secret); `alias.test.ts` pins the unbiased limit (17 cases).
- verified:
  - `npm run test:ghost` → `tests 17`, `suites 3`, `pass 17`, `fail 0`.
  - `npm run lint` → `✔ No ESLint warnings or errors`.
  - `npm run typecheck` → exit 0 (no output).
  - `npm run build` → `✓ Compiled successfully in 1204ms`; `/` and `/_not-found` generated.
  - `grep -rn "fetch(" apps/web/src/` (via the Grep tool) → **one** match:
    `apps/web/src/lib/api/client.ts:158: this.fetchImpl = options.fetchImpl ?? ((input, init) => fetch(input, init));`
  - ESLint rule proof: a temporary `src/__fetch_probe.ts` calling `fetch(...)` →
    `error Call fetch only from src/lib/api/client.ts — use the typed API client instead  no-restricted-syntax`,
    exit 1; probe deleted afterwards.
- issues / notes:
  - `docs/API.md` still does not specify the DELETE `owner_key` transport; the wiring uses a JSON body. Carried
    forward to T-015/T-021 (as the manager already noted).
  - The default `ghostTransport` exists but nothing imports `src/lib/ghost` into the app yet.
  - No new runtime dependencies were added; no version pins changed.
- next: T-013 (Delhi area seed) is independent and still unblocked.

### 2026-10-31 · worker s-20261031-1551

- changed:
  - `apps/web/src/lib/ghost/crypto.ts` — `generateSecret` (CSPRNG, 32 bytes), base64url codec,
    `deriveOwnerKey` via WebCrypto HMAC-SHA256.
  - `apps/web/src/lib/ghost/alias.ts` — `generateAlias` (CSPRNG, non-ambiguous alphabet),
    `ensureSessionAlias` / `rotateAlias` / `getSessionAlias` / `setSessionAlias` / `clearSessionAlias`
    backed by `sessionStorage`; no React, no DOM assumptions beyond storage guards.
  - `apps/web/src/lib/ghost/vault.ts` — IndexedDB (`postly-ghost` → `keys`) with `sessionKey` and
    `post:<id>` records; save/get/delete, `listOwnPosts`, `countOwnPosts`, JSON export/import,
    `deleteOwnPost` (recomputes `owner_key`, `DELETE /api/v1/posts/{id}`, key removed only on success),
    `resetVault` / `closeVault`, typed `GhostVaultError` (`missing_secret`, `invalid_vault`,
    `delete_failed`, `indexeddb_unavailable`, `browser_only`).
  - `apps/web/src/lib/ghost/index.ts` — public barrel.
  - Tests: `__tests__/crypto.test.ts`, `__tests__/vault.test.ts`, `__tests__/alias.test.ts`
    (16 cases, `node:test`).
  - `apps/web/package.json` + `package-lock.json` — `test:ghost` script, pinned `fake-indexeddb@6.2.7`.
  - `apps/web/tsconfig.json` — `allowImportingTsExtensions` so Node can run the `.ts` tests.
  - `apps/web/eslint.config.js` — disable `no-floating-promises` for `__tests__` only (node:test registers
    `describe`/`it`; they are intentionally not awaited).
- verified:
  - `npm run test:ghost` → `tests 16`, `pass 16`, `fail 0` (3 suites).
  - `npm run lint` → `✔ No ESLint warnings or errors`.
  - `npm run typecheck` → no output (success).
  - `npm run build` → `✓ Compiled successfully`, routes `/` and `/_not-found` generated.
- issues / notes:
  - The task's `files:` paths said `apps/web/lib/ghost/…`; the scaffold (T-004) puts library code under
    `apps/web/src/lib/`. I implemented in `src/lib/ghost/` and updated the `files:` list rather than
    creating a second, non-idiomatic tree.
  - `deleteOwnPost` sends `DELETE /posts/{id}` with JSON `{ "owner_key": … }`. `docs/API.md` only shows
    `owner_key` in the create body; the DELETE transport is not specified there. T-015 should implement the
    same reading (or the contract should be tightened).
  - Alias generation is client-side; collision retry against the DB remains a server concern (T-015), and a
    client-chosen alias can still impersonate an official (manager's T-011 note for T-037).
  - `expiry_days` / logout warning UI are out of scope here (T-040 / T-041); the vault exposes
    `countOwnPosts()` for that warning now.
- next: T-013 (Delhi area seed) is unblocked; T-015 consumed both T-011 and T-014.

## Manager review

### 2026-10-31 · manager s-20261031-1640

- verdict: **rework**. The crypto is exactly right — I verified the HMAC independently — but the vault
  breaks a standing project invariant: it is now the second file under `src/` that calls `fetch`.
- checked (re-run by the manager; nothing taken from the report):
  - **The HMAC is correct, and I proved it myself.** With my own `node:crypto` script:
    `HMAC-SHA256(key = bytes 00..1f, msg = "post-123")` → `BaCamp9SDkGtI1yYKz_76ElI3Kq2QXghpcnxz0UACEI`
    (hex `05a09a9a9f520e41ad235c982b3ffbe84948dcaab6417821a5c9f1cf45000842`) — identical to the recorded
    vector and to the test's expectation; the uuid vector `KuKeZcKXwA4w5U3TZBDV_Mk8SK4U-pemWTvt9MQsR_c`
    matches too. I also computed the two **wrong** variants: the reversed key/message
    (`DdEyTvbh0yKAy6wapJD-cT1INsnEljUD5zyx3zGzE5M`) and the key-as-base64url-**string**
    (`-Yy1EmPuBt6unoMDpmS6sX3jdzUoA8f2F8cLOVSSh_k`) — both differ, so the test pins the HMAC direction
    (secret = key, target id = message) **and** that the key is the raw 32 bytes, not the encoded string.
    That is the interop detail a Kotlin/Swift client will need.
  - **CSPRNG only.** `generateSecret` uses `crypto.getRandomValues(new Uint8Array(32))`; the alias uses
    `crypto.getRandomValues`; no `Math.random` anywhere in the module.
  - **Vault behaviour.** `npm run test:ghost` → **tests 16, pass 16, fail 0** (3 suites). The tests cover
    persistence across a closed/reopened IndexedDB connection (the reload case), export → `resetVault` →
    import round trip, malformed/unsupported export rejection, missing secret → `GhostVaultError
    ("missing_secret")`, and the delete path: the `owner_key` in the request body **equals the locally
    derived key**, and the local key is removed **only** when the API answers 2xx (a 500 keeps the secret).
  - **The secret never leaves the browser.** `deleteOwnPost` sends `{"owner_key": …}` — the derived key, not
    the secret; the vault's only other "export" is a local JSON download.
  - **SSR-safe and not bundled.** Importing `src/lib/ghost/index.ts` in plain Node (no
    `fake-indexeddb`) works — 30 exports, `generateAlias()` and `deriveOwnerKey()` run — so there is no
    import-time IndexedDB access. A search of `.next/static/chunks/*.js` finds **no** trace of the ghost
    code: nothing imports it yet, so it is not in the client bundle.
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
    `✓ Compiled successfully`, `/` still `ƒ (Dynamic)` — `allowImportingTsExtensions` (needed for Node to
    run the `.ts` tests) does not disturb the Next build.
  - `npm view fake-indexeddb dist-tags` → `latest: 6.2.7` (the `beta` tag is an unrelated 4.0.0-beta.6);
    the installed version reads back `6.2.7` → the pin is the current stable, per `AGENTS.md` rule 5.
  - **The blocker — the `fetch` invariant is broken.** `grep -rn "fetch(" apps/web/src/` now matches
    **two** files:
    ```
    apps/web/src/lib/ghost/vault.ts:448:  options.fetchImpl ?? ((input, init) => fetch(input, init));
    apps/web/src/lib/api/client.ts:204:  response = await fetch(url, {
    ```
    T-006's done-when says that grep must match **only** `client.ts`, and `AGENTS.md` §11 restates it:
    "`client.ts` … is the **only** file under `src/` allowed to call `fetch`". The whole point of the
    typed client is that it is the single door to the API — auth headers, base URL, the error envelope and
    the `ApiError` type. A second, raw `fetch` in the vault bypasses all four, and it is exactly the
    pattern that let T-006's first attempt ship a page that called `fetch("/api/v1/health")` directly.
    T-012's task file does not mention the rule (it predates T-006's rework), which is why the worker had
    no way to know — but the invariant is the project's, not the task file's.
- fix list (worker):
  1. **Remove the raw `fetch` from `vault.ts`.** The delete must go through the typed client. Two workable
     shapes — pick one and keep the vault testable:
     - **(a)** Keep the vault framework-agnostic: make the transport an injected seam with **no default**
       `fetch`, and put the default wiring in `src/lib/api/` (a small `ghost.ts` next to `client.ts`) that
       delegates to the typed client. The vault then contains zero `fetch` calls.
     - **(b)** Give `ApiClient` a public method for a body-carrying DELETE with no response body (e.g.
       `requestVoid(path, {method:"DELETE", body})`) and call it from the vault. Note that the existing
       `request<T>()` **cannot** be used as-is: it insists on a `{data, meta}` envelope and would throw
       `invalid_response` on a 204/empty body, and it would also reject the `owner_key` payload shape.
     Either way the existing test must keep proving the same behaviour: the request carries the derived
     `owner_key` in the body, `DELETE /posts/{id}`, and the local key is removed only on success.
  2. **Make the invariant machine-enforced.** It has now been broken once, and a grep in a task file is not
     a guard. Add an ESLint rule that bans `fetch(` outside `src/lib/api/client.ts` — e.g. a config block
     scoped to `src/**/*.{ts,tsx}` with `src/lib/api/client.ts` ignored, using `no-restricted-syntax` with
     the selector `CallExpression[callee.name="fetch"]` (or `no-restricted-globals` with `name: "fetch"`).
     Then `npm run lint` fails for anyone who adds a second call site.
  3. **Remove the modulo bias in `generateAlias()`.** `byte % ALIAS_ALPHABET.length` over 256 bytes with a
     31-character alphabet is biased: `256 % 31 = 8`, so the first 8 characters are ~3.5 % more likely than
     the rest. The backend's `random_alias` uses unbiased `secrets.choice`; the client should match. Use
     rejection sampling (`byte < 248` → `byte % 31`) or an equivalent unbiased draw.
  4. **Wrap the base64url decode error.** `fromBase64Url` throws a plain `Error`, so `importVault` can
     surface an untyped error instead of `GhostVaultError("invalid_vault", …)`. Wrap it.
  5. Re-run `npm run test:ghost`, `npm run lint`, `npm run typecheck`, `npm run build` and paste the real
     output; then paste the `grep -rn "fetch(" apps/web/src/` result showing only `client.ts`.
- notes (no action required, carried forward):
  - **The alias lives in `sessionStorage` (per tab) while the post keys live in IndexedDB (per origin).** A
    second tab therefore gets a *different* alias but can still delete the first tab's posts. AD-007 says
    "one alias per browser session" — decide in T-041 whether the alias belongs in the vault next to the
    keys, and document the answer.
  - **`crypto.subtle` needs a secure context.** `http://localhost` is fine, but a deployed instance over
    plain HTTP has no `crypto.subtle` and the ghost flow breaks silently. The deployment must be HTTPS.
  - **The DELETE transport for `owner_key` is still unspecified.** `docs/API.md` only shows `owner_key` in a
    create body; the vault sends it in a DELETE body. T-015 (create) and T-021 (delete) must agree on one
    transport (body vs header) and write it into `docs/API.md`. Note that the Next rewrite proxy has to
    forward a DELETE body — worth one live check when the endpoint exists.
  - `setSessionAlias()` does not validate the prefix the way `getSessionAlias()` does. Cosmetic.
  - **The frontend's generated types are still stale** — `apps/web/src/lib/api/types.ts` predates
    `/auth/*`. Re-run `npm run api:types` **on the host** before T-012's output is consumed by T-020.
  - The task's `files:` list said `apps/web/lib/ghost/…`; the worker correctly used `apps/web/src/lib/ghost/`
    (the scaffold puts library code under `src/`, and the `~/*` alias only reaches `src/`). The worker
    updated the list — that was the right call.
- next: the rework is small and self-contained. **T-013** (Delhi area seed) is unblocked and independent of
  this task, so it can start while the rework happens.

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**. All five rework items are done and I re-ran every `## Done when` check myself; the
  single-fetch-door invariant is now machine-enforced, not merely remembered.
- checked (re-run by the manager on this machine; nothing taken from the worker's report):
  - `npm run test:ghost` → `tests 17`, `suites 3`, `pass 17`, `fail 0` (the 17th case is the new alias-bias
    test).
  - `npm run lint` → `✔ No ESLint warnings or errors`, exit 0. `npm run typecheck` → exit 0, no output.
    `npm run build` → `✓ Compiled successfully in 884ms`, `/` still `ƒ (Dynamic)`, `/_not-found` `○`.
  - **The fetch invariant holds.** A search of `apps/web/src/` for `fetch(` returns exactly **one** match —
    `apps/web/src/lib/api/client.ts:158` (`options.fetchImpl ?? ((input, init) => fetch(input, init))`).
    The word `fetch` appears elsewhere only in comments (`src/lib/api/ghost.ts:4-5`, `src/lib/api/client.ts:43`).
    `vault.ts` has no network code at all.
  - **The guard actually bites.** I dropped a probe at `src/__fetch_probe.ts` calling `fetch(url)` and ran
    lint: `Error: Call fetch only from src/lib/api/client.ts — use the typed API client instead.
    no-restricted-syntax`, exit 1. The probe is deleted; `git status` shows no leftovers.
  - **The HMAC, recomputed independently again** with my own `node:crypto` one-liner (not the repo's test):
    `HMAC-SHA256(key = bytes 00..1f, msg = "post-123")` → `BaCamp9SDkGtI1yYKz_76ElI3Kq2QXghpcnxz0UACEI`
    (hex `05a09a9a9f520e41ad235c982b3ffbe84948dcaab6417821a5c9f1cf45000842`); the uuid vector
    `KuKeZcKXwA4w5U3TZBDV_Mk8SK4U-pemWTvt9MQsR_c` matches. The two wrong variants still differ (reversed
    key/message `DdEyTvbh0yKAy6wapJD-cT1INsnEljUD5zyx3zGzE5M`; key-as-base64url-string
    `-Yy1EmPuBt6unoMDpmS6sX3jdzUoA8f2F8cLOVSSh_k`), so the vector pins both the HMAC direction and the
    "raw bytes, not encoded string" detail a Kotlin/Swift client will need.
  - **Rework item 1 — no raw fetch in the vault.** `deleteOwnPost(postId, { transport })` derives the owner key
    and hands it to the injected transport; `src/lib/api/ghost.ts` binds that to the typed client
    (`DELETE /posts/{id}`, body `{ owner_key }`) and `ApiClient.requestVoid` sends it without demanding a
    `{data, meta}` envelope (a 204 body would have thrown `invalid_response` under `request()`).
  - **Rework item 2 — machine-enforced.** `apps/web/eslint.config.js` bans
    `CallExpression[callee.name="fetch"]` for `src/**/*.{ts,tsx}` with `src/lib/api/client.ts` ignored, and
    `next lint` fails on a violation (proved above).
  - **Rework item 3 — modulo bias gone.** `ALIAS_ALPHABET.length === 31`, `ALIAS_UNBIASED_LIMIT === 248`
    (`floor(256/31)*31`), and `generateAlias()` rejects bytes ≥ 248 before the draw. The test pins both
    numbers, so a future edit that re-introduces the bias fails the suite.
  - **Rework item 4 — decode errors are typed.** `decodeStoredKey()` wraps `fromBase64Url` into
    `GhostVaultError("invalid_vault")`, and it is used by `getSessionKey`, `getPostKey` and `importVault`.
  - **Rework item 5 — the delete test still proves the real thing.** `vault.test.ts` drives the actual
    `createGhostTransport(new ApiClient({ fetchImpl }))`: one call to `/api/v1/posts/post-42`, method
    `DELETE`, body `owner_key` **equal to the locally derived key**, and the stored key removed only on
    success — a 500 raises `delete_failed` and keeps the secret.
  - **Vault behaviour.** The tests cover persistence across a closed/reopened IndexedDB connection (the reload
    case), export → `resetVault` → import round trip, malformed/unsupported export rejection, and the
    missing-secret path (`GhostVaultError("missing_secret")`, and the transport is never called).
  - **SSR-safe and unbundled.** Importing `src/lib/ghost/index.ts` in plain Node (no `fake-indexeddb`) works —
    31 exports, `generateAlias()` and `deriveOwnerKey()` run — so there is no import-time IndexedDB access.
    `.next/static/chunks/*.js` contains no `postly-ghost` / `Neighbor_` / `deriveOwnerKey`: nothing imports
    the ghost code into the app yet.
  - **Pin check.** `npm view fake-indexeddb dist-tags` → `latest: 6.2.7` (the `beta` tag is an unrelated
    `4.0.0-beta.6`); the installed tree reads back `fake-indexeddb@6.2.7` and `package-lock.json` carries the
    integrity hash. Exact pin, current stable — `AGENTS.md` rule 5 satisfied.
- notes (no action required, carried forward):
  - **`globalThis.fetch(url)` slips past the ESLint rule** (I probed it: lint exits 0). Only the bare
    `fetch(...)` call form is caught. If the guard needs to be airtight, add `no-restricted-globals` for
    `fetch`/`globalThis`/`window` — but the rule as it stands satisfies the rework item and is enough to
    stop the accidental second door.
  - **The `owner_key` encoding is still not written down.** The client produces base64url; the backend's own
    fixture uses hexdigest (`backend/tests/test_auth.py:308`). The server stores and compares the string
    opaquely, so nothing breaks today — but `docs/API.md` / `docs/SECURITY.md` must pin the encoding (and the
    DELETE transport: JSON body vs header) in T-015/T-021, or a Kotlin/Swift client will not interoperate.
  - The alias lives in `sessionStorage` while the post keys live in IndexedDB, so a second tab gets a
    different alias but can still delete the first tab's posts. Decide in T-041 whether the alias belongs in
    the vault next to the keys (AD-007).
  - `resetVault()` has no `onblocked` handler: if another tab holds the database open,
    `indexedDB.deleteDatabase` fires neither `success` nor `error` and the promise never settles. Minor, but
    the "delete everything" UI (T-041) must not hang on it.
  - `crypto.subtle` needs a secure context — `http://localhost` is fine, a deployed instance must be HTTPS.
  - The frontend's generated types are still stale: `apps/web/src/lib/api/types.ts` knows only
    `/api/v1/health` (the backend now has `/auth/*`). Re-run `npm run api:types` **on the host** before
    T-020 consumes it.
  - `setSessionAlias()` does not validate the prefix the way `getSessionAlias()` does. Cosmetic.
  - Nothing imports `src/lib/ghost` into the app yet — the wiring exists, the UI does not. That is T-021's
    job, not a gap here.
  - Process: the quest file is manager-owned; the worker updated its T-012 row to `rework` on its own. I have
    set it to `done` below. The board row also stayed `[ ]` while the task was at `review` — fixed now.
- next: **T-013** (Delhi area seed) is unblocked and independent. T-015/T-021 must consume the vault and
  settle the `owner_key` encoding + DELETE transport in `docs/API.md`.
