# T-019 · Feed tabs (for-you / trending / new / nearby) + ranking

- status: done
- quest: Q1
- depends: T-016, T-017, T-018
- owner: s-20261101-0810
- updated: 2026-11-01 11:15
- files: backend/app/api/v1/feed.py, backend/app/api/v1/router.py, backend/app/services/feed.py, backend/app/schemas/feed.py, backend/tests/test_feed.py, backend/app/core/config.py, docs/API.md

## Goal

Build the four feed tabs and the ranking that makes them different. This is the "local news panel" — a
time-decayed ranking so fresh problems surface, old ones decay, and no single author or area takes over.

## Done when

- [x] `GET /api/v1/feed/new` returns posts newest-first.
- [x] `GET /api/v1/feed/trending` returns posts ordered by the time-decayed score.
- [x] `GET /api/v1/feed/for-you` boosts the caller's area and followed areas/authors when signed in, and
      behaves like trending for an anonymous caller.
- [x] `GET /api/v1/feed/nearby?lat=&lng=&radius_m=` returns posts within the radius ordered by distance.
- [x] The ranking matches the documented formula:
      `score = engagement * exp(-age_hours / HALF_LIFE) * area_boost * affinity_boost`
      with `engagement = log10(max(1, net_votes) + 2) + 0.6*comments + 0.05*views`.
      Write a test with fixed timestamps that asserts the order of three posts.
- [x] Cursor pagination works and does not skip or repeat posts when new posts arrive between pages.
- [x] `pytest -q` covers all four tabs, the filters (`area_id`, `category_id`) and the pagination.
- [x] Posts with `moderation_state = HIDDEN` never appear in any feed.

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

### Findings (2026-11-01)

- **Ranking is done in Python**, not SQL: Trending/For You load the newest `FEED_CANDIDATE_LIMIT = 1000`
  non-hidden posts with `include={area,category,author,media}` and compute
  `decayed_score()` from the counters. This keeps the formula identical to the documented one and avoids a
  SQL/Python drift. The bound is documented; a later optimisation can move it into SQL/materialised scores.
- **Pagination**:
  - `/feed/new`: a `(created_at, id)` cursor with `ORDER BY created_at DESC, id DESC`; the next page filters
    `created_at < c OR (created_at = c AND id < c.id)`. A late post sorts above the cursor and is simply not
    returned by that pagination session — existing posts never repeat.
  - `/feed/trending` / `/feed/for-you`: the cursor embeds the pinned `now`, the last score and the last id.
    Page 2 reuses that `now`, recomputes the same scores, and keeps rows after `(-score, id)`. New posts
    cannot reorder existing rows between pages.
  - `/feed/nearby`: cursor over `(distance_m, id)`; distances are stable for fixed `lat`/`lng`.
- **Boosts**: For You, signed-in only — selected `area_id` 2.0×, followed areas (`AreaFollow`) 1.5×,
  followed authors (`Follow`) 1.5×. Anonymous For You = Trending order (no boosts). Half-lives are
  `Settings.for_you_half_life_hours = 12` / `trending_half_life_hours = 18`.
- **Diversity penalty**: not implemented; recorded in the backlog for a later ranking pass.
- Follows are read directly from `AreaFollow`/`Follow` (T-051 will expose the write endpoints).

## Work log

- 2026-11-01 s-20261101-0810: implemented all four feed tabs, the Python ranking + pinned-now cursors,
  For You boosts, Nearby distance filtering, hidden-post exclusion; 11 tests, 94 total pass.

## Report

### 2026-11-01 · worker s-20261101-0810

- changed:
  - `backend/app/services/feed.py` — `engagement()`/`decayed_score()`, opaque cursor encode/decode,
    `(created_at,id)` new feed, `(pinned now, score,id)` ranked feeds with area/affinity boosts,
    `(distance,id)` nearby feed, hidden-post filtering, candidate bounds.
  - `backend/app/api/v1/feed.py` — `/feed/new`, `/feed/trending`, `/feed/for-you`, `/feed/nearby`
    with shared `area_id`/`category_id`/`limit`/`cursor` params.
  - `backend/app/schemas/feed.py` — `FeedPost` (post + optional score/distance), `FeedPage`/`FeedMeta`.
  - `backend/app/api/v1/router.py` — wire the feed router.
  - `backend/app/core/config.py` — configurable half-lives (12 h / 18 h defaults).
  - `backend/tests/test_feed.py` — 11 tests with an isolated area/category: new ordering + filters,
    trending formula/decay, For You author/area boosts, anonymous parity, nearby radius/distance,
    hidden exclusion, two pagination tests with a late arrival, invalid cursor, radius validation.
  - `docs/API.md` §7 — formula, half-lives, boosts, cursor rules, radius bounds, response shape.
- verified (real output):
  - `python -m pytest -q` → **94 passed** (11 new); `ruff check .` → all checks passed;
    `ruff format --check .` → all files already formatted.
  - Live smoke (2 posts, 2 comments, 1 vote): `/feed/new` → `B,A`; `/feed/trending` →
    `A:1.677, B:0.477`; `/feed/for-you` → `A,B`; `/feed/nearby` → `A:0m, B:1479m`.
  - SQL after the suite: no leftover `T019` posts/comments and no orphan POST votes.
