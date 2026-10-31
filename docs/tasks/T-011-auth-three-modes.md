# T-011 · Auth: Google + pseudonymous + ghost + session middleware

- status: done
- quest: Q1
- depends: T-010, T-004
- owner: s-20261031-1542
- updated: 2026-10-31 16:22
- files: backend/app/api/v1/auth.py, backend/app/api/v1/me.py, backend/app/api/v1/router.py, backend/app/core/security.py, backend/app/core/deps.py, backend/app/core/config.py, backend/app/main.py, backend/app/schemas/auth.py, backend/app/schemas/__init__.py, backend/app/services/ghost.py, backend/app/services/__init__.py, backend/tests/test_auth.py

## Goal

Implement the three identity modes and the middleware that resolves a caller on every request. This is the
most security-sensitive task in the project: the invariant is that **for ghost content the server holds no
secret and no link**.

## Done when

- [x] `POST /auth/google` accepts a Firebase ID token, verifies it with `firebase-admin`, and returns an
      opaque session token. A tampered or expired token is rejected with `401`.
- [x] `POST /auth/pseudo` creates a pseudonymous identity: the client sends a 256-bit `secret`, the server
      stores only `HMAC-SHA256(PEPPER, secret)` and returns an alias + session token. The raw secret is never
      persisted or logged.
- [x] `POST /auth/rotate-alias` issues a new alias for the same identity.
- [x] `GET /me` resolves the caller from the `Authorization: Bearer` header for all three modes and returns
      the right shape (mode, alias, expiry preference).
- [x] A **ghost** request carries no session at all: the server resolves ownership per row by comparing the
      client-supplied `owner_key` against `ghostOwnerKey`. A wrong key returns `403 not_owner`.
- [x] `pytest -q` covers: valid Google token, invalid token, pseudonymous create + reuse, rotate alias,
      ghost ownership success, ghost ownership failure, and "the server never receives the ghost secret".
- [x] No email, phone, IP or User-Agent is written to the database by any of these paths (assert it in a
      test or by inspecting the rows).
- [x] **Rework item (added by the manager, 2026-10-31):** a request-validation failure returns the
      documented error envelope **and never reflects the submitted value**. `POST /auth/pseudo` with a short
      secret must answer `{"error": {"code": "validation_error", …}}` and the response body must not contain
      the secret. A generic 500 must use the envelope too. See the manager review for the exact fix.

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

- **firebase-admin 7.7.0** call used: `auth.verify_id_token(id_token, check_revoked=False)`. It validates
  signature + expiry and raises `InvalidIdTokenError` / `ExpiredIdTokenError`. We explicitly compare
  `claims["aud"] == project_id` and `claims["iss"] == f"https://securetoken.google.com/{project_id}"`.
  `project_id` comes from the service-account JSON's `project_id`, falling back to `FIREBASE_PROJECT_ID`.
  We return **only** `claims["uid"]` (or `sub`) — email/phone in the claims are never copied anywhere.
- Credentials loading supports both an inline JSON string and a file path in `FIREBASE_ADMIN_CREDENTIALS`;
  there is no import-time Firebase initialisation, so tests and `APP_ENV=development` work without creds.
- **prisma-client-py 0.15.0 quirk:** it returns **timezone-aware** datetimes for `DateTime` columns
  (`Session.expiresAt`), even though the schema declares `timestamp(3)`. Compare against
  `datetime.now(UTC)` (aware) or you get `TypeError: can't compare offset-naive and offset-aware datetimes`.
- Session lookup is `db.session.find_unique(where={"tokenHash": ...}, include={"user": True})`; the raw
  token is never stored or logged.
- Success responses use the `Envelope[T]` generic from `app/schemas/auth.py` (`{"data": …}`), and
  `app/main.py` now maps `HTTPException` to the `{"error": {code, message, details}}` contract.
- Ghost ownership has no HTTP endpoint yet (posts arrive in T-015), so the test exercises
  `assert_ghost_owner` through a tiny probe FastAPI app.

## Work log

- 2026-10-31 s-20261031-1513: implemented auth + principal + ghost ownership; pytest 15 passed.
- 2026-10-31 s-20261031-1542: rework — error envelope for validation + unhandled errors; pytest 18 passed.

## Report

### 2026-10-31 · worker s-20261031-1513

