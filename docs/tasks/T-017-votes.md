# T-017 · Votes (up/down) + salted voter keys + counters

- status: done
- quest: Q1
- depends: T-015
- owner: s-20261101-0810
- updated: 2026-11-01 10:28
- files: backend/app/api/v1/votes.py, backend/app/api/v1/router.py, backend/app/schemas/vote.py, backend/app/services/votes.py, backend/tests/test_votes.py, docs/API.md

## Goal

Let the community vote — up or down — on posts and comments, and make sure a vote is counted exactly once
per person (or per anonymous session) while keeping the counters correct.

## Done when

- [x] `PUT /api/v1/votes/{target_type}/{target_id}` casts a vote; repeating it with a different value
      **changes** the vote rather than adding a second one.
- [x] `DELETE` removes the vote and the counters go back down.
- [x] The `upvote_count` / `downvote_count` on the post/comment row always match the vote rows — verified
      by a test that votes, unvotes and re-reads.
- [x] A registered user cannot vote twice on the same target (the unique constraint holds), and the same is
      true for a ghost session.
- [x] Two different ghost sessions on the same target produce two votes (they are different people as far
      as we know).
- [x] A vote on a non-existent target returns `404`; a vote on a comment returns the comment's own counters.
- [x] `pytest -q` covers all of the above.
- [x] The API returns the new counters so the client can update without a refetch.

## Notes / gotchas

- One `Vote` table serves posts, comments and blame targets, distinguished by `targetType`.
- `voterKey` is the deduplication key and it is **not** nullable:
  - registered / pseudonymous → `u:<userId>`
  - ghost → `a:HMAC-SHA256(sessionKey, targetId)` — salted per target, so one ghost's votes cannot be
    joined across posts, while still allowing one vote per target.
  The unique constraint `@@unique([targetType, targetId, voterKey])` then works for everybody.
- `voterId` stays nullable and points at the `User` for registered/pseudonymous voters, so "my votes" and
  account deletion work.
- The counter update must happen in the **same transaction** as the vote write. A vote that lands without
  its counter is a bug that shows up in the feed ranking.
- Vote flipping (up → down) must not double-count.
- `target_type` is validated against a whitelist (`POST`, `COMMENT`, `BLAME`).
  **Manager note (2026-11-01):** `BLAME` is deliberately **rejected** on this route (422 pointing at T-050) —
  the schema has a dedicated `BlameVote` table with its own counter, and T-050 owns
  `POST /posts/{id}/blame`. Implementing it here would double-count.
- Voting on your own post is allowed for now (no rule against it) — do not invent a restriction nobody asked
  for; note it in the report if it seems wrong.

## Research notes

The vote model: `docs/DATA_MODEL.md` §4. The endpoint contract: `docs/API.md` §6. The salted-key design:
`docs/SECURITY.md` §2.

### Findings (2026-11-01)

- **Prisma transactions work as advertised:** `async with db.tx() as tx:` gives a `Prisma`-shaped object
  isolated until the block exits; the vote write and the counter increment run inside it. No helper or
  raw SQL was needed. T-021/T-052 can use the same pattern.
- The compound unique key is addressed as
  `where={"targetType_targetId_voterKey": {"targetType": …, "targetId": …, "voterKey": …}}`.
- Counter updates use Prisma's atomic `{"increment": n}` on `upvoteCount`/`downvoteCount`; the updated row
  returns the new values, so no re-read is needed.
- The generic route accepts **POST** and **COMMENT**. `BLAME` is deliberately rejected: blame votes live in
  `BlameVote` and belong to `POST /posts/{id}/blame` (T-050).
- A ghost's `voter_key` must match `^a:[A-Za-z0-9_-]{43}$` — enforcing the `a:` prefix stops a ghost from
  guessing a `u:<userId>` key and overwriting someone's vote.

## Work log

- 2026-11-01 s-20261101-0810: implemented PUT/DELETE votes with transactional counter updates, ghost
  per-target voter keys, comment targets and flip handling; 8 tests, 73 total pass.

## Report

### 2026-11-01 · worker s-20261101-0810

- changed:
  - `backend/app/schemas/vote.py` — `VoteCast` (`value` 1/−1 + optional `voter_key`), `VoteRemove`,
    `VoteOut` (target, value, fresh counters).
  - `backend/app/services/votes.py` — target whitelist, ghost voter-key validation (`a:` + 43 base64url
    chars), `u:<userId>` for sessions, transactional create/update/delete + counter deltas, idempotent
    DELETE.
  - `backend/app/api/v1/votes.py` — `PUT` and `DELETE /votes/{target_type}/{target_id}` (DELETE body
    optional; ghosts send `voter_key`).
  - `backend/app/api/v1/router.py` — wire the votes router.
  - `backend/tests/test_votes.py` — 8 tests: create, flip, delete/idempotency, two users, two ghost
    sessions, ghost-key validation, comment counters, 404s/invalid type/value.
  - `docs/API.md` §6 — body shape, ghost `voter_key` contract, response with counters, BLAME note.
- verified (real output):
  - `python -m pytest -q` → **73 passed** (8 new); `ruff check .` → all checks passed;
    `ruff format --check .` → all files already formatted.
  - Live ghost smoke: `PUT +1` → `up=1 down=0`; flip `PUT −1` → `up=0 down=1`; `DELETE` → `value=null
    up=0 down=0`; `GET /posts/{id}` confirmed `0/0`; post deleted afterwards.
  - SQL after the suite: 0 leftover `T017` posts/users, 0 orphan POST votes.
