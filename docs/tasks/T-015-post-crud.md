# T-015 · Post CRUD + client-generated ids + alias snapshot

- status: done
- quest: Q1
- depends: T-011, T-014
- owner: s-20261101-0810
- updated: 2026-11-01 09:07
- files: backend/app/api/v1/posts.py, backend/app/api/v1/router.py, backend/app/api/v1/areas.py, backend/app/schemas/post.py, backend/app/schemas/area.py, backend/app/services/posts.py, backend/tests/test_posts.py, backend/tests/test_areas.py, docs/API.md

## Goal

The heart of the app: create, read, edit and delete a problem report. A post carries a title, body, area,
category, an author (or an anonymous alias), a blame target and a status — and it must work identically for
a Google user, a pseudonymous user and a ghost.

## Done when

- [x] `POST /api/v1/posts` creates a post for a Google user, a pseudonymous user and a ghost, and all three
      responses have the same shape.
- [x] A ghost's `POST` body contains `owner_key` and **no** author identifier; the stored row has
      `authorId = null` and a `ghostOwnerKey` equal to the supplied value.
- [x] The post id is client-generated: a client-supplied UUID is stored verbatim, and a server-generated one
      also works.
- [x] `GET /api/v1/posts/{id}` returns the post with its media, counters, area, category, blame target and
      author display — but **never** a `ghostOwnerKey`, an `owner_key` or any hash.
- [x] `PATCH` and `DELETE` work for the owner (session for registered/pseudonymous, `owner_key` for ghost)
      and return `403 not_owner` for anyone else.
- [x] `pytest -q` covers create × 3 modes, read, edit, delete, and "another user cannot edit or delete".
- [x] The API never returns `ghostOwnerKey`, `secretHash` or `tokenHash` in any response or error body.

## Notes / gotchas

- The response model is an explicit pydantic model, never the raw Prisma row. That is how the leak above is
  prevented — write the response model as an allow-list.
- `alias` is a **snapshot** stored on the post row. A ghost rotates their alias; old posts keep the old one.
- `blameCategory` is restricted to public entities/roles (municipality, contractor, utility, police, school,
  landlord, unknown). Naming a private individual is a policy violation — reject it at the API, not just in
  the UI.
- `status` starts at `OPEN`. The status *workflow* (OPEN → IN_PROGRESS → SOLVED → CLOSED) is T-050; for now
  allow only `OPEN` on create and reject other transitions.
- `lat`/`lng` are optional. Round them to ~100 m (about 3 decimal degrees) **before** storing them.
- Deleting a post must hard-delete its media rows and files — but the media files are created in T-016, so
  leave a clear seam for that (a service function that T-016 fills in).
- Rate limiting is T-037; do not build it here, but do not create an endpoint that can be trivially flooded
  either.

## Research notes

The data model: `docs/DATA_MODEL.md` §3. The endpoint contract: `docs/API.md` §4. The anonymity invariants:
`docs/SECURITY.md` §2.

Record any prisma-client-py quirks you hit with `include`, nested relations and cascade deletes — T-021 needs
the delete cascade.

### Cascade findings (2026-11-01, T-015)

- `Media`, `Comment`, `BlameVote` and `PostView` all declare `onDelete: Cascade` on their `Post` relation:
  deleting the post row removes them at the database level. Verified with a real media row (count 1 → 0).
- `Vote` has **no FK to Post** — it is polymorphic through `(targetType, targetId)`. Deleting a post leaves
  POST votes orphaned unless the delete service removes them explicitly. T-017 (votes) and T-021 (delete
  flows) must add that; T-015 cannot because votes do not exist yet.
- `ModerationRecord`, `Report` and `UserReveal` are also polymorphic (`target_type`/`target_id`), so they
  do not cascade either. T-021 must clean them up explicitly.
- `include={"area": True, "category": True, "author": True, "media": True}` works in one query; relations
  are `None` if not included, so the response mapper guards `area`/`category` and treats `media or []`.

## Work log

- 2026-11-01 s-20261101-0810: implemented POST/GET/PATCH/DELETE with the three identity modes, allow-list
  response model, owner checks, coordinate rounding, the media cascade seam and `GET /areas/{id}`; 15 new
  tests, 56 total pass.

## Report

### 2026-11-01 · worker s-20261101-0810

