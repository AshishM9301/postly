# T-017 · Votes (up/down) + salted voter keys + counters

- status: ready
- quest: Q1
- depends: T-015
- owner: -
- updated: -
- files: backend/app/api/v1/votes.py, backend/app/schemas/vote.py, backend/app/services/votes.py, backend/tests/test_votes.py

## Goal

Let the community vote — up or down — on posts and comments, and make sure a vote is counted exactly once
per person (or per anonymous session) while keeping the counters correct.

## Done when

- [ ] `PUT /api/v1/votes/{target_type}/{target_id}` casts a vote; repeating it with a different value
      **changes** the vote rather than adding a second one.
- [ ] `DELETE` removes the vote and the counters go back down.
- [ ] The `upvote_count` / `downvote_count` on the post/comment row always match the vote rows — verified
      by a test that votes, unvotes and re-reads.
- [ ] A registered user cannot vote twice on the same target (the unique constraint holds), and the same is
      true for a ghost session.
- [ ] Two different ghost sessions on the same target produce two votes (they are different people as far
      as we know).
- [ ] A vote on a non-existent target returns `404`; a vote on a comment returns the comment's own counters.
- [ ] `pytest -q` covers all of the above.
- [ ] The API returns the new counters so the client can update without a refetch.

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
- Voting on your own post is allowed for now (no rule against it) — do not invent a restriction nobody asked
  for; note it in the report if it seems wrong.

## Research notes

The vote model: `docs/DATA_MODEL.md` §4. The endpoint contract: `docs/API.md` §6. The salted-key design:
`docs/SECURITY.md` §2.

If prisma-client-py makes transactions awkward, record the pattern you used here — T-021 (deletes) and
T-052 (notifications) need transactions too.

## Work log

## Report

## Manager review