- issues / notes:
  - **BLAME is rejected** on the generic route with a 422 pointing at T-050, even though the Notes list it
    in the whitelist. The generic table has no blame counter of its own and the schema already has a
    dedicated `BlameVote`; implementing it here would double-count against T-050.
  - Voting on your own post is allowed, as instructed.
  - Concurrent votes from the same key rely on the unique constraint; a racing second insert can surface as
    a DB error rather than a retry. Not needed for the MVP, but T-037/rate-limiting work should revisit it.
  - `GET /me/votes` (API.md §6) is still unimplemented; it needs a UX decision for ghost voters (their keys
    are per-target and the client would have to supply them).
- next: T-018 (comments + threads + comment votes) is now unblocked.

## Manager review

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**. I voted on the live API myself — cast, flip, repeat, delete, two users, two ghost
  sessions, comment targets and every error path — and then checked the counter invariant over the whole
  table with SQL. The counters and the vote rows agree everywhere.
- checked (re-run by the manager; nothing taken from the worker's report):
  - **Cast / flip / repeat.** `PUT +1` → `up=1, down=0`; `PUT −1` → `up=0, down=1` (the vote **moved**, not
    added); `PUT −1` again → `up=0, down=1` (no double count).
  - **A second user votes independently.** Bob `+1` → `up=1, down=1`, and `GET /posts/{id}` reported the same
    `upvote_count=1 / downvote_count=1` as the API response.
  - **Delete.** `DELETE` → the counter went down and `value` became `null`; a second `DELETE` → **200** with
    the same counters (idempotent).
  - **Ghosts.** A valid `a:<43 base64url>` key was accepted; **two different ghost keys on the same target
    produced two votes** (up=2, down=1 after the first flipped to −1). A ghost without a key → **422
    `voter_key_required`**; a ghost sending `u:someone` → **422** (it cannot claim a session key and
    overwrite someone's vote); a short key → **422**.
  - **Error paths.** Unknown post → **404 `post_not_found`**; unknown comment → **404 `comment_not_found`**;
    an unknown target type → **422**; `BLAME` → **422** with the message "BLAME votes use
    POST /posts/{id}/blame (T-050)"; `value: 2` → **422**.
  - **Comment targets use the comment's own counters.** Voting +1 then flipping to −1 on a comment gave the
    comment `up=0, down=1` (and the DB row agreed) while the post's counters stayed `0/0`.
  - **The invariant, checked over the whole table.** A SQL left join of `posts`/`comments` against `votes`
    returned **0 rows** whose `upvote_count`/`downvote_count` disagree with their vote rows.
  - **The stored keys are what the design says.** The session vote is `u:<userId>` with `voter_id` set; the
    two ghost votes are `a:<43 chars>` with `voter_id` **NULL** — a ghost vote links to no user row. The
    unique key is `(target_type, target_id, voter_key)` ✓.
  - **Tests.** `docker compose exec api python -m pytest -q` → `73 passed, 1 warning` (the pre-existing
    Starlette `httpx` deprecation). `ruff check .` → `All checks passed!`; `ruff format --check .` → `45 files
    already formatted`.
  - **I left the environment clean:** 0 posts, 0 comments, 0 votes, 1 pre-existing user. (Deleting my posts
    did **not** remove the vote rows — `Vote` has no FK to its target — so I deleted them explicitly; see
    the note below.)
- correction I made (manager owns the docs):
  - `docs/API.md` §6 listed `GET /me/votes` as if it existed. It does not (it needs a UX decision for ghost
    voters, whose keys are per-target), so I marked the row **"not implemented yet (planned)"** instead of
    leaving a contract the API does not honour. The rest of §6 — the ghost `voter_key` shape
    (`a:` + base64url HMAC-SHA256), the flip semantics, the counters in the response, the idempotent DELETE
    and the 404 codes — is accurate and now good enough for a Kotlin/Swift client to implement.
  - I amended the task's own Note about the target whitelist: `BLAME` is deliberately rejected here (the
    schema has a dedicated `BlameVote` table with its own counter and T-050 owns the blame endpoint), so the
    next session does not read it as a missing feature.
- notes (no action required, carried forward):
  - **The server cannot verify a ghost's `voter_key`** — it never sees the session key, so a malicious ghost
    could vote N times with N different keys on the same target. That is inherent to the anonymity design
    (the same trade-off as the post `owner_key`); the dedup guarantee holds for honest clients, and rate
    limiting (T-037) is the mitigation.
  - **The `Vote` table has no `createdAt`** (the schema from T-010, and `docs/DATA_MODEL.md` agrees). The
    feed's time-decayed ranking (T-019) will have to rank on `Post.createdAt` + counters, or T-019 needs a
    migration to timestamp the votes.
  - **Deleting a post orphans its votes** — `Vote` is polymorphic (`target_type`/`target_id`), so it has no
    FK to `Post`. My own cleanup hit exactly this. T-021 (delete flows) must sweep the vote rows for the
    deleted target ids, together with `Report`, `ModerationRecord` and `UserReveal` that the T-015 research
    notes already listed.
  - A racing second insert for the same voter key surfaces as a DB error rather than a retry — the worker
    flagged it and it is the right call for the MVP; T-037 should revisit it under load.
  - Voting on your own post is allowed, as the task instructed.
- next: **T-018** (comments + threads + comment votes) is unblocked; T-021 must sweep the polymorphic rows
  when a post is deleted, and T-019 needs to know the votes carry no timestamp.
