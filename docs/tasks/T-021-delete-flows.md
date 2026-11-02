# T-021 · Delete flows: post, account, ghost purge, removal request

- status: done
- quest: Q1
- depends: T-011, T-012, T-015
- owner: s-20261102-0814
- updated: 2026-11-02 08:45
- files: backend/app/api/v1/me.py, backend/app/api/v1/posts.py, backend/app/api/v1/ghost.py, backend/app/api/v1/router.py, backend/app/schemas/deletion.py, backend/app/services/deletion.py, backend/app/services/posts.py, backend/tests/test_deletion.py, docs/SECURITY.md, docs/API.md

## Goal

Make deletion real and complete. Every path in the privacy promise must work: delete one post, delete the
whole account, purge everything created with a ghost session key, and — for someone who lost their key —
request a moderator-assisted removal. Deletion is **hard**: rows and files, never a flag.

## Done when

- [x] `DELETE /api/v1/posts/{id}` removes the post row, its comments, votes, blame votes, reveals, views,
      reports, its media rows **and the media files on disk**.
- [x] `DELETE /api/v1/me` removes the user row and everything that belongs to them: posts (with their
      media files), comments, votes, follows, area follows, reveals, notifications, sessions and push
      subscriptions.
- [x] A pseudonymous account deletion requires the client secret as well as the session token; a wrong
      secret is rejected.
- [x] `POST /api/v1/ghost/purge` with a session key deletes every post, comment and vote created with that
      key — and **only** those. The sweep must not touch another session's content.
- [x] `POST /api/v1/posts/{id}/removal-request` creates a request a moderator can act on, without requiring
      the caller to prove ownership.
- [x] `pytest -q` asserts the database and the media directory are empty of the deleted content afterwards.
- [x] A test proves a deleted user's posts no longer appear in any feed or in `GET /users/{id}/posts`.
      (`GET /users/{id}/posts` does not exist yet — it is T-051 — so the test covers `/feed/new` and
      `/feed/trending` and the DB row.)
- [x] `docs/SECURITY.md` and `docs/API.md` describe exactly what is deleted.

## Notes / gotchas

- **Hard delete only.** No `deletedAt`, no tombstones, no soft-delete flags. A privacy promise that leaves
  rows behind is not a promise.
- Deleting media means deleting the file from `backend/media/` as well as the row. Test the filesystem, not
  just the database.
- The ghost purge works because ownership keys are salted per target: the server recomputes
  `HMAC(sessionKey, targetId)` for candidate rows and compares. Do not add a stored session row for
  ghosts — that would make them linkable.
- The purge sweep over every post to find matches is O(n). Fine at this scale; note the cost in the report
  so a later task can add an index or a marker column.
- Order matters: delete children before parents (votes and comments before posts) or the foreign keys
  complain.
- The API must be idempotent: deleting an already-deleted post returns `404`, not `500`.
- A user who deletes their account must not be able to come back and see their old content through a cached
  client — the frontend clears its cache (that part is a frontend task; note it in the report).

## Research notes

The deletion contract: `docs/SECURITY.md` §4. The endpoints: `docs/API.md` §2 and §4. The data model
cascade: `docs/DATA_MODEL.md` §8.

Record the prisma-client-py cascade-delete behaviour you relied on (or did not) in this task's
`## Research notes` — it is the part most likely to surprise.

- **Cascades that do work** (from `schema.prisma`): deleting a `Post` cascades `Media`, `Comment` (both the
  `postId` and `Comment.parent` relations), `BlameVote` and `PostView`. Deleting a `User` cascades
  `Session`, `Post`, `Comment`, `Vote`, `BlameVote`, `Follow` (both sides), `AreaFollow`, `UserReveal`,
  `Notification` and `PushSubscription`.
- **Cascades that do NOT exist:** `Vote`, `UserReveal` and `Report` are polymorphic (`targetType` +
  `targetId`) and have **no FK** to a post/comment/media. The service deletes those rows explicitly before
  the parent row. `Vote` also has no timestamp and no FK, as T-017 warned.
- **Do not rely on `Comment.parent` cascade for account deletion:** it would delete other users' replies to
  a deleted user's comment. Account deletion reuses `_promote_children` from `services/comments.py` so
  replies survive and shift up.