- changed:
  - `backend/app/core/security.py` — HMAC(PEPPER) hashing, opaque `postly_sess_…` tokens, alias generator,
    constant-time compare, Firebase credentials loader + `verify_id_token` with aud/iss checks.
  - `backend/app/core/deps.py` — `Principal` + `get_principal` (Bearer → Google/pseudonymous; no header →
    ghost) and `require_user` (ghost rejected).
  - `backend/app/api/v1/auth.py` — `POST /auth/google`, `POST /auth/pseudo` (create/reopen by secret hash),
    `POST /auth/rotate-alias`.
  - `backend/app/api/v1/me.py` — `GET /me` for google / pseudonymous / ghost.
  - `backend/app/schemas/auth.py` (+ `schemas/__init__.py`) — request/response models and `Envelope[T]`.
  - `backend/app/services/ghost.py` (+ `services/__init__.py`) — `assert_ghost_owner` → `403 not_owner`.
  - `backend/app/api/v1/router.py` — wire auth + me routers.
  - `backend/app/core/config.py` — Firebase/session/ghost-expiry settings.
  - `backend/app/main.py` — HTTP exceptions rendered as the `{"error": …}` contract envelope.
  - `backend/tests/test_auth.py` — 13 tests.
- verified:
  - `docker compose exec api python -m pytest -q` → `15 passed, 1 warning in 6.54s`
  - `docker compose exec api ruff check .` → `All checks passed!`
  - `docker compose exec api ruff format --check .` → `23 files already formatted`
  - `docker compose exec api python -m prisma migrate status` → `Database schema is up to date!`
  - live smoke: `GET /api/v1/health` → `{"status":"ok","db":"ok"}`;
    `GET /api/v1/me` (no header) → `{"data":{"mode":"ghost","alias":null,...,"expiry_days":90}}`;
    `POST /api/v1/auth/pseudo` → alias + `postly_sess_…`, then `GET /me` with Bearer → `mode: pseudonymous`.
- issues / notes:
  - Google verification is tested with `firebase_admin.auth.verify_id_token` monkeypatched; the real
    network path needs real credentials and is not exercised. The aud/iss checks themselves are real code
    and covered by the wrong-audience test.
  - `expiry_days` is validated on `/auth/pseudo` but there is no column to persist a per-session preference
    yet (planned T-040); `/me` returns the configured default (`GHOST_POST_TTL_DAYS=90`).
  - No schema/migration changes. `main.py` gained the error-envelope handler because the contract in
    `docs/API.md` §1 requires it and auth errors are the first ones that need it.
- next: T-012 (ghost crypto helpers + local key vault) or T-013 (Delhi area seed) — both have no remaining
  dependency on this task.

### 2026-10-31 · worker s-20261031-1542 (rework)

- changed:
  - `backend/app/main.py` — added a `RequestValidationError` handler that returns the documented envelope
    and sanitises every error to `{type, loc, msg}` (drops `input` and `ctx`, so the submitted secret is
    never reflected); added an `Exception` handler returning `500 internal_error` with a generic message
    and server-side logging only.
  - `backend/tests/test_auth.py` — added: short secret → 422 envelope with no echo, non-object JSON body →
    422 envelope with no echo, unhandled exception → 500 envelope with no exception text.
- verified:
  - `docker compose exec api python -m pytest -q` → `18 passed, 1 warning in 7.95s`
  - `docker compose exec api ruff check .` → `All checks passed!`
  - `docker compose exec api ruff format --check .` → `23 files already formatted`
  - live `POST /api/v1/auth/pseudo` with `{"secret":"mysecret"}` (from inside the container):
    ```
    HTTP 422
    {"error":{"code":"validation_error","message":"Request validation failed",
              "details":{"errors":[{"type":"string_too_short","loc":["body","secret"],
                                    "msg":"String should have at least 32 characters"}]}}}
    leak: False
    ```
  - live `POST /api/v1/auth/pseudo` with `["s3cr3t-must-not-appear"]` → 422 `validation_error`,
    `model_attributes_type`, `leak: False`.
  - live `GET /api/v1/nope` → 404 `{"error":{"code":"not_found","message":"Not Found","details":{}}}`.
- issues / notes:
  - The `Exception` handler is proven through a probe FastAPI app in pytest (a route that raises a
    distinctive message; status 500, envelope, text absent). In production uvicorn sends the handler's
    response; TestClient needs `raise_server_exceptions=False` to observe it, so the real app route set
    is untouched.
  - No changes outside the rework scope; no schema/migration changes.

## Manager review

### 2026-10-31 · manager s-20261031-1558

- verdict: **rework**. The anonymity design is right and every done-when item is met — but one path leaks
  the submitted secret back to the client and breaks the documented error envelope. The fix is small and
  lives in one file the task already touches.
