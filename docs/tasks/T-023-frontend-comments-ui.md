# T-023 · Frontend comments: thread view, replies and comment votes

- status: done
- quest: Q1
- depends: T-018, T-020
- owner: s-20261102-0927
- updated: 2026-11-02 10:15
- files: apps/web/src/components/**, apps/web/src/lib/api/endpoints.ts, apps/web/src/lib/identity.ts, apps/web/src/lib/ghost/vault.ts, apps/web/src/lib/ghost/index.ts, apps/web/src/lib/ghost/__tests__/vault.test.ts

## Goal

T-018's comment API is live and tested, but **no screen shows a thread**. This task gives every post a
thread: the comments below the card, a reply box under each comment (three levels deep, like the API), and
comment votes that update the counters immediately. Deleting a comment keeps its replies — the screen must
show that honestly (the replies move up instead of disappearing).

The app stays ghost-only here: a ghost comment is created with its own per-comment `owner_key`.

## Done when

- [x] Opening a post shows its comments, oldest first, with the thread shape (`parent_id` / `depth`).
- [x] A reply can be written under a comment; a reply under a reply works up to **depth 3** and the API's
      `422` for a deeper reply is shown as a message, not a crash.
- [x] A top-level comment can be written from the post card.
- [x] Upvote/downvote on a comment updates the counter immediately and reconciles with the server.
- [x] Deleting your own comment removes it and **keeps its replies** (they move up), exactly as the API does.
- [x] `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
      `✓ Compiled successfully`.
- [x] The only `fetch(` under `apps/web/src/` is in `src/lib/api/client.ts`.

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

- 2026-11-02 s-20261102-0927: built the comments dialog/thread, ghost comment keys, replies, comment
  votes and delete-with-promotion; lint/typecheck/build pass and a live proxy smoke exercised the full
  thread + depth 3 + delete flow.

## Report

### 2026-11-02 · worker s-20261102-0927

- changed:
  - `src/lib/ghost/vault.ts` — added a `comment:` record kind with `saveCommentKey`, `getCommentKey`,
    `deleteCommentKey` and `listOwnCommentIds`. Comments are kept out of `listOwnPosts()` so T-024 does
    not mistake a comment id for a post id.
  - `src/lib/ghost/index.ts`, `src/lib/identity.ts` — exports plus
    `createGhostCommentIdentity(commentId)` and `ownerKeyForComment(commentId)`; each comment gets its own
    32-byte key stored in IndexedDB and its own `HMAC(commentKey, commentId)`.
  - `src/lib/api/endpoints.ts` — `CommentOut`/`CommentPage`/`CommentCreate` types plus
    `getComments`, `createComment` and `deleteComment` (204 via `requestVoid`).
  - `src/components/comment-form.tsx` (new) — client-generated UUID, ghost alias/owner key, validation,
    API error shown inline (including `422 max_depth_exceeded`), feed + comment invalidation.
  - `src/components/comment-thread.tsx` (new) — infinite flat-list query, client-side tree rebuild,
    own-comment discovery from the vault, loading/error/empty states and "Load more".
  - `src/components/comment-item.tsx` (new) — recursive replies with a left rule, comment votes, reply
    form, and owner-only delete (confirmation says replies are kept).
  - `src/components/post-comments.tsx` (new) — the post card's comment-count button opens the thread
    dialog.
  - `src/components/vote-buttons.tsx` — generalized to `targetId` + `targetType` (`POST` / `COMMENT`) and
    syncs refreshed server counters; `post-card.tsx` uses the new props and renders `PostComments`.
  - `src/lib/ghost/__tests__/vault.test.ts` — one new case proving comment keys are stored separately and
    are not listed as posts (18 ghost tests now).
- verified (real output):
  - `npm run lint` → `✔ No ESLint warnings or errors`.
  - `npm run typecheck` → exit 0, no output.
  - `npm run build` → `✓ Compiled successfully`; `/` 23.3 kB, 222 kB First Load JS.
  - `npm run test:ghost` → `tests 18`, `pass 18`, `fail 0`.
  - `Select-String ... '\bfetch\('` → only `src/lib/api/client.ts:158`.
  - Live smoke **through the Next proxy** (`http://localhost:3000/api/v1`):
    `post.create 201`; `comment.root 201 0`; replies `1 2 3`; a depth-4 reply →
    `422 max_depth_exceeded "Comments nest at most 3 levels deep"`; thread listed root `d0` then
    `d1/d2/d3` with `parent_id` set; `comment.vote 200 1`; deleting the root → `204`, and the thread then
    returned the reply at `d0` with `parent_id` null, followed by `d1` and `d2`; `post.commentCount 3`;
    cleanup `post.delete 204`.
  - Rebuilt/recreated `postly-web`; container healthy and `curl http://localhost:3000` still returns 200
    with the shell (30,516 bytes).
- issues / notes:
  - The thread is opened by the comment-count button on the card; there is no separate post-detail page.
  - Own-comment detection is device-local by design: it comes from the comment keys in IndexedDB, so a
    comment can only be deleted on the device that holds its key (the same model as ghost posts).
  - Comment keys are **not yet in the vault export/import JSON**; that belongs with T-041's key export
    work. Until then, exporting/importing the vault preserves post keys but not comment keys.
  - The destructive action uses `window.confirm`; no browser screenshot was taken in this environment.
  - The dialog fetches 50 comments per page and loads more on demand; the tree rebuild treats a reply
    whose parent is not on the loaded page as a root (oldest-first paging should prevent this in practice).
- next: manager verification; T-024 (deletion UI) can use `listOwnCommentIds` / `deleteCommentKey`.

## Manager review

### 2026-11-02 · manager s-20261102-1010

- verdict: **accepted**, with one follow-up that this task surfaced but does not own. The thread UI is
  correct; the review found a real gap in the **backend** that the new delete button now exposes.
- checked (re-run by me; nothing taken from the worker's report):
  - `npm run lint` → `✔ No ESLint warnings or errors`; `npm run typecheck` → exit 0; `npm run build` →
    `✓ Compiled successfully` (`/` 23.3 kB, 222 kB First Load JS); `npm run test:ghost` → **18 pass**,
    0 fail (the new vault case included).
  - **The single-fetch-door invariant holds**: the only real `fetch(` under `apps/web/src/` is
    `src/lib/api/client.ts:158`.
  - **The API flow, driven by me through the Next proxy** (my own script, not the worker's):
    root comment → **201, depth 0** → reply → **201, depth 1** → depth 2 → **201** → depth 3 → **201** →
    depth 4 → **422 `max_depth_exceeded`** ✓; `GET /posts/{id}/comments` → the flat list with depths
    `[0,1,1,2,3]` and `parent_id` set ✓; `PUT /votes/COMMENT/{id}` → **200 `up=1`** ✓;
    `DELETE /comments/{id}` with a **wrong** `owner_key` → **403 `not_owner`** ✓; with the right key →
    **204**, and the thread then showed the reply **promoted** (`parent_id: null`, `depth: 0`) ✓.
  - **Code read**: the tree is rebuilt on the client from `parent_id`; the reply form, the inline `422`
    message, the owner-only delete with a confirmation that says the replies are kept; `VoteButtons` is
    now `targetId` + `targetType` and reconciles with the counters the server returns; the ghost comment
    key is a **separate 32-byte key per comment**, stored as `comment:<id>` in the vault and never mixed
    with the post keys ✓; own-comment detection is device-local (the comment ids in the vault) — the same
    model as ghost posts ✓.
- **The finding — a backend gap, not a UI bug**: `DELETE /api/v1/comments/{id}`
  (`backend/app/services/comments.py::delete_comment`) deletes the comment row and promotes its replies but
  **does not sweep the rows that have no foreign key to it**. I proved it: after deleting a comment that
  had an upvote, the `votes` row was still there (`target_type = COMMENT`, target = the deleted comment).
  The post-delete path (T-021) sweeps them and the account/purge paths sweep them
  (`deletion.py::_remove_comment`), but the standalone comment delete does not. T-018 already flagged
  this ("T-021 must sweep the votes of deleted posts and comments"); T-021 closed it for posts and
  accounts, **not** for the comment endpoint — and this UI now puts that button in front of people.
  Filed as **T-027**.
- notes (carried forward):
  - The **comment keys are not in the vault export/import** yet: exporting preserves the post keys but
    not the comment keys. That belongs with T-041's key-export work.
  - The thread opens from the comment-count button on the card; there is no post-detail page.
  - The tree treats a reply whose parent is not on the loaded page as a root — with oldest-first paging
    that does not happen in practice, but it is worth knowing.
  - The destructive action uses `window.confirm`, and **no browser screenshot was possible here**, so the
    *visual* thread is unproven. The first person to open a post should look at it.
- environment left clean: 0 posts, 0 comments, 0 media rows, 0 files in the media volume. The two orphan
  votes this review produced are exactly the gap above; I removed them, and one pre-existing orphan from
  the T-020 session is still there (same cause, now tracked by T-027).
- next: **T-027** (the comment-delete sweep) and then **T-028** … **T-029** + **T-038** (the simple
  composer: AI category, auto area, ≤ 300 words).
