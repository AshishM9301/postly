# T-027 · Deleting a comment must sweep its votes, reveals and reports

- status: ready
- quest: Q1
- depends: T-018, T-021
- owner: -
- updated: 2026-11-02 10:25
- files: backend/app/services/comments.py, backend/app/services/deletion.py, backend/tests/test_comments.py, backend/tests/test_deletion.py, docs/SECURITY.md

## Goal

`DELETE /api/v1/comments/{id}` removes the comment and promotes its replies, but it leaves the rows that
have **no foreign key** to the comment behind: the `Vote` rows that targeted it, and any `UserReveal` or
`Report` rows targeting it. The post-delete path (T-021) sweeps them and the account/purge paths sweep
them (`deletion.py::_remove_comment`), but the standalone comment delete does not — and T-023's UI now
puts that button in front of people.

A deleted comment must leave **nothing** behind that points at it.

## Done when

- [ ] After `DELETE /api/v1/comments/{id}` there is **no** `Vote` row with
      `target_type = 'COMMENT'` and that comment's id, and no `UserReveal` / `Report` row targeting it.
- [ ] The comment's replies still survive and are promoted (the current behaviour must not regress):
      the reply's `parent_id` becomes null and its `depth` becomes 0.
- [ ] `Post.comment_count` is still decremented exactly once.
- [ ] A test proves it (the existing comment suite is in `backend/tests/test_comments.py`): vote on a
      comment, delete the comment, assert the vote row is gone.
- [ ] `docker compose exec -T api python -m pytest -q` → all pass;
      `docker compose exec -T api ruff check app tests` → `All checks passed!`;
      `docker compose exec -T api ruff format --check app tests` → `NN files already formatted`.
- [ ] `docs/SECURITY.md` §4 says that deleting a comment removes its votes, reveals and reports too.

## Notes / gotchas

- The fix belongs in `backend/app/services/comments.py::delete_comment`. `deletion.py` already has the
  right helper (`_delete_target_rows(tx, "COMMENT", [comment.id])`) — reuse it instead of writing a second
  copy. It is a private helper in another module: either make it public or import it deliberately, and
  say which in the report.
- **Order matters**: the polymorphic rows must go **before** the comment row, and the children must be
  promoted **before** the delete (the current order is right — do not reorder it carelessly).
- `Vote` has no timestamp and no FK, so an orphan is invisible: the only way to see the leak is to count
  the rows. The test must assert the count, not just the absence of an error.
- A vote on a **reply** of the deleted comment is a vote on a different target and must survive — the
  reply still exists.
- The ghost purge (T-021) sweeps ghost votes by voter key; do not break that.

## Research notes

- The leak was found during the T-023 manager review: deleting a comment that had an upvote left the
  `votes` row behind (`target_type = 'COMMENT'`). Reproduce it with SQL, not by trusting the API.

## Work log

## Report

## Manager review