- **Reports are anonymised, not deleted, when the user goes:** `Report.reporterId` and `handledBy` are
  `onDelete: SetNull`; `ModerationRecord.reviewedBy` likewise. T-021's Done-when list does not include
  reports owned by the user, and `SECURITY.md` now says so.
- `Notification.payload` is a Prisma `Json` field: a plain dict is rejected (`P2009`), the test must use
  `prisma.fields.Json({...})`.
- `db.tx()` + `delete_many(where={"field": {"in": [...]}})` works as expected; guard empty lists because an
  empty `in` is still a query.
- Ghost purge input is the **base64url form of the raw 32-byte secret**, not the ASCII string of the encoded
  key. The server decodes first so it reproduces the client's WebCrypto HMAC (T-012 shows the key is raw
  bytes).

## Work log

- 2026-11-02 s-20261102-0814: implemented post/account/ghost purges, removal request, docs; 5 new deletion
  tests; full suite 99 passed.

## Report

### 2026-11-02 · worker s-20261102-0814

- changed:
  - `backend/app/services/deletion.py` (new) — hard delete of a post, an account and a ghost session.
    Explicitly removes polymorphic `Vote`/`UserReveal`/`Report` rows, deletes media files through the
    storage provider, promotes replies instead of cascading them for account/comment deletes, and sweeps
    ghost rows with constant-time `HMAC(secret, targetId)` comparisons.
  - `backend/app/api/v1/posts.py` — `DELETE /posts/{id}` now calls the full cascade; added
    `POST /posts/{id}/removal-request` (no ownership proof, creates an `OPEN` `Report`).
  - `backend/app/api/v1/me.py` — added `DELETE /me` (`204`); pseudonymous accounts must send `secret`.
  - `backend/app/api/v1/ghost.py` (new) + `router.py` — `POST /ghost/purge` with `{session_key}`.
  - `backend/app/schemas/deletion.py` (new) — request/response shapes.
  - `backend/app/services/posts.py` — the `delete_media_files` placeholder now actually deletes each
    `Media.path`/`thumbPath` from storage.
  - `backend/tests/test_deletion.py` (new) — 5 tests: post cascade + files, account cascade (including
    reply promotion and feed removal), pseudonymous secret gate, ghost-session isolation, removal request.
  - `docs/API.md` — exact `/me` delete body, ghost purge encoding/response, removal-request contract,
    media-with-post note, `invalid_secret` code.
  - `docs/SECURITY.md` — exact deletion matrix, ghost-purge encoding, per-post-key caveat, reports SetNull.
- verified:
  - `docker compose exec -T api python -m pytest -q` → `99 passed, 1 warning in 110.52s`.
  - `docker compose exec -T api python -m pytest tests/test_deletion.py -q` → `5 passed, 1 warning`.
  - `docker compose exec -T api ruff check app tests` → `All checks passed!`
  - `docker compose exec -T api ruff format --check app tests` → `54 files already formatted`.
- issues / follow-ups:
  - **`GET /users/{id}/posts` does not exist yet** (it is T-051). The feed half of the Done-when is tested;
    the test also proves the row is gone. Re-check the users endpoint when T-051 lands.
  - **Standalone `DELETE /media/{id}`** was listed in `docs/API.md` §9 as "(T-021)" but is not in this task's
    `files:` list or Done-when. I did not add it; the doc now says media is deleted with its post. If the
    contract needs standalone media deletion, open a follow-up task.
  - **Per-post ghost keys are not swept by the session purge.** The session key reproduces only rows whose
    owner key was derived from it. Content made with a separate per-post key must be deleted with that
    post's `owner_key` or via the removal request. Documented in both docs.
  - The purge is **O(n)** over all ghost posts/comments/votes, as the task anticipated. No index/marker
    column added.
  - **Frontend cache clearing after account deletion is still a frontend task** (not in this backend
    scope); the web app also has no UI for purge/removal yet.
  - `services/deletion.py` imports the private `_promote_children` from `services/comments.py`. If that
    helper changes, both call sites must move together; a later refactor can make it public if desired.
- next: manager verification. After that, T-040 (ghost expiry sweep) is the natural follow-up; T-022 does
  not exist.

## Manager review

### 2026-11-02 · manager s-20261102-0810

