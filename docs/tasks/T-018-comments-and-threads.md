# T-018 · Comments + nested threads + comment votes

- status: done
- quest: Q1
- depends: T-015, T-017
- owner: s-20261101-0810
- updated: 2026-11-01 10:47
- files: backend/app/api/v1/comments.py, backend/app/api/v1/router.py, backend/app/schemas/comment.py, backend/app/services/comments.py, backend/tests/test_comments.py, docs/API.md

## Goal

Give the post a debate. Comments nest up to three levels, can be voted on, and work the same for Google,
pseudonymous and ghost users. This is where "who is to blame" gets argued out.

## Done when

- [x] `POST /api/v1/posts/{id}/comments` creates a top-level comment; passing `parent_id` creates a reply.
- [x] Replies are limited to depth 3 — a deeper reply is rejected with a clear error, not silently
      flattened.
- [x] `GET /api/v1/posts/{id}/comments` returns the full thread with `parent_id` and `depth`, newest-last,
      cursor-paginated.
- [x] Comment votes work through the same vote endpoint as post votes (T-017) and the comment's counters
      update.
- [x] A ghost comment stores `ghostOwnerKey` and `authorId = null`; the response never leaks the key.
- [x] The author can edit and delete their comment; nobody else can.
- [x] `pytest -q` covers: top-level, reply, depth limit, thread retrieval, edit/delete ownership, ghost
      comment.

## Notes / gotchas

- `Comment.id` is **client-generated** (UUID) like `Post.id` — a ghost computes its `owner_key` from it
  before sending.
- `depth` is stored on the row so listing does not need recursion. Compute it from the parent's depth + 1 on
  create.
- When a parent comment is deleted, decide what happens to its replies: keep them as top-level orphans, or
  delete them. **Pick one, implement it, and write it down in `docs/API.md`** — the client needs to know.
  (Recommendation: keep the replies, set `parentId = null`.)
- Counter updates: `Post.comment_count` must be accurate, including when comments are deleted.
- Comments inherit the post's area but are not separately area-filtered.
- No notification side effects yet — T-052 adds them. Do not build a notification stub here.

## Research notes

The comment model: `docs/DATA_MODEL.md` §3. The endpoint contract: `docs/API.md` §5. The ghost key scheme:
`docs/SECURITY.md` §2.

### Findings (2026-11-01)

- **Orphan decision: keep the replies.** Deleting a comment detaches its direct children (`parent_id =
  null`) and shifts each subtree up so promoted roots are `depth = 0` (children of a deleted depth-`d`
  comment lose `d + 1`). Only the deleted comment decrements `Post.comment_count`; replies stay counted.
  This avoids the schema's `onDelete: Cascade` deleting the whole subtree, which would have lost the
  debate.
- Prisma's self-relation works normally: `find_many(where={"parentId": id})` walks down one level at a
  time. Detaching with `update_many(..., {"parentId": None})` alone would leave inconsistent depths, so
  the service updates rows recursively inside the transaction.
- Cursor pagination: `order=[{"createdAt": "asc"}, {"id": "asc"}]`, `cursor={"id": last_id}`, `skip=1`,
  `take=limit+1` works in prisma-client-py 0.15. Fetch one extra row to compute `has_more`; the cursor is
  the last returned id.
- The create + `commentCount` increment and the delete + decrement run in `db.tx()` like T-017.

## Work log

- 2026-11-01 s-20261101-0810: implemented create/reply/thread/edit/delete with depth cap, ownership and
  counter transactions; keep-replies-on-delete; 10 tests, 83 total pass.

## Report

### 2026-11-01 · worker s-20261101-0810

- changed:
  - `backend/app/schemas/comment.py` — `CommentCreate` (optional client UUID, `parent_id`, ghost
    alias/owner_key), `CommentUpdate`, `CommentOwnerKey`, the allow-list `CommentOut`, and a
    `CommentPage` envelope with `meta.cursor`/`meta.has_more`.
  - `backend/app/services/comments.py` — depth computation + cap 3, parent-must-belong-to-post check,
    owner checks (session/ghost key), transactional create/delete with `Post.comment_count`, and
    keep-replies promotion on delete.
  - `backend/app/api/v1/comments.py` — `POST/GET /posts/{id}/comments`, `PATCH/DELETE /comments/{id}`.
  - `backend/app/api/v1/router.py` — wire the comments router.
  - `backend/tests/test_comments.py` — 10 tests: top-level, reply depths, pagination, edit ownership,
    ghost edit/delete keys, keep-replies, comment votes, 404/422 edges.
  - `docs/API.md` §5 — create body, response, depth cap, pagination and the keep-replies policy.
- verified (real output):
  - `python -m pytest -q` → **83 passed** (10 new); `ruff check .` → all checks passed;
    `ruff format --check .` → all files already formatted.
  - Live ghost smoke: root comment `depth=0`, reply `parent=root depth=1`; thread rows=2; deleting the
    root promoted the reply to `parent=null depth=0`; `Post.comment_count` went to 1; then cleaned up.
  - SQL after the suite: 0 leftover `T018` posts/comments/users, 0 orphan COMMENT votes.
