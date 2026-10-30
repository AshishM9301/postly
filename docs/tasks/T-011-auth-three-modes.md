# T-011 · Auth: Google + pseudonymous + ghost + session middleware

- status: ready
- quest: Q1
- depends: T-010, T-004
- owner: -
- updated: -
- files: backend/app/api/v1/auth.py, backend/app/api/v1/me.py, backend/app/core/security.py, backend/app/core/deps.py, backend/app/schemas/auth.py, backend/tests/test_auth.py, backend/app/services/ghost.py

## Goal

Implement the three identity modes and the middleware that resolves a caller on every request. This is the
most security-sensitive task in the project: the invariant is that **for ghost content the server holds no
secret and no link**.

## Done when

- [ ] `POST /auth/google` accepts a Firebase ID token, verifies it with `firebase-admin`, and returns an
      opaque session token. A tampered or expired token is rejected with `401`.
- [ ] `POST /auth/pseudo` creates a pseudonymous identity: the client sends a 256-bit `secret`, the server
      stores only `HMAC-SHA256(PEPPER, secret)` and returns an alias + session token. The raw secret is never
      persisted or logged.
- [ ] `POST /auth/rotate-alias` issues a new alias for the same identity.
- [ ] `GET /me` resolves the caller from the `Authorization: Bearer` header for all three modes and returns
      the right shape (mode, alias, expiry preference).
- [ ] A **ghost** request carries no session at all: the server resolves ownership per row by comparing the
      client-supplied `owner_key` against `ghostOwnerKey`. A wrong key returns `403 not_owner`.
- [ ] `pytest -q` covers: valid Google token, invalid token, pseudonymous create + reuse, rotate alias,
      ghost ownership success, ghost ownership failure, and "the server never receives the ghost secret".
- [ ] No email, phone, IP or User-Agent is written to the database by any of these paths (assert it in a
      test or by inspecting the rows).

## Notes / gotchas

- Firebase: `firebase_admin.auth.verify_id_token(id_token)` returns the decoded claims; **also** check that
  `iss == f"https://securetoken.google.com/{project_id}"` and that `aud` is the project id. The SDK's
  `verify_id_token` checks the signature and expiry; the issuer/audience check is still worth doing
  explicitly.
- The service-account credentials come from `FIREBASE_ADMIN_CREDENTIALS` in `.env`. Never commit them.
  Support both an inline JSON string and a file path.
- Session tokens: 32+ random bytes, opaque, stored as `HMAC-SHA256(PEPPER, token)` in `Session.tokenHash`.
  Send the raw token to the client once; the client keeps it (localStorage) and sends it as a Bearer.
- Ghost mode needs **no** `User` row and **no** `Session` row. If you find yourself creating one, the
  design is broken.
- `PEPPER` and `SECRET_KEY` are separate values. `PEPPER` hashes ownership keys and session tokens;
  `SECRET_KEY` signs short-lived URLs. Both come from the environment and must be required in non-dev.
- Do not log request bodies on `/auth/*` or the value of `owner_key` anywhere.
- The alias generator must produce something readable and unique (`Neighbor_` + 4 chars from a
  non-ambiguous alphabet), and must not collide — retry on collision.

## Research notes

The design this task implements: `docs/SECURITY.md` §2 and §3. The API shape: `docs/API.md` §2.

Add to this task's `## Research notes`: the exact firebase-admin call signature you used, how you verified a
token's issuer/audience, and any prisma-client-py session-model quirks.

## Work log

## Report

## Manager review