- verdict: **accepted**. The worker did the hard part properly: the polymorphic rows without a foreign key
  are swept explicitly, the media files really leave the disk, and the ghost purge only touches its own
  session. I re-ran the suite and then drove every flow against the live API myself.
- checked (re-run by me; nothing taken from the worker's report):
  - `docker compose exec -T api python -m pytest -q` → `99 passed, 1 warning in 110.40s`.
  - `ruff check app tests` → `All checks passed!`; `ruff format --check app tests` → `54 files already
    formatted`.
  - **Post delete, live** (container restarted so the new code was loaded): `POST /posts` 201 →
    `POST /media` 201 → `POST` comment 201 → `PUT /votes/POST/{id}` 200 (`up=1`) →
    `PUT /votes/COMMENT/{id}` 200 → `POST /posts/{id}/removal-request` 201 (no auth) →
    `DELETE /posts/{id}` **204** → `DELETE` again **404** (idempotent, not a 500).
  - **Ownership gate**: `DELETE /posts/{id}` with a wrong `owner_key` on a **live** post → **403
    `not_owner`**, the post is still `GET`-able (200); with the right key → 204 ✓.
  - **Rows after the post delete** (SQL): post 0 · media 0 · comment 0 · votes 0 · `user_reveals` 0 ·
    `reports` 0 · `post_views` 0 — and **`find /app/media -type f` returns nothing**: the file the upload
    wrote is gone, not just its row. That was the gap T-016/T-020 left open.
  - **Account delete, live**: `POST /auth/pseudo` 200 → `DELETE /me` with **no** secret **403
    `invalid_secret`** → with a **wrong** secret 403 → with the **right** secret **204** → `DELETE /me`
    again **401** (the session died with the user). The user row, the session, the post, the media row and
    the media file are gone; the user's own comment is gone; **another user's reply to that comment survived
    and was promoted** (`parent_id: null`, `depth: 0`); the other user's post is still in `/feed/new` ✓.
  - **Ghost purge, live**: two ghost sessions → purge one → `{"posts":1,"comments":1,"votes":1}`; the other
    session's post **survived**, the purged session's post, comment and vote are **gone**; a non-canonical
    key → **422 `validation_error`** ✓.
  - **Removal request, live**: no auth at all → **201**, and the `reports` row is `reporter_id: null`,
    `reason: removal_request`, `status: OPEN`; **the post stays up** until a human acts ✓.
  - **Docs**: `docs/API.md` pins the `/me` body, the ghost-purge encoding and response, the removal-request
    contract and the new `invalid_secret` code; `docs/SECURITY.md` states the exact deletion matrix, the
    per-post-key caveat and the `SetNull` behaviour for reports ✓.
- notes (carried forward, no rework needed):
  - The `GET /users/{id}/posts` half of the Done-when **cannot** run — that endpoint is T-051. The test
    covers `/feed/new`, `/feed/trending` and the DB row, exactly as the task file says.
  - `DELETE /media/{id}` was dropped from the API contract and the doc now says media dies with its post.
    Correct for now; a standalone media delete is a possible small follow-up, not a defect.
  - `POST /ghost/purge` is unauthenticated **by design** — the session secret is the credential. It is
    O(n) over every ghost post/comment/vote, and it has no rate limit yet: T-037 must cover it.
  - The frontend has **no** deletion UI: no "delete my post", no "delete my account", no purge button and
    no removal-request form. That is a frontend task, not a defect in this one.
  - My own script mistakes, logged so the next session does not repeat them: I first posted a reply with an
    `owner_key` derived from a random id instead of the comment's own id (→ 422), and I probed the
    wrong-owner-key case on an already-deleted post (→ 404); re-run on a live post it is 403 `not_owner`.
- environment left clean: **0 posts, 0 comments, 0 media rows, 0 reports, 0 files in the media volume**,
  1 pre-existing user + session, and 1 pre-existing orphan vote from the T-020 review session — that
  orphan exists because `Vote` has no foreign key, which is precisely the gap this task closes for every
  deletion from now on.
- next: the board has no frontend tasks left for Q1. The new tasks are **T-022** (app shell + theme),
  **T-023** (comments UI), **T-024** (deletion UI) and **T-025** (sign-in UI).
