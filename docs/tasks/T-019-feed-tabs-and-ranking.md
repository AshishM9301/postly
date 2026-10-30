# T-019 · Feed tabs (for-you / trending / new / nearby) + ranking

- status: ready
- quest: Q1
- depends: T-016, T-017, T-018
- owner: -
- updated: -
- files: backend/app/api/v1/feed.py, backend/app/services/feed.py, backend/app/schemas/feed.py, backend/tests/test_feed.py, docs/API.md

## Goal

Build the four feed tabs and the ranking that makes them different. This is the "local news panel" — a
time-decayed ranking so fresh problems surface, old ones decay, and no single author or area takes over.

## Done when

- [ ] `GET /api/v1/feed/new` returns posts newest-first.
- [ ] `GET /api/v1/feed/trending` returns posts ordered by the time-decayed score.
- [ ] `GET /api/v1/feed/for-you` boosts the caller's area and followed areas/authors when signed in, and
      behaves like trending for an anonymous caller.
- [ ] `GET /api/v1/feed/nearby?lat=&lng=&radius_m=` returns posts within the radius ordered by distance.
- [ ] The ranking matches the documented formula:
      `score = engagement * exp(-age_hours / HALF_LIFE) * area_boost * affinity_boost`
      with `engagement = log10(max(1, net_votes) + 2) + 0.6*comments + 0.05*views`.
      Write a test with fixed timestamps that asserts the order of three posts.
- [ ] Cursor pagination works and does not skip or repeat posts when new posts arrive between pages.
- [ ] `pytest -q` covers all four tabs, the filters (`area_id`, `category_id`) and the pagination.
- [ ] Posts with `moderation_state = HIDDEN` never appear in any feed.

## Notes / gotchas

- `HALF_LIFE` = 12h for For You, 18h for Trending (see `docs/PLAN.md` §5). Make it configurable.
- The score is computed at query time from the denormalised counters on the post row. Do not add a stored
  score column yet — a materialised snapshot is a later optimisation.
- The formula involves `exp()` and `log10()`. In Postgres, `exp()` and `log()` exist; `log10` may need
  `ln(x)/ln(10)`. Either compute in SQL or fetch candidates and rank in Python — but keep it consistent and
  test the SQL version against a Python reference.
- **Cursor pagination on a changing score is tricky.** Either pin the score calculation to a timestamp
  (`now` captured at request time and reused across pages) or use a cursor over `(created_at, id)`. Pick one,
  document it in `docs/API.md`, and test that no post is skipped.
- A diversity penalty (so one author or one area cannot own the panel) is in the plan. If you implement it,
  document the exact rule; if you skip it, say so in the report and leave it for the backlog.
- The `for-you` boost for a signed-in user needs follows (T-051). Until then, use the area boost only and
  leave a clear seam.
- Nearby needs the post's optional `lat`/`lng`. Posts without coordinates are excluded from Nearby but
  still appear in the other tabs (by area).

## Research notes

The ranking formula: `docs/PLAN.md` §5. The endpoint contract: `docs/API.md` §7. The counters:
`docs/DATA_MODEL.md` §3.

Record the pagination approach and the SQL you used for the score here — T-060 (API versioning) and any
future caching work will build on it.

## Work log

## Report

## Manager review
