# T-015 · Post CRUD + client-generated ids + alias snapshot

- status: ready
- quest: Q1
- depends: T-011, T-014
- owner: -
- updated: -
- files: backend/app/api/v1/posts.py, backend/app/schemas/post.py, backend/app/services/posts.py, backend/tests/test_posts.py, docs/API.md

## Goal

The heart of the app: create, read, edit and delete a problem report. A post carries a title, body, area,
category, an author (or an anonymous alias), a blame target and a status — and it must work identically for
a Google user, a pseudonymous user and a ghost.

## Done when

- [ ] `POST /api/v1/posts` creates a post for a Google user, a pseudonymous user and a ghost, and all three
      responses have the same shape.
- [ ] A ghost's `POST` body contains `owner_key` and **no** author identifier; the stored row has
      `authorId = null` and a `ghostOwnerKey` equal to the supplied value.
- [ ] The post id is client-generated: a client-supplied UUID is stored verbatim, and a server-generated one
      also works.
- [ ] `GET /api/v1/posts/{id}` returns the post with its media, counters, area, category, blame target and
      author display — but **never** a `ghostOwnerKey`, an `owner_key` or any hash.
- [ ] `PATCH` and `DELETE` work for the owner (session for registered/pseudonymous, `owner_key` for ghost)
      and return `403 not_owner` for anyone else.
- [ ] `pytest -q` covers create × 3 modes, read, edit, delete, and "another user cannot edit or delete".
- [ ] The API never returns `ghostOwnerKey`, `secretHash` or `tokenHash` in any response or error body.

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

## Work log

## Report

## Manager review