- issues / notes:
  - The caller's own area is represented by the `area_id` filter; because it filters, its 2× boost cannot
    reorder posts inside that set. Followed areas/authors are what visibly change For You ordering.
  - No diversity penalty yet (backlog).
  - The 1000/2000 candidate bounds mean very old high-engagement posts can be excluded from Trending/Nearby;
    documented in the research notes for a future SQL/materialised-score pass.
- next: T-020 (frontend feed UI) is unblocked.

## Manager review

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**. I recomputed the ranking formula myself and compared it with the API, measured every
  boost, paged all three cursor kinds and proved that HIDDEN posts stay hidden. One sentence in
  `docs/API.md` was wrong and I corrected it.
- checked (re-run by the manager; nothing taken from the worker's report):
  - **Isolated fixtures.** I created a throwaway area with three posts whose counters and ages I set
    directly in Postgres, so the ranking could be predicted by hand.
  - **`/feed/new`** → newest first (C, B, A by age) ✓.
  - **`/feed/trending`** → ordered by the decayed score, and the API's scores matched **my own
    recomputation of the documented formula** to ~1e-4 (B `1.161996` vs my `1.162369`, C `0.756590` vs
    `0.756833`, A `0.198130` vs `0.198194` — the residual is my rounded age, not the server's maths) ✓.
  - **`/feed/for-you` anonymous** → the 12 h half-life, and again my recomputation matched (B `1.099025` vs
    `1.099554`, C `0.746035` vs `0.746394`) ✓.
  - **The boosts, measured rather than assumed.** The selected `area_id` → **×2.0** on every post in the
    filtered area (a uniform multiplier, so it never reorders); a followed **area** → **×1.5 exactly**
    (measured `1.119583 / 0.746393 = 1.5000`); a followed **author** → **×1.5 exactly**; both together →
    **×2.25** (measured `1.822559 / 0.810031 = 2.2500`). The affinity boost made a post **overtake**
    another in the order ✓.
  - **`/feed/nearby`** → ordered by distance (A `0 m`, B `1480 m`); `radius_m=100` returned only A; the post
    **without coordinates was excluded** ✓.
  - **HIDDEN posts never appear.** I flipped one post to `HIDDEN` and it disappeared from **all four** tabs
    (`new`, `trending`, `for-you`, `nearby`) ✓.
  - **Filters** (`area_id`, `category_id`) work; an unknown area gives an empty feed ✓.
  - **Pagination.** `/feed/new`, `/feed/trending` and `/feed/nearby` with `limit=1` returned every post
    **exactly once**. **A late arrival between pages**: page 1 = [C, B], a new post arrived, page 2 = [A] —
    no overlap, and none of the original three was skipped ✓.
  - **Invalid cursor → 422**; `radius_m=0` and `radius_m=99999` → 422 ✓.
  - **Tests.** `docker compose exec api python -m pytest -q` → `94 passed, 1 warning` (the pre-existing
    Starlette `httpx` deprecation). `ruff check .` → `All checks passed!`; `ruff format --check .` → `53 files
    already formatted`.
  - **I left the environment clean:** 0 posts, 0 votes, 103 areas, 549 aliases, 1 pre-existing user; my
    throwaway area, follows and identities are deleted.
- correction I made (manager owns the docs):
  - `docs/API.md` §7 said "Anonymous For You applies no boosts (**order matches Trending**)". I **proved that
    wrong**: with X (5 upvotes, 10 h old) and Y (1 upvote, fresh), Trending puts X first (`0.4849` vs
    `0.4771`) while anonymous For You puts Y first (`0.4771` vs `0.3673`) — the half-lives differ (12 h vs
    18 h), so the older post decays faster in For You. The sentence now says the order *can* differ.
- notes (no action required, carried forward):
  - **The "caller's area" boost is only knowable through the `area_id` filter** — with `area_id=X` every post
    in the result gets ×2.0, a uniform multiplier that cannot reorder anything. The worker flagged this
    honestly, and it is right: a real "my area" needs a home area the schema does not have, so the frontend
    will pass `area_id`. The visible personalisation comes from the followed areas and authors.
  - **The followed-area boost is shadowed when the caller filters by that same area**: the `area_id` branch
    wins (×2.0) before the followed-area branch (×1.5) is considered. Harmless (2.0 > 1.5), but the ×1.5
    only shows when the caller does *not* filter by that area.
  - **The candidate bounds** (1000 for the ranked tabs, 2000 for nearby) mean a very old, high-engagement
    post can be missing from Trending/Nearby. Fine at this scale; the later SQL/materialised-score pass
    should deal with it.
  - **No diversity penalty** — the task allowed skipping it with a note, and it is recorded in the backlog
    and in `docs/API.md` ✓.
  - The `Vote` table still carries **no timestamp**, so "trending" is driven by the post's age and its
    counters, never by vote recency. That is now the documented design rather than a gap.
  - `/feed/trending` internally builds a synthetic ghost `Principal` to disable the boosts — harmless, but a
    `tab` flag alone would be cleaner if the feed grows.
- next: **T-020** (the frontend feed UI) is unblocked and is the first task that consumes these endpoints;
  it should pass `area_id` and read the `score` / `distance_meters` fields.
