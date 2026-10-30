# T-012 · Ghost crypto helpers + local key vault + export/import

- status: ready
- quest: Q1
- depends: T-004
- owner: -
- updated: -
- files: apps/web/lib/ghost/crypto.ts, apps/web/lib/ghost/vault.ts, apps/web/lib/ghost/alias.ts, apps/web/lib/ghost/index.ts, apps/web/lib/ghost/__tests__/crypto.test.ts, apps/web/lib/ghost/__tests__/vault.test.ts

## Goal

Build the client half of the anonymity design: the crypto helpers, the local key vault and the alias
generator. The browser is the only place the ghost secret ever exists. It must be correct, tested and
portable — a Kotlin or Swift client must be able to produce the same HMACs later.

## Done when

- [ ] `deriveOwnerKey(secret, targetId)` returns a base64url `HMAC-SHA256(secret, targetId)` using WebCrypto
      (`crypto.subtle.importKey` + `crypto.subtle.sign`), and the test vectors match a known-good
      implementation (verify with a one-line Node script using `node:crypto`).
- [ ] The secret is generated with `crypto.getRandomValues` (32 bytes) — never `Math.random`.
- [ ] The vault stores secrets in IndexedDB (`postKey` per post id, `sessionKey` for votes/comments), survives
      a page reload, and can be exported to a JSON file and imported back.
- [ ] `listOwnPosts()` returns the ids the user can still delete, and `deleteOwnPost(id)` computes the
      `owner_key` locally and calls the API.
- [ ] `rotateAlias()` produces a new alias and stores it for the session; the previous alias stays on older
      posts.
- [ ] Unit tests pass (`npm run test` if the scaffold has a runner, otherwise a `npm run test:ghost` script
      using node:test) and cover: determinism, different ids → different keys, export→import round trip,
      missing secret handling.
- [ ] `npm run lint`, `npm run typecheck`, `npm run build` pass.

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

Record the test vectors and the exact base64url encoding here so the server-side verifier (T-011/T-021) and
any future mobile client can be checked against them.

## Work log

## Report

## Manager review