- checked (every item re-run by the manager from the current tree; the running container was already on the
  new code — `GET /api/v1/me` and `/openapi.json` both show the auth endpoints):
  - **The ghost invariant holds.** `GET /api/v1/me` with no `Authorization` header → 200
    `{"data":{"mode":"ghost","alias":null,"user_id":null,"expiry_days":90,"is_admin":false}}` — **no User row,
    no Session row**. `require_user` rejects a ghost with 401. `assert_ghost_owner` compares with
    `hmac.compare_digest` (`security.secure_compare`) and raises **403 `not_owner`**; an empty/`None` key
    never matches. A ghost post row was created with `authorId = None` and its `ghostOwnerKey`; the test
    asserts the post key is neither equal to nor contained in the stored key and that the user/session counts
    did not move. The server can only *compare* an owner key — it cannot derive one.
  - **Secrets are only stored as HMAC.** I recomputed it independently: `HMAC-SHA256(PEPPER, secret)` =
    `b4591abdf423402caad7f74ded420587630c23eca9d75fe6075e2445aa9c9707` = the `secret_hash` actually in the
    `users` row. The raw secret appears nowhere (`SELECT count(*) … LIKE '%S3cr3t%'` → 0). Session rows hold
    only a 64-hex `token_hash` — the raw `postly_sess_…` token is never stored.
  - **No contact or network data.** `information_schema.columns` for `users` and `sessions` shows only
    `secret_hash` / `token_hash`; the full `sessions` column list is
    `id,user_id,token_hash,created_at,expires_at,revoked_at` — **no email, phone, IP or User-Agent
    column**. The Google path stores only the Firebase `uid`: the test feeds an `email` and a `phone_number`
    in the claims and asserts neither appears in the user or session rows.
  - **Live flow.** `POST /auth/pseudo` → alias + `postly_sess_…`; the same secret again → **same alias, new
    token**; `GET /me` with the Bearer → `mode: pseudonymous`; `POST /auth/rotate-alias` → a new alias for the
    same identity. A malformed `Authorization: Basic abc` → 401 `unauthorized`; an unknown token → 401;
    an unknown route → 404 in the documented envelope.
  - **The production guard works.** `APP_ENV=production` with `PEPPER`/`SECRET_KEY` empty →
    `ValidationError: SECRET_KEY, PEPPER must be set when APP_ENV='production'` — the app refuses to start.
  - **Firebase aud/iss are real code, not decoration.** `verify_firebase_token` compares `claims["aud"]` to
    the project id and `claims["iss"]` to `https://securetoken.google.com/<project_id>`, and the
    wrong-audience and tampered/expired cases are covered by tests.
  - `pytest -q` → **15 passed** (13 test functions, 2 of them parametrized); `ruff check .` →
    `All checks passed!`; `ruff format --check .` → `23 files already formatted`.
  - **The blocker — the 422 path.** `POST /api/v1/auth/pseudo` with `{"secret":"mysecret"}`:
    ```
    HTTP/1.1 422 Unprocessable Content
    {"detail":[{"type":"string_too_short","loc":["body","secret"],
                "msg":"String should have at least 32 characters","input":"mysecret","ctx":{"min_length":32}}]}
    ```
    Two problems in one response:
    (a) **the submitted secret is reflected back** in `input` — FastAPI's validation errors include the
    offending value by default. The task's rule is that the raw secret must not escape the server, and
    response bodies are exactly what proxies, APM tools and client error logs capture;
    (b) the body is **FastAPI's default `{"detail": [...]}`**, not the contract's
    `{"error": {code, message, details}}` from `docs/API.md` §1. `app/main.py` registers a handler for
    `StarletteHTTPException`, but `RequestValidationError` is a different exception with its own
    FastAPI handler, so every 422 in the whole API misses the envelope. The T-006 typed client then sees a
    payload that is not an error envelope and reports **`internal_error` for every validation failure**.
    The same happens on `POST /auth/google` with an empty `id_token`.
