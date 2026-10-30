# T-010 · Prisma schema (19 models) + migration + seed categories

- status: ready
- quest: Q1
- depends: T-003
- owner: -
- updated: -
- files: backend/prisma/schema.prisma, backend/prisma/migrations/**, backend/scripts/seed_categories.py, backend/tests/test_schema.py

## Goal

Write the real data model. `schema.prisma` becomes the single source of truth for the whole app: every later
task (auth, posts, media, votes, moderation, notifications) codes against these models, and the TypeScript
Prisma client for the frontend types is generated from the same file. Replace the probe schema from T-001.

## Done when

- [ ] `backend/prisma/schema.prisma` contains all 19 models, 7 enums and the documented indexes — matching
      `docs/DATA_MODEL.md` field for field.
- [ ] `python -m prisma migrate dev --name init` applies cleanly on an empty database.
- [ ] `python -m prisma migrate status` reports the database is in sync.
- [ ] `python -m prisma generate` succeeds and the generated models expose every field in the docs.
- [ ] `python scripts/seed_categories.py` inserts the 9 categories and is idempotent (running it twice
      leaves 9 rows).
- [ ] `pytest -q` includes a test that creates and reads one row of at least three different models
      (Post, Comment, Vote) through the generated client.
- [ ] The frontend can generate its TS types from the same schema (`prisma generate` with the
      `prisma-client-js` generator, output committed, **types only** — no database access from the browser).

## Notes / gotchas

- The frontend TS client is for **types only**. Never instantiate it in the browser and never ship a
  `DATABASE_URL` to the frontend.
- Every model with a `@@unique` constraint listed in `docs/DATA_MODEL.md` must have it — the anonymity and
  vote-dedupe design depends on those constraints.
- `Vote.voterKey` is `String` (not nullable) precisely so `@@unique([targetType, targetId, voterKey])`
  works for both registered and ghost voters. Registered users use `u:<userId>`, ghosts use
  `a:HMAC(sessionKey, targetId)`.
- `Post.id` and `Comment.id` are **client-generated UUIDs** (`@default(uuid())` gives a default, but the
  client will always send its own). Ghosts depend on the client knowing the id before it creates the row.
- `Post.ghostOwnerKey` and `Comment.ghostOwnerKey` are nullable and must be indexed if you ever query by
  them (the ghost purge sweep does).
- If a Prisma enum is awkward in the generated Python client, switch that field to `String` + a check
  constraint and record it in `docs/DECISIONS.md`. Do not fight the generator.
- Keep `schema.prisma` formatted (`prisma format`) and the migration committed.

## Research notes

The field-by-field spec: `docs/DATA_MODEL.md`. Prisma-from-Python specifics: `docs/research/00-versions.md` §4.

Write down here anything surprising about how prisma-client-py handles enums, `Json`, `Decimal`, `@updatedAt`,
cascading deletes or nested `include` — T-011, T-015 and T-021 all need those answers.

## Work log

## Report

## Manager review
