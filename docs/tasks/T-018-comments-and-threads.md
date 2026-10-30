# T-018 · Comments + nested threads + comment votes

- status: ready
- quest: Q1
- depends: T-015, T-017
- owner: -
- updated: -
- files: backend/app/api/v1/comments.py, backend/app/schemas/comment.py, backend/app/services/comments.py, backend/tests/test_comments.py

## Goal

Give the post a debate. Comments nest up to three levels, can be voted on, and work the same for Google,
pseudonymous and ghost users. This is where "who is to blame" gets argued out.

## Done when

- [ ] `POST /api/v1/posts/{id}/comments` creates a top-level comment; passing `parent_id` creates a reply.
- [ ] Replies are limited to depth 3 — a deeper reply is rejected with a clear error, not silently
      flattened.
- [ ] `GET /api/v1/posts/{id}/comments` returns the full thread with `parent_id` and `depth`, newest-last,
      cursor-paginated.
- [ ] Comment votes work through the same vote endpoint as post votes (T-017) and the comment's counters
      update.
- [ ] A ghost comment stores `ghostOwnerKey` and `authorId = null`; the response never leaks the key.
- [ ] The author can edit and delete their comment; nobody else can.
- [ ] `pytest -q` covers: top-level, reply, depth limit, thread retrieval, edit/delete ownership, ghost
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

Record the orphan-reply decision and any prisma-client-py self-relation quirks in this task's
`## Research notes`.

## Work log

## Report

## Manager review