- fix list (worker — small, all in `backend/app/main.py` plus one test):
  1. **Add a `RequestValidationError` handler** in `backend/app/main.py` that returns the documented
     envelope: `{"error": {"code": "validation_error", "message": …, "details": {…}}}`.
  2. **Never reflect the submitted value.** Build `details` from `exc.errors()` but keep only
     `type`, `loc` and `msg` per error — drop `input` and `ctx` (the `input` key is the leak), and make sure
     the `message` does not contain the value either. `exc.errors()` also accepts `include_input=False` on
     recent FastAPI — check the installed version and use it if available, otherwise strip explicitly.
  3. **Make a 500 use the envelope too.** `_HTTP_ERROR_CODES` already lists 500/503, but only
     `StarletteHTTPException` is handled, so an unexpected exception still returns FastAPI's plain-text
     "Internal Server Error". Add a generic handler that returns
     `{"error": {"code": "internal_error", "message": "Internal server error", "details": {}}}` and
     **does not leak the exception text** (log it server-side instead — never the request body).
  4. **Add a test** in `backend/tests/test_auth.py`:
     - `POST /auth/pseudo` with a too-short secret → 422, `response.json()["error"]["code"] ==
       "validation_error"`;
     - the response body **does not contain** the submitted secret (send a distinctive value such as
       `"s3cr3t-must-not-appear"` and assert it is absent from `response.text`);
     - the same for a body that is not a JSON object at all.
  5. **Re-run** `pytest -q`, `ruff check .`, `ruff format --check .` and paste the real output; then re-run
     the live `curl` of the 422 above and show the new body.
