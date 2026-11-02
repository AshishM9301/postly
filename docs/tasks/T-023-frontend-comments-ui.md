# T-023 · Frontend comments: thread view, replies and comment votes

- status: ready
- quest: Q1
- depends: T-018, T-020
- owner: -
- updated: 2026-11-02 08:50
- files: apps/web/src/components/**, apps/web/src/lib/api/endpoints.ts, apps/web/src/lib/identity.ts

## Goal

T-018's comment API is live and tested, but **no screen shows a thread**. This task gives every post a
thread: the comments below the card, a reply box under each comment (three levels deep, like the API), and
comment votes that update the counters immediately. Deleting a comment keeps its replies — the screen must
show that honestly (the replies move up instead of disappearing).

The app stays ghost-only here: a ghost comment is created with its own per-comment `owner_key`.

## Done when

- [ ] Opening a post shows its comments, oldest first, with the thread shape (`parent_id` / `depth`).
- [ ] A reply can be written under a comment; a reply under a reply works up to **depth 3** and the API's
      `422` for a deeper reply is shown as a message, not a crash.
- [ ] A top-level comment can be written from the post card.
- [ ] Upvote/downvote on a comment updates the counter immediately and reconciles with the server.
- [ ] Deleting your own comment removes it and **keeps its replies** (they move up), exactly as the API does.
- [ ] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`.
- [ ] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts`.

## Notes / gotchas

- The API returns a **flat** list with `parent_id` and `depth`; the tree is rebuilt on the client.
- Comment ids are **client-generated** (a UUID) because a ghost derives its `owner_key` from the comment id:
  `owner_key = base64url(HMAC-SHA256(commentKey, commentId))`. The key must be derived from the id the
  client sends.
- The ghost library already has the helpers: `~/lib/ghost` (vault) and `~/lib/identity` (see T-012/T-020).
- A comment's votes use the same endpoint as post votes: `PUT /votes/COMMENT/{id}`.
- `Post.comment_count` is maintained by the server in the same transaction — trust the server's counter
  after a write, do not count locally.

## Research notes

- The contract: `docs/API.md` §5. The worker that built the API left notes in
  `docs/tasks/T-018-comments-and-threads.md` — read those before writing the screen.

## Work log

## Report

## Manager review