- issues / notes:
  - `GET /comments/{id}/replies` (listed in API.md §5) is not implemented; the flat thread endpoint
    already contains every reply and the client rebuilds the tree from `parent_id`. Documented in §5.
  - No notification side effects (T-052), as instructed.
  - A ghost can use a different `owner_key` per comment; the reply smoke used one per target, matching
    the HMAC-per-target design.
- next: T-019 (feed tabs/ranking) is now unblocked with T-016, T-017, T-018 done.

## Manager review

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**. I built a thread on the live API — root, three reply levels, one level too deep —
  paged it, edited it, voted on it and deleted the root of it, then checked the two invariants over the
  whole table with SQL. The keep-replies policy works exactly as documented.
- checked (re-run by the manager; nothing taken from the worker's report):
  - **Threading.** Root → `depth: 0`, `parent_id: null`; replies → `depth: 1`, `2`, `3`; one level deeper →
    **422 `max_depth_exceeded`** ("Comments nest at most 3 levels deep") — rejected, not silently flattened ✓.
  - **Thread listing.** All four comments came back with `parent_id` and `depth`, oldest-first ✓.
  - **Cursor pagination.** `?limit=2` → 2 rows + `meta.cursor` + `meta.has_more: true`; the cursor → the
    next 2 rows, `has_more: false`, no overlap ✓. A cursor that is not a comment of this post → **422
    `validation_error`** ✓.
  - **Ghost comment.** 201, the client-generated UUID stored **verbatim**, `author: null`, the alias
    snapshotted, and the raw body leaked **nothing** — no `ghostOwnerKey`, no `owner_key`, not the key value.
    The stored row has `authorId = None` and `ghostOwnerKey` exactly as sent ✓.
  - **Duplicate comment id** → **409 `conflict`** ✓.
  - **Ownership.** The author edits → **200**; another user → **403 `not_owner`**; a ghost with a wrong key →
    **403**; a ghost with the right key → **200** ✓.
  - **Comment votes go through the same endpoint as post votes** (T-017): the comment's counters moved
    (`up=1`) while the post's vote counters stayed `0/0` ✓.
  - **Delete keeps replies — the documented policy.** Deleting the root promoted its reply to
    `parent_id: null, depth: 0` and shifted the rest of the subtree up by one (depth 1, 2); only the deleted
    comment decremented the post's `comment_count` (5 → 4) ✓.
  - **Invariants over the whole table.** A SQL join found **0 posts** whose `comment_count` disagrees with
    their comment rows, and **0 comments** whose `depth` ≠ the parent's depth + 1 ✓.
  - **Error paths.** Unknown post → **404 `post_not_found`**; unknown parent → **404 `comment_not_found`**;
    unknown comment on PATCH and DELETE → **404**; a bad cursor → **422** ✓.
  - **Tests.** `docker compose exec api python -m pytest -q` → `83 passed, 1 warning` (the pre-existing
    Starlette `httpx` deprecation). `ruff check .` → `All checks passed!`; `ruff format --check .` → `49 files
    already formatted`.
  - **I left the environment clean:** 0 posts, 0 comments, 0 votes, 1 pre-existing user.
- notes (no action required, carried forward):
  - **Deleting a comment orphans its votes — I proved it.** Bob voted on Alice's comment; Alice deleted the
    comment; the vote row **survived**, pointing at a comment that no longer exists. `Vote` is polymorphic —
    its only foreign key is `votes.voter_id → users` — so a vote disappears only when the *voter* is deleted.
    The same applies to deleting a post: the schema cascades the comments away, but their votes stay.
    **T-021 must sweep the votes of deleted posts and comments** (and `Report`, `ModerationRecord`,
    `UserReveal`) — the gap the T-015 research notes already listed, now confirmed for comments as well.
  - `GET /comments/{id}/replies` is **not implemented**; `docs/API.md` §5 now says so ("not implemented; use
    the flat thread"). The flat endpoint carries every reply and the client rebuilds the tree from
    `parent_id`, so nothing is missing from the contract.
  - The depth cap is `depth ≤ 3`, i.e. a root plus three reply levels (four rows deep) — `docs/API.md` says
    "capped at 3" with the root at 0, so it is unambiguous.
  - `Comment.moderationState` starts as `CLEAN`, exactly like posts — T-030/T-035 must revisit the initial
    state (the same note as T-015).
  - A ghost uses one `owner_key` per comment (`HMAC(commentKey, commentId)`), which matches the per-target
    design ✓.
  - No notification side effects, as instructed — T-052 owns them.
- next: **T-019** (feed tabs + ranking) is unblocked now that T-016, T-017 and T-018 are done; T-021 must
  sweep the orphaned votes when a post or comment is deleted.