- changed:
  - `backend/app/schemas/post.py` — `PostCreate` (client UUID, alias/owner_key, blame enum, `status` locked
    to `OPEN`, optional lat/lng, `media_ids` reserved), `PostUpdate`, `OwnerKeyBody`, and the explicit
    allow-list `PostOut`/`MediaOut`/`AuthorOut`.
  - `backend/app/services/posts.py` — coordinate rounding, alias snapshots, owner checks (session id or
    ghost HMAC), `delete_media_files()` seam for T-016, and `post_to_response()`.
  - `backend/app/api/v1/posts.py` — `POST /posts` (201), `GET /posts/{id}`, `PATCH /posts/{id}`,
    `DELETE /posts/{id}` (204). Validates area/category, rejects non-OPEN status, requires ghost
    alias+owner_key, 409 on a duplicated client id.
  - `backend/app/api/v1/router.py` — wire the posts router.
  - `backend/app/api/v1/areas.py` + `backend/app/schemas/area.py` — added `GET /areas/{id}` with
    `post_count` (T-014b's note assigned "one area with post counts" to T-015).
  - `backend/tests/test_posts.py` — 13 tests (3 modes, ghost storage, client/server ids, read allow-list,
    owner-only edit/delete, ghost keys, media cascade, validation, no secret echo).
  - `backend/tests/test_areas.py` — two tests for `GET /areas/{id}` (post count, unknown id 404).
  - `docs/API.md` §4 — full create body, shared response shape, PATCH/DELETE owner_key transport, media note;
    §3 documents the area detail response.
- verified (real output):
  - `python -m pytest -q` → **56 passed** (13 post tests + 2 area-detail tests new).
  - `ruff check .` → all checks passed; `ruff format --check .` → 34 files already formatted.
  - Live ghost smoke against the running API: `POST` → 201 with `author=null`, `lat=28.631`; `GET` →
    `pincode=110019`, `media=[]`, no forbidden key in the body; `DELETE` with the right `owner_key` → 204,
    then `GET` → 404. Live `GET /areas/{id}` for 110019 → `post_count: 0`; unknown id → 404.
  - `/openapi.json` exposes `/api/v1/posts` and `/api/v1/posts/{post_id}`; `PostOut` keys contain no secrets.
- issues / notes:
  - `media_ids` is accepted but non-empty returns `422 media_not_supported`; the schema requires `postId` on
    `Media`, so T-016 must decide the upload/attach flow (likely create media after the post). Documented.
  - `DELETE` of a post with votes would orphan `Vote` rows (no FK); recorded in the research notes for
    T-017/T-021.
  - Ghost `expires_at` stays null; expiry is T-040.
  - The API was restarted to load the new router; the live smoke post was deleted and left the DB clean.
- next: T-016 (media upload) is now unblocked; T-017 votes and T-018 comments depend on this.

## Manager review

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**. I drove the whole CRUD surface myself against the running API — all three identity
  modes, the ownership rules, the leak checks and the stored row — and re-ran the suite. One long-standing
  documentation gap (`owner_key` encoding) I closed myself, since this task owns the post contract.
- checked (re-run by the manager; nothing taken from the worker's report):
  - **Create as a pseudonymous user.** `POST /auth/pseudo` → alias + token; `POST /posts` → **201**, the
    response has the allow-list shape (`is_anonymous: true`, `author: {id, alias}`, `alias` = the account
    alias), `status: OPEN`, `area`/`category` embedded.
  - **Create as a ghost with a client-generated id.** `POST /posts` with `id: 0397f825-…` → **201** and the
    id came back **verbatim**; `author: null`, `alias: "Neighbor_mgr7"` (the client alias is snapshotted on
    the row), `is_anonymous: true`, `lat 28.631234 → 28.631`, `lng 77.071234 → 77.071` (rounded to ~100 m),
    `blame_category: MUNICIPALITY` + `blame_label: MCD`.
  - **What the database really stores** (read straight from Postgres through the Prisma client):
    `authorId = None`, `ghostOwnerKey = KuKeZcKXwA4w5U3TZBDV_Mk8SK4U-pemWTvt9MQsR_c` (exactly the string
    the client sent), `alias = Neighbor_insp`, `isAnonymous = True`, `status = OPEN`, `expiresAt = None`.
    No author row, no session row, no hash of the secret.
  - **Nothing leaks.** The raw `GET /posts/{id}` body contains none of `ghostOwnerKey`, `ghost_owner_key`,
    `owner_key`, `secretHash`, `tokenHash` — and not the actual `owner_key` value I sent. The OpenAPI
    `PostOut` schema has 24 allow-listed properties and no field whose name contains ghost/owner/secret/
    token/hash. The error bodies are clean too (`403 not_owner` → `{"error":{"code":"not_owner",…}}`).
  - **Ownership.** Ghost PATCH with a wrong key → **403 `not_owner`**, with the right key → **200**. Ghost
    DELETE with a wrong key → **403**, with the right key → **204**, then `GET` → **404**. With two
    pseudonymous identities: the other user's PATCH → **403**, DELETE → **403**, the owner's DELETE → **204**,
    GET → **404**.
  - **Duplicate client id** → **409 `conflict`**.
  - **Validation** → 422 in all six cases I tried: `status: "IN_PROGRESS"`, `blame_category: "INDIVIDUAL"`
    (private individuals are not an allowed enum value), `blame_label` without a category, non-empty
    `media_ids` (422 `media_not_supported`), unknown `area_id` (422 `area_required`), unknown `category_id`.
    A ghost create without `alias` → 422, without `owner_key` → 422.
  - **`GET /areas/{id}` now exists** — this closes the gap I flagged in the T-014 review: `post_count: 1`
    while the post was alive, `0` after deleting it, and `404` for an unknown id.
  - **Tests.** `docker compose exec api python -m pytest -q` → `56 passed, 1 warning` (the pre-existing
    Starlette `httpx` deprecation). The new file covers create × 3 modes, the ghost row, client/server ids,
    the read allow-list, owner-only edit/delete, the media cascade (1 → 0) and the no-echo validation error.
  - **Lint / format.** `ruff check .` → `All checks passed!`; `ruff format --check .` → `34 files already
    formatted`.
  - **OpenAPI.** `/api/v1/posts` (POST) and `/api/v1/posts/{post_id}` (GET/PATCH/DELETE) are exposed.
  - **I left the database clean:** 0 posts, 103 areas, 549 aliases; I deleted the three pseudonymous
    identities my own smoke tests created (the one remaining user, `Neighbor_jqr8`, predates this session).
- correction I made (manager owns the docs):
  - `docs/API.md` §4 still described `owner_key` as `"HMAC(postKey, id)"` with no encoding — the note I have
    carried since T-012 and again in the T-014 review. This task owns the post contract, so I pinned it:
    **base64url** (RFC 4648 §5, no `=` padding), the secret is the HMAC **key** and the post id the
    **message**, the string travels in the JSON **body** of POST/PATCH/DELETE (never a header), and the
    server compares it byte-for-byte in constant time. The web client (T-012) already sends base64url, so the
    two now agree on the wire.
- notes (no action required, carried forward):
  - **Every post is created with `moderationState: CLEAN`** — correct for now (it is the only non-flagged
    value in the enum), but `docs/MODERATION.md` says the post is created with its state already set, so
    T-030/T-035 must decide the initial state and the worker path.
  - `GET /posts/{id}` returns a post regardless of `moderationState`; filtering `FLAGGED`/`HIDDEN` content
    belongs to T-035.
  - A ghost PATCH/DELETE **without** an `owner_key` returns `403 not_owner`, while the create path returns
    `422 validation_error` for a missing key. Both are safe; the inconsistency is cosmetic.
  - **The ghost's alias is client-chosen** and only pattern-checked (`^[A-Za-z0-9_]{3,32}$`), so a ghost can
    claim `MCDelhi` or `Admin`. This is the same impersonation gap the T-011 review flagged for pseudonymous
    aliases; it belongs with T-037 (moderation / reserved aliases), not with this task.
  - The worker's own cascade research is worth keeping: `Media`, `Comment`, `BlameVote` and `PostView` have
    `onDelete: Cascade` on their Post relation, but **`Vote`, `Report`, `ModerationRecord` and `UserReveal`
    are polymorphic** (no FK to Post) — deleting a post will orphan them. T-017 (votes) and T-021 (delete
    flows) must remove those rows explicitly.
  - `media_ids` is accepted but a non-empty list is rejected; the `Media` row requires `postId`, so T-016 has
    to decide the order (upload after create, then attach) or change the schema.
  - `expires_at` stays null; ghost expiry is T-040.
  - The frontend's generated `types.ts` is still stale (only `/api/v1/health`). Re-run `npm run api:types`
    **on the host** before T-020 consumes the post endpoints.
- next: **T-016** (media upload + blurHash + signed URLs) is unblocked; T-017 (votes) and T-018 (comments)
  depend on this task, and T-021 needs the cascade notes above.