- notes (no action required, carried forward):
  - **`docs/API.md` says `GET /me` needs auth ("yes") — the implementation returns a ghost principal
    instead.** The behaviour is what the done-when asks for, so the **doc** is what is wrong. I have fixed
    the doc myself (see the board/quest update) — do not "fix" the endpoint to 401.
  - **The frontend's generated types are now stale.** `apps/web/src/lib/api/types.ts` was generated before
    `/auth/*` existed. Re-run `npm run api:types` **on the host** when the frontend starts using these
    endpoints (T-012 / T-020). The spec does not declare the 401/403/409 responses either, so the
    generated types will not tell the frontend that `/auth/google` can fail — handle 401 generically.
  - **A client-chosen alias can impersonate an official.** `PseudoAuthRequest.alias` accepts
    `^[A-Za-z0-9_]{3,32}$`, so `MCDelhi` or `Admin` is a valid alias. `docs/API.md` §2 documents `alias?`
    as part of the request, so the worker implemented the contract — the gap is in the contract: there is
    no reserved-name / official-impersonation rule anywhere in `docs/`. Raise it as a moderation rule for
    T-037 (or a new task); do not silently change the schema here.
  - **The aud/iss checks are skipped if no project id can be determined.** `_ensure_firebase_app()` only
    records the certificate's `project_id` when it initializes the app itself; if the app was already
    initialized elsewhere and `FIREBASE_PROJECT_ID` is unset, `_firebase_project_id()` returns `None` and
    the aud/iss comparison is **skipped** (the SDK's own signature check still applies). Failing closed
    when no project id is known would be safer.
  - **No rate limit on `POST /auth/pseudo`** — each call creates a new User *and* a new Session row, so an
    attacker can mint identities (and session rows) freely. T-037 owns rate limiting; T-062 owns session
    cleanup / rotation. Not a T-011 defect.
  - `expiry_days` is validated against `GHOST_EXPIRY_OPTIONS` but not persisted — the schema has no column
    for it (T-040 plans the per-session preference). `/me` returns the configured default. Correct for now,
    but `POST /auth/pseudo` accepting `expiry_days` and then ignoring it is a small contract lie.
  - **Bookkeeping:** the worker touched five files outside the task's `files:` list —
    `backend/app/main.py` (the envelope handler), `backend/app/core/config.py` (Firebase/session settings),
    `backend/app/api/v1/router.py` (wiring) and the two `__init__.py` files. All five are justified and
    documented in the report, and the envelope handler is exactly where the rework has to happen, so I have
    added them to `files:` rather than asking for churn. The done-when boxes are now ticked because I
    verified every one of them.
- next: the rework is a **small** follow-up in one file — any worker can take it. After it lands, T-011 is
  accepted and the board moves on; **T-012** (ghost crypto + key vault) and **T-013** (Delhi area seed) are
  both unblocked in the meantime.

### 2026-10-31 · manager s-20261031-1622 (re-review of the rework)

- verdict: **accepted**. T-011 is `done`; the board row is `[x]`.
- checked (re-run by the manager, from the current tree and against the running container — which the worker
  had restarted, so it was serving the new code):
  - **The blocker is fixed, live.** `POST /api/v1/auth/pseudo` with `{"secret":"mysecret"}`:
    ```
    HTTP/1.1 422 Unprocessable Content
    {"error":{"code":"validation_error","message":"Request validation failed",
              "details":{"errors":[{"type":"string_too_short","loc":["body","secret"],
                                    "msg":"String should have at least 32 characters"}]}}}
    ```
    The documented envelope ✓, `code: "validation_error"` ✓, **no `input`, no `ctx`, and the string
    `mysecret` is nowhere in the body** ✓. A non-object body (`["s3cr3t-must-not-appear"]`) →
    `422 validation_error` with `model_attributes_type` and no echo ✓.
  - **The 500 handler is wired into the real app, not just the probe app the test uses.** I added a
    `/__boom` route that raises `RuntimeError("CANARY-EXCEPTION-TEXT-MUST-NOT-LEAK")` to the **real**
    `app` object and drove it with `TestClient(app, raise_server_exceptions=False)`:
    `STATUS: 500` · `BODY: {"error":{"code":"internal_error","message":"Internal server error","details":{}}}`
    · `CANARY_IN_BODY: False`. The traceback goes to the server log (Starlette's `ServerErrorMiddleware`
    re-raises after sending the response, so uvicorn logs it) and nothing leaks to the client. The response
    also never carries a traceback because `FastAPI(...)` is built without `debug=`, so `DEBUG=true` cannot
    switch the traceback on. ✓
  - **The three new tests are the ones I asked for** (`test_validation_error_uses_envelope_and_never_echoes_the_secret`,
    `test_non_object_json_body_uses_envelope_without_echoing_it`,
    `test_unhandled_error_uses_envelope_without_leaking_details`) — including the strong form of the first
    one: every error object must have exactly `{type, loc, msg}`, so a future change that re-adds `input`
    fails the test.
  - `pytest -q` → **18 passed**, 1 warning; `ruff check .` → `All checks passed!`; `ruff format --check .` →
    `23 files already formatted`.
  - **The whole auth surface re-verified** (nothing in it changed since the first review, but re-run anyway):
    - `POST /auth/pseudo` → alias + `postly_sess_…`; the same secret again → **same alias**, new token;
      `GET /me` with the Bearer → `mode: pseudonymous`; `GET /me` with no header → `mode: ghost`,
      `alias: null`, `user_id: null`.
    - The stored `secret_hash` equals an **independently recomputed** `HMAC-SHA256(PEPPER, secret)`
      (`ff9d71a7fe905addec2ba4837b7339ae38b81dee3e9fd8fc6952b4c2a644c2a8` on both sides), and a
      `LIKE '%Verify-Secret%'` scan finds **0** plaintext rows.
    - `POST /auth/rotate-alias` without a session → 401 `unauthorized` ("This endpoint requires a session");
      with a bogus bearer → 401 `unauthorized` ("Invalid or expired session"); a malformed
      `Authorization: Basic abc` → 401; an unknown route → 404 `not_found` in the envelope.
    - `APP_ENV=production` with `PEPPER`/`SECRET_KEY` empty → the app still refuses to start.
    - `GET /api/v1/health` → `{"status":"ok","db":"ok"}`; the web page still renders `ok`/`ok`.
  - **Database left clean:** `users=0 sessions=0 categories=9 posts=0` — I deleted the two identities my
    first review created; the worker’s tests clean up after themselves.
- notes (no action required, carried forward — unchanged from the first review, none of them blocking):
  - **A client-chosen alias can impersonate an official** (`PseudoAuthRequest.alias` accepts
    `MCDelhi`, `Admin`). The contract allows `alias?`, so this is a **moderation gap**, not a code defect —
    it belongs to T-037 or a new task, together with a reserved-name rule.
  - **The aud/iss checks are skipped when no project id can be determined** (the app was initialised
    elsewhere and `FIREBASE_PROJECT_ID` is unset). Failing closed would be safer.
  - **No rate limit on `POST /auth/pseudo`** — every call mints a User *and* a Session row. T-037 / T-062.
  - **`expiry_days` is accepted but not persisted** (no column yet — T-040). `/me` returns the default.
  - **`settings.debug` is never wired to `FastAPI(debug=…)`** — harmless (fail-safe) but the flag is dead
    config.
  - **The frontend's generated types are stale** — `apps/web/src/lib/api/types.ts` predates `/auth/*`.
    Re-run `npm run api:types` **on the host** before T-012 / T-020 use those endpoints. The spec also does
    not declare the 401/403/409 responses, so the generated types will not tell the frontend that
    `/auth/google` can fail — handle 401 generically.
  - A 405 (wrong method) currently maps to `internal_error` because `_HTTP_ERROR_CODES` has no 405 entry.
    `docs/API.md` §14 does not list a `method_not_allowed` code either, so this is inside the documented
    set — but it reads oddly in a client. Worth revisiting when the error-code list is next touched.
- next: **T-011 accepted → Q1 moves on.** Unblocked now: **T-012** (ghost crypto + key vault) and
  **T-013** (Delhi area seed). **T-015** still waits for T-014.
