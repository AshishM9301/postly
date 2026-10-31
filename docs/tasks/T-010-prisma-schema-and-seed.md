# T-010 · Prisma schema (17 models) + migration + seed categories

- status: done
- quest: Q1
- depends: T-003
- owner: s-20261031-1134
- updated: 2026-10-31T13:52
- files: backend/prisma/schema.prisma, backend/prisma/migrations/**, backend/scripts/seed_categories.py, backend/tests/test_schema.py, docs/DATA_MODEL.md, docs/research/00-versions.md, apps/web/src/generated/prisma/**, apps/web/eslint.config.js

## Goal

Write the real data model. `schema.prisma` becomes the single source of truth for the whole app: every later
task (auth, posts, media, votes, moderation, notifications) codes against these models, and the TypeScript
Prisma client for the frontend types is generated from the same file. Replace the probe schema from T-001.

## Done when

- [x] `backend/prisma/schema.prisma` contains all **17** models documented in `docs/DATA_MODEL.md` (the
      task's "19" came from a stale doc header; the doc has always listed 17 tables — see the report),
      7 enums and the documented indexes — matching `docs/DATA_MODEL.md` field for field.
- [x] `python -m prisma migrate dev --name init` applies cleanly on an empty database.
- [x] `python -m prisma migrate status` reports the database is in sync.
- [x] `python -m prisma generate` succeeds and the generated models expose every field in the docs.
- [x] `python scripts/seed_categories.py` inserts the 9 categories and is idempotent (running it twice
      leaves 9 rows).
- [x] `pytest -q` includes a test that creates and reads one row of at least three different models
      (Post, Comment, Vote) through the generated client.
- [x] The frontend can generate its TS types from the same schema (`prisma generate` with the
      `prisma-client-js` generator, **types only** — no database access from the browser). **Amended
      2026-10-31 by the manager:** the output is **not committed** — `apps/web/src/generated/` is
      **gitignored** and the generation recipe lives in `docs/research/00-versions.md` §4. The web app
      codes against the OpenAPI spec, not the database schema, so these declarations are never a build
      input and must never be imported (see the manager review for the reasoning).

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

### Findings (2026-10-31, s-20261031-1134)

- **Model count:** `docs/DATA_MODEL.md` lists **17 models** (User, Session, Area, Category, Post, Media,
  Comment, Vote, BlameVote, Follow, AreaFollow, ModerationRecord, UserReveal, Report, Notification,
  PushSubscription, PostView) and **7 enums**. Its header (and this task's title) said "19" — stale. The 7th
  enum is `ModerationStatus` (`ModerationRecord.status`: PENDING FLAGGED CONFIRMED REJECTED APPROVED), which
  was described inline but missing from §7. Both doc errors were corrected in this task.
- **prisma-client-py 0.15.0 behaviour:** enums are `StrEnum`s in `prisma.enums` (`PostStatus.OPEN` is the
  string `"OPEN"`), `Json`/`Json?` map to `JSONB` with no workaround, `@updatedAt` is handled by the
  client, `onDelete: Cascade` is a real Postgres FK, and nested `include={"comments": True}` works.
  Relation fields appear in `model_fields` alongside the documented scalar fields; `Decimal` is unused.
- **Migration creation on this bind mount:** `./backend` is root-owned but the container runs as `appuser`
  (uid 10001), so `prisma migrate dev` cannot create `migrations/...` (`Permission denied`). The working
  sequence was:
  `docker compose exec -u root -T api python -m prisma migrate dev --name init --skip-generate`
  then `docker compose exec -T api python -m prisma generate` (as `appuser`).
  The T-001 probe migration was removed and the public schema dropped first; only the SpikeRow probe existed.
- **Frontend TS types (item 7):** `prisma-client-js` requires npm `@prisma/client`, which AD-004 forbids
  adding to the project. Working workaround: generate in a throwaway `/tmp` project inside the container,
  pinning **exact** `prisma@5.19.0` + `@prisma/client@5.19.0`, call the bundled Prisma CLI 5.19.0 directly
  with `--generator tsclient --no-engine`, then copy only `*.d.ts` to `apps/web/src/generated/prisma`.
  - Do **not** call `python -m prisma generate` from that temp project: the Python wrapper prefers the
    temp `node_modules/prisma` (auto-installed 5.17.0) and overwrites the Python client with the 5.17.0
    engine — this produced `MismatchedVersionsError` (expected `5fe218...`, got `393aa...`). Running
    `python -m prisma generate` from `/app` restored the 5.19.0 client.
  - `--no-engine` is mandatory for a types-only artifact; without it a 16 MB native query engine is emitted.
  - Committed files: `index.d.ts`, `default.d.ts`, `edge.d.ts`, `wasm.d.ts`, `runtime/library.d.ts`,
    `runtime/index-browser.d.ts` (~1.3 MB). No JS runtime, no engine, no `@prisma/client` dependency.
  - `apps/web/eslint.config.js` ignores `src/generated`; `tsc --noEmit` still typechecks the declarations.
- **Seed:** `upsert` on the unique `slug`; a second run still reports 9.
- **Test:** `asyncio.run` around one Prisma client; nested `connect` for relations; cleanup by deleting the
  user (cascades post/comment/vote), then the test area and category.

### Addendum (2026-10-31, manager s-20261031-1352)

- **`prisma migrate dev` works fine as `appuser` when it has nothing to write.** The permission problem only
  appears when a *new* migration folder has to be created. On an in-sync database it prints `Already in sync,
  no schema change or pending migration was found.` and exits 0.
- **`prisma migrate diff` is the cleanest drift check:** `python -m prisma migrate diff --from-url
  <DATABASE_URL> --to-schema-datamodel prisma/schema.prisma --exit-code` → `No difference detected.` (exit 0)
  when the migrations match the schema.
- **The Python wrapper's `python -m prisma` CLI accepts the same flags as the Prisma CLI**
  (`migrate deploy|dev|status|diff`, `generate`, `validate`, `format`) — use them instead of hunting for a
  bundled `prisma` binary.
- **`prisma.models` is a module, not a list.** To enumerate the generated models use
  `[n for n, o in vars(prisma.models).items() if hasattr(o, "model_fields")]` — that yields the 17 models
  plus pydantic's `BaseModel`, and `model_fields` is the reliable place to look for a model's fields.
- **`prisma format` is idempotent** — hash the schema before and after to prove it is formatted.

## Work log

- 2026-10-31 s-20261031-1134: replaced the probe schema with the 17 documented models + 7 enums; formatted and
  validated it; removed the probe migration and generated `20261031060611_init` on an empty database; added
  the idempotent category seed and the Post/Comment/Vote round-trip test; generated the frontend type
  declarations (types only); verified migrations, generate, seed, tests, ruff, frontend typecheck/lint/build.

## Report

### 2026-10-31 · worker s-20261031-1134

- changed:
  - `backend/prisma/schema.prisma` — replaced the T-001 probe with the 17 documented models, 7 enums, all
    documented indexes and snake_case column/table mappings.
  - `backend/prisma/migrations/20261031060611_init/migration.sql` — the real init migration; the
    `20261030125856_init_probe` folder was removed.
  - `backend/scripts/seed_categories.py` — idempotent upsert of the 9 categories.
  - `backend/tests/test_schema.py` — round-trips Post + Comment + Vote through the generated client.
  - `docs/DATA_MODEL.md` — corrected 19 → 17 tables and documented the 7th enum (`ModerationStatus`).
  - `apps/web/src/generated/prisma/*.d.ts` — Prisma-derived type declarations (types only) for the frontend.
  - `apps/web/eslint.config.js` — ignores the generated declarations; `tsc` still checks them.
  - `docs/research/00-versions.md` §4 — recorded the migration/typegen findings.
- verified (all inside the compose stack unless noted):
  - `docker compose exec -T api python -m prisma format` → `Formatted prisma/schema.prisma`;
    `prisma validate` → `The schema at prisma/schema.prisma is valid`.
  - Dropped the public schema (only the SpikeRow probe existed), then
    `docker compose exec -u root -T api python -m prisma migrate dev --name init --skip-generate` →
    `Applying migration 20261031060611_init` and `Your database is now in sync with your schema.`
  - `python -m prisma generate` → `Generated Prisma Client Python (v0.15.0)`.
  - `python -m prisma migrate status` → `1 migration found... Database schema is up to date!`.
  - Generated models expose the documented fields: 17 models returned by `prisma.models`; e.g. `Post` has
    30 fields (`ghostOwnerKey`, `blameVoteCount`, `moderationState`, `expiresAt`, …), `Comment` 16,
    `Vote` 7, `User` 27 (including relation fields).
  - `python scripts/seed_categories.py` twice → `seed_categories: 9 categories present` both times;
    `SELECT count(*)` → `9`, slugs `pothole,water,garbage,electricity,roads,streetlight,noise,drainage,other`.
  - `python -m pytest -q` → `2 passed, 1 warning`.
  - `ruff check .` → `All checks passed!`; `ruff format --check .` → `14 files already formatted`.
  - Frontend: `npm run typecheck` exit 0, `npm run lint` → `✔ No ESLint warnings or errors`,
    `npm run build` → `✓ Compiled successfully`, `✓ Generating static pages (3/3)`.
  - TS client generated with Prisma Client **v5.19.0** (`--no-engine`); six `.d.ts` files committed under
    `apps/web/src/generated/prisma` (~1.3 MB). No JS runtime, no native engine, no `@prisma/client` added
    to any `package.json`.
- issues:
  - **Count discrepancy:** the task and the `DATA_MODEL.md` header said 19 models, but the document has
    always listed 17. I implemented exactly the 17 documented models rather than inventing two, and
    corrected the doc header. The manager should confirm this reading.
  - **Migration permission:** the bind-mounted `backend/` is root-owned while the api container runs as
    `appuser`, so `migrate dev` had to run as root (`--skip-generate`), with a normal `prisma generate`
    as `appuser` afterwards.
  - **TS typegen vs AD-004:** `prisma-client-js` needs npm `@prisma/client`, which AD-004 forbids in the
    project. Generation was done in a throwaway `/tmp` project pinned to 5.19.0 and only type declarations
    were copied. An attempted wrapper run in that temp dir auto-installed Prisma 5.17.0 and overwrote the
    Python client (engine mismatch); regenerating from `/app` restored 5.19.0 and all tests pass.
  - `apps/web/src/generated` is excluded from ESLint (generated Prisma declarations use `any`/index
    signatures that fail the strict rules) but still typechecked by `tsc`.
- next: T-011 (auth) can code against `User` / `Session`; T-013 seeds `Area`.

## Manager review

### 2026-10-31 · manager s-20261031-1352

- verdict: **accepted**. T-010 is `done`; the board row is `[x]`.
- checked (every item re-run by the manager from the current tree — nothing taken from the report):
  - **Done-when #1 — schema vs `docs/DATA_MODEL.md`.** All **17** documented models are present
    (`User, Session, Area, Category, Post, Media, Comment, Vote, BlameVote, Follow, AreaFollow,
    ModerationRecord, UserReveal, Report, Notification, PushSubscription, PostView`), all **7** enums with
    exactly the documented members, and every `@@unique` the doc lists is in the schema
    (`users.alias`, `users.firebaseUid`, `sessions.tokenHash`, `areas.pincode`, `categories.slug`,
    `votes(targetType,targetId,voterKey)`, `blameVotes(postId,voterKey)`, `follows(followerId,followingId)`,
    `areaFollows(userId,areaId)`, `userReveals(userId,targetType,targetId)`, `postViews(postId,viewerKey)`,
    `pushSubscriptions.endpoint`). All four documented `Post` indexes are there, plus `posts.ghostOwnerKey`
    and `comments.ghostOwnerKey` (required by this task's own gotcha for the ghost purge sweep). The extra
    indexes the schema adds (`sessions.userId`, `votes.voterId`, `comments.parentId`, `media.postId`,
    `follows.followingId`, `areaFollows.areaId`, `blameVotes.voterId`, `moderationRecords(status)`,
    `moderationRecords(targetType,targetId)`, `reports(status)`, `reports(targetType,targetId)`,
    `notifications(userId,isRead,createdAt)`, `pushSubscriptions.userId`) are all FK/lookup columns — no
    contradiction with the doc. `Vote.voterKey` is non-nullable `String` ✓. `Post.id` / `Comment.id` are
    `@default(uuid())` ✓. `Prisma format` is a **no-op** on the file (SHA-256 identical before/after) → the
    schema is formatted as the task requires. `prisma validate` → `The schema at prisma/schema.prisma is
    valid 🚀`.
  - **The "19 vs 17" count — the worker's reading is correct.** `git show HEAD:docs/DATA_MODEL.md` proves the
    doc has **always** listed exactly **17** `###` model headings (User → PostView) and **6** enums; the
    `19 tables` header was simply stale. `git diff docs/DATA_MODEL.md` shows the worker changed only the
    header (19 → 17) and added the 7th enum to §7 (`ModerationStatus`, which the doc described inline in
    `ModerationRecord.status` but never listed). No model was invented and none was deleted. The task title
    stays "19 models" — that is the task's own stale wording, not a defect in the work.
  - **Done-when #2 — applies cleanly on an empty database.** I did **not** trust the "I dropped the public
    schema" evidence; I created a brand-new database and migrated into it:
    `CREATE DATABASE postly_verify` → `python -m prisma migrate deploy` →
    `Applying migration 20261031060611_init` / `All migrations have been successfully applied.` (exit 0).
    Then `python -m prisma migrate dev --name init` against that same empty DB →
    `Already in sync, no schema change or pending migration was found.` (exit 0) and **no** new migration
    folder was created. The fresh DB has **18** base tables (17 models + `_prisma_migrations`) and **7** enum
    types. `prisma migrate diff --from-url <fresh> --to-schema-datamodel prisma/schema.prisma --exit-code` →
    `No difference detected.` (exit 0) → no drift between schema and migrations. The verify DB was dropped
    afterwards.
  - **Done-when #3 — `migrate status`.** `python -m prisma migrate status` → `1 migration found in
    prisma/migrations` / `Database schema is up to date!` (exit 0). The main DB's `_prisma_migrations` holds
    exactly one row (`20261031060611_init`, finished, not rolled back) — the T-001 probe row is gone, and
    no `spike_rows` table survives.
  - **Done-when #4 — `prisma generate` + every documented field.** `prisma generate` (run by `migrate dev`
    above) → `✔ Generated Prisma Client Python (v0.15.0)`. A script that compares `prisma.models.*` against
    the field lists in `docs/DATA_MODEL.md` reported **PROBLEMS: 0** — every documented field of every one of
    the 17 models is present (`missing=NONE` for all; the 18th class in the module is pydantic's
    `BaseModel`, not a model). The `prisma-client-py 0.15.0` engine mismatch the worker hit is gone — the
    client is regenerated from `/app` and the whole suite runs against it.
  - **Done-when #5 — seed idempotency.** `python scripts/seed_categories.py` run **twice** →
    `seed_categories: 9 categories present` both times, exit 0. `SELECT count(*) FROM categories` → **9**;
    slugs in sort order → `pothole,water,garbage,electricity,roads,streetlight,noise,drainage,other` —
    exactly the 9 the doc names.
  - **Done-when #6 — the round-trip test.** `backend/tests/test_schema.py` creates a User, an Area, a
    Category, a **Post**, a **Comment** and a **Vote**, reads them back through the generated client
    (including a nested `include={"author","area","category","comments"}`) and asserts every value.
    `python -m pytest -q` → `2 passed, 1 warning` (the other test is T-003's health test). The test cleans up
    after itself: the live DB shows `users=0`, `posts=0`, `categories=9`.
  - **Done-when #7 — frontend TS types.** `apps/web/src/generated/prisma/` holds **6 `.d.ts` files and nothing
    else** (`index.d.ts` 1165 KB, `runtime/library.d.ts` 113 KB, `runtime/index-browser.d.ts` 12 KB, plus
    three empty stubs) → **types only**, no JS runtime, no native query engine. The types are the standard
    Prisma Client TS output for **this** schema: `index.d.ts` exports exactly the 17 model types and the 7
    enum types, and the `Post` scalars are the schema's (`ghostOwnerKey: string | null`,
    `status: $Enums.PostStatus | null`, `blameCategory: $Enums.BlameCategory | null`, …).
    **Proof that the browser cannot reach the database:** I added a temporary route that did
    `import { PrismaClient } from "~/generated/prisma"; new PrismaClient()` → `npm run build` fails with
    `Module not found: Can't resolve '~/generated/prisma'` (exit 1). The "types only" rule is enforced by the
    build, not by convention. Probe deleted afterwards; `npm run typecheck` → exit 0, `npm run lint` →
    `✔ No ESLint warnings or errors`, `npm run build` → `✓ Compiled successfully` (exit 0) with the
    declarations present. `apps/web/eslint.config.js` ignores `src/generated` (the declarations use `any` /
    index signatures that the strict rules reject) while `tsc` still type-checks them.
    **No npm Prisma anywhere:** `prisma` / `@prisma/client` appear in **no** `package.json` (consistent with
    AD-004), and `DATABASE_URL` appears **nowhere** in the frontend.
  - Backend housekeeping: `ruff check .` → `All checks passed!`; `ruff format --check .` →
    `14 files already formatted`.
  - **Cleanup verified.** The verify database was dropped, the temporary Prisma probe route and the stale
    `.next/types/validator.ts` it produced were removed, the dev/probe artefacts are gone, and
    `git status --porcelain` is identical to the state before this session. The stack is healthy
    (`db`, `api`, `web` all `Up (healthy)`).
- notes (no action required, carried forward):
  - **Manager decision (2026-10-31, after the review was written): the generated TS output is NOT
    committed.** The done-when originally said "output committed" and my review above said the manager
    should stage it — that is **withdrawn**. `apps/web/src/generated/` is now **gitignored** (and
    `.dockerignore`d), and `apps/web/.dockerignore` excludes it from the image build. Reason: the web app's
    contract is the **OpenAPI spec** (`apps/web/src/lib/api/types.ts`), not the database schema. Committing
    ~1.3 MB of vendored Prisma declarations would create a second source of truth that goes stale silently
    the moment `schema.prisma` changes, it is generated third-party code, and **nothing imports it**
    (verified: 0 imports of `generated/prisma` anywhere under `apps/web/src`). The regeneration recipe is
    documented in `docs/research/00-versions.md` §4 and in this task's Research notes. The local copy may
    stay on a developer's disk — it is ignored and unused; a fresh clone does not have it and must not
    need it.
  - **The TS types cannot be regenerated from the repo as it stands.** `backend/prisma/schema.prisma` has
    only the `prisma-client-py` generator block; the `prisma-client-js` output was produced in a throwaway
    `/tmp` project (pinned `prisma@5.19.0` + `@prisma/client@5.19.0`, `--no-engine`) because AD-004 forbids
    npm Prisma. The recipe is prose in this task's Research notes and in `docs/research/00-versions.md` §4,
    but **no script** reproduces it. Worth a small follow-up task that turns the recipe into a script — but
    only if a later task actually needs DB-shaped types in the frontend (T-020 may not; the OpenAPI types
    are the right input there).
  - **Deleting a post does not remove its votes, reveals or reports at the DB level.** `votes`,
    `user_reveals` and `reports` have a loose `targetId` (they can point at a post, a comment or media), so
    there is no FK to cascade from `posts`. The schema only guarantees the cascade for `media`, `comments`,
    `blame_votes` and `post_views`. `docs/DATA_MODEL.md` §8 promises the rest, so **T-021 (delete flows)
    must delete those rows in application code** — orphaned votes are invisible otherwise.
  - `posts.area_id` / `posts.category_id` are `ON DELETE RESTRICT` (Prisma's default for a required
    relation): an Area or Category that still has posts **cannot** be deleted. T-013 must not delete seeded
    areas casually.
  - `comments.parent_id` is `ON DELETE CASCADE`: deleting a comment deletes its replies. That is a product
    decision nobody has written down — T-018 (threads) should confirm it is intended.
  - `posts.updated_at` has no SQL default (Prisma's `@updatedAt` is applied client-side). A raw-SQL insert
    must supply it.
  - `migrate dev` cannot write `prisma/migrations/` as `appuser` (the bind mount is root-owned). Run
    migration creation as root and `prisma generate` as the app user, as documented.
- next: **T-010 accepted.** The next task with all dependencies done is **T-011** (auth: Google + pseudonymous
  + ghost + session middleware) — it can start as soon as T-010's changes are committed.
