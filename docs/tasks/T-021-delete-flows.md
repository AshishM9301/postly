# T-021 · Delete flows: post, account, ghost purge, removal request

- status: ready
- quest: Q1
- depends: T-011, T-012, T-015
- owner: -
- updated: -
- files: backend/app/api/v1/me.py, backend/app/api/v1/posts.py, backend/app/api/v1/ghost.py, backend/app/services/deletion.py, backend/tests/test_deletion.py, docs/SECURITY.md, docs/API.md

## Goal

Make deletion real and complete. Every path in the privacy promise must work: delete one post, delete the
whole account, purge everything created with a ghost session key, and — for someone who lost their key —
request a moderator-assisted removal. Deletion is **hard**: rows and files, never a flag.

## Done when

- [ ] `DELETE /api/v1/posts/{id}` removes the post row, its comments, votes, blame votes, reveals, views,
      reports, its media rows **and the media files on disk**.
- [ ] `DELETE /api/v1/me` removes the user row and everything that belongs to them: posts (with their
      media files), comments, votes, follows, area follows, reveals, notifications, sessions and push
      subscriptions.
- [ ] A pseudonymous account deletion requires the client secret as well as the session token; a wrong
      secret is rejected.
- [ ] `POST /api/v1/ghost/purge` with a session key deletes every post, comment and vote created with that
      key — and **only** those. The sweep must not touch another session's content.
- [ ] `POST /api/v1/posts/{id}/removal-request` creates a request a moderator can act on, without requiring
      the caller to prove ownership.
- [ ] `pytest -q` asserts the database and the media directory are empty of the deleted content afterwards.
- [ ] A test proves a deleted user's posts no longer appear in any feed or in `GET /users/{id}/posts`.
- [ ] `docs/SECURITY.md` and `docs/API.md` describe exactly what is deleted.

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

## Work log

## Report

## Manager review
