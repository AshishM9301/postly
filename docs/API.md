# API CONTRACT

Base URL `/api/v1`. JSON in, JSON out. This is the contract a future Kotlin / Swift client codes against,
so treat changes here as breaking.

## 1. Conventions

**Envelope**
```json
{ "data": { ... }, "meta": { "cursor": "opaque", "has_more": true } }
```
Errors:
```json
{ "error": { "code": "post_not_found", "message": "No such post", "details": {} } }
```

**Auth** — `Authorization: Bearer <token>`

| Mode | Token |
|---|---|
| Google | Firebase ID token (verified server-side with `firebase-admin`) |
| Pseudonymous | our opaque session token (`postly_sess_<random>`) |
| Ghost | no token. Ownership is proven per-row by sending `owner_key` in the body/header |

Public endpoints (no auth): `GET /health`, `GET /categories`, `GET /areas/search`, `GET /feed/*`,
`GET /posts/{id}`, `POST /auth/*`.

**Pagination** — cursor based. `?limit=20&cursor=<opaque>`. Cursors are opaque to clients.

**Timestamps** — ISO-8601 UTC strings.

**IDs** — UUID strings. Clients may generate their own (required for ghost posts).

## 2. Auth

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/auth/google` | body: `{ id_token }` | exchange a Firebase ID token for a Postly session |
| POST | `/auth/pseudo` | body: `{ alias?, secret, expiry_days? }` | create/reopen a pseudonymous identity |
| POST | `/auth/rotate-alias` | yes | new alias, same identity |
| GET | `/me` | no (ghost) / yes | current principal — see below |
| PATCH | `/me` | yes | edit profile / alias / ghost expiry preference |
| DELETE | `/me` | yes (+ `secret` for pseudonymous) | **hard delete** of the account and everything |
| POST | `/ghost/purge` | body: `{ session_key }` | delete every ghost post/comment/vote made with that key |
| GET | `/me/keys/export` | yes (ghost) | download the local key vault as JSON |

`/auth/pseudo` response:
```json
{ "data": { "alias": "Neighbor_7f3a", "token": "postly_sess_…", "mode": "pseudonymous" } }
```

`GET /me` needs no token: a request with **no** `Authorization` header is a **ghost** caller and gets the
empty ghost principal back (there is no ghost user row to look up):

```json
{ "data": { "mode": "ghost", "alias": null, "user_id": null, "expiry_days": 90, "is_admin": false } }
```

With a `Bearer` session token it resolves the session and returns `mode: "google"` or
`mode: "pseudonymous"` with the alias. A malformed, unknown, revoked or expired token is `401
unauthorized`.

## 3. Areas & categories

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/areas/search?q=&limit=` | no | search areas by name / district / PIN code |
| GET | `/areas/detect?lat=&lng=` | no | nearest area for a coordinate (Haversine) |
| GET | `/areas/{id}` | no | one area with post counts |
| GET | `/categories` | no | all categories |

`/areas/search`:

- a **six-digit** `q` is treated as an exact PIN code (one result or none); it never falls back to a name
  match.
- anything else is a case-insensitive substring match on the area's display `name`, its stored aliases
  (every suffix-stripped office name belonging to that PIN, e.g. `Karol Bagh` for `110005`), **or** its
  `district`.
- `%`, `_` and `\` are matched as **literal characters**, not LIKE wildcards (`?q=%` returns `[]`).
- `limit` defaults to `10` and is capped at `25`. Results are ordered by `pincode`.

```json
{ "data": [
  { "id": "…", "pincode": "110058", "name": "Janakpuri A 3",
    "district": "WEST", "lat": 28.6241111, "lng": 77.0793611 }
] }
```

`/areas/detect` (`lat` −90..90, `lng` −180..180):

- Always returns the **nearest active area**, even for a coordinate outside Delhi — there is no distance
  cut-off (the client can judge the distance). `404 area_not_found` only when the table has no active
  areas.
- `distance_meters` is an integer: Haversine on a 6,371,000 m sphere.
- The candidate list is bounded and cached in-process for 60 seconds (103 rows today).

```json
{ "data": { "id": "…", "pincode": "110019", "name": "Alaknanda",
             "district": "SOUTH EAST", "lat": 28.5256389, "lng": 77.2541667,
             "distance_meters": 412 } }
```

`/areas/{id}` returns one active area plus its post count (`404 area_not_found` otherwise):

```json
{ "data": { "id": "…", "pincode": "110019", "name": "Alaknanda",
             "district": "SOUTH EAST", "lat": 28.5256389, "lng": 77.2541667,
             "post_count": 0 } }
```

`/categories` returns every category ordered by `sort_order`:

```json
{ "data": [
  { "id": "…", "name": "Pothole", "slug": "pothole",
    "icon": "traffic-cone", "color": "#f97316", "sort_order": 1 }
] }
```

## 4. Posts

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/posts` | yes | create. Ghost users send `owner_key`; ids are client-generated |
| GET | `/posts/{id}` | no | one post + comments preview |
| PATCH | `/posts/{id}` | owner | edit body/title (ghost: `owner_key`) |
| DELETE | `/posts/{id}` | owner | **hard delete** (ghost: `owner_key`) |
| PATCH | `/posts/{id}/status` | yes | `OPEN` → `IN_PROGRESS` → `SOLVED` → `CLOSED` |
| POST | `/posts/{id}/blame` | yes | vote on the blame target |
| POST | `/posts/{id}/removal-request` | no | moderator-assisted removal (lost key path) |
| POST | `/posts/{id}/views` | no | view counter (idempotent per viewer key) |

Create body (`201 Created`):
```json
{
  "id": "3f2c…uuid",                    // optional; clients (ghosts) may generate it
  "title": "Deep pothole near the gate",
  "body": "Three bikes have crashed here this week.",
  "area_id": "…",
  "category_id": "…",
  "alias": "Neighbor_7f3a",             // ghost only, required — stored as a snapshot
  "owner_key": "HMAC(postKey, id)",     // ghost only, required — see below for the exact encoding
  "blame_category": "MUNICIPALITY",     // optional enum; private individuals are not allowed
  "blame_label": "MCD",                 // optional, requires blame_category
  "status": "OPEN",                     // only OPEN accepted on create (workflow is T-050)
  "lat": 28.63, "lng": 77.07,           // optional, rounded to 3 decimals server-side
  "media_ids": []                       // reserved for T-016; non-empty currently returns 422
}
```

The create/read/edit response is the same explicit allow-list for all three modes:
```json
{ "data": {
  "id": "…", "alias": "Neighbor_7f3a", "is_anonymous": true,
  "title": "…", "body": "…", "status": "OPEN", "moderation_state": "CLEAN",
  "blame_category": "MUNICIPALITY", "blame_label": "MCD", "blame_vote_count": 0,
  "upvote_count": 0, "downvote_count": 0, "comment_count": 0, "view_count": 0,
  "lat": 28.631, "lng": 77.071, "expires_at": null,
  "created_at": "…", "updated_at": "…",
  "area": { "id": "…", "pincode": "110019", "name": "…", "district": "…", "lat": 0, "lng": 0 },
  "category": { "id": "…", "name": "Pothole", "slug": "pothole", "icon": "…", "color": "…",
                "sort_order": 1 },
  "author": { "id": "…", "alias": "Neighbor_7f3a" },   // null for ghost content
  "media": []
} }
```

- `owner_key` is `base64url(HMAC-SHA256(postKey, postId))` — RFC 4648 §5 base64url (`A-Za-z0-9-_`),
  **no `=` padding**. The secret is the HMAC **key**, the post id is the **message**. The server stores the
  string opaquely and compares it byte-for-byte in constant time, so client and server must agree on the
  encoding — the web client (`apps/web/src/lib/ghost/crypto.ts`) sends base64url. It travels in the JSON
  **body** of `POST`, `PATCH` and `DELETE`, never in a header.
- `PATCH /posts/{id}` body: `{ "title"?: string, "body"?: string, "owner_key"?: string }` — at least
  one of title/body. Ghosts must include `owner_key`.
- `DELETE /posts/{id}` body for ghosts: `{ "owner_key": "…" }`; returns `204 No Content`. DB rows cascade,
  files are removed by the media service (T-016).
- None of these responses ever contain `ghostOwnerKey`, `secretHash` or `tokenHash`; the response model is
  an allow-list.
- `403 not_owner` for a wrong session/`owner_key`, `404 post_not_found` for an unknown id.


## 5. Comments

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/posts/{id}/comments` | no | flat thread (rebuild the tree from `parent_id`) |
| POST | `/posts/{id}/comments` | yes (+ ghost `owner_key`) | top-level comment or reply |
| PATCH | `/comments/{id}` | owner | edit body |
| DELETE | `/comments/{id}` | owner | delete (replies are kept) |
| GET | `/comments/{id}/replies` | no | not implemented; use the flat thread |

Create body:
```json
{
  "id": "uuid (optional; ghosts generate it)",
  "body": "The contractor left the rubble here.",
  "parent_id": "…",                    // omit for a top-level comment
  "alias": "Neighbor_7f3a",            // ghost only, required
  "owner_key": "HMAC(commentKey, id)"  // ghost only, required
}
```

- `depth` is computed on create (`parent.depth + 1`, top level `0`) and **capped at 3**; a deeper reply
  returns `422 max_depth_exceeded`.
- `GET /posts/{id}/comments` is oldest-first (`created_at`, then `id`), cursor-paginated:
  `?limit=20&cursor=<last id>`. The response is `{ "data": [CommentOut…], "meta": { "cursor": …, "has_more": … } }`.
  Each `CommentOut` carries `id`, `post_id`, `parent_id`, `alias`, `body`, `depth`, counters, timestamps and
  `author` (`null` for ghosts). Ghost keys never appear.
- **DELETE keeps replies**: the direct children are promoted to top level (`parent_id = null`) and their
  subtree's depth is shifted up so promoted roots are `depth = 0`. Only the deleted comment decrements the
  post's `comment_count`; replies remain counted.
- Comment votes use `PUT /votes/COMMENT/{id}` from §6; the comment's own counters are updated.

## 6. Votes

| Method | Path | Auth | Purpose |
|---|---|---|---|
| PUT | `/votes/{target_type}/{target_id}` | yes (+ ghost `voter_key`) | cast or change a vote |
| DELETE | `/votes/{target_type}/{target_id}` | yes (+ ghost `voter_key`) | remove your vote |
| GET | `/me/votes` | yes | your votes — **not implemented yet** (planned) |

`target_type` is `POST` or `COMMENT` (case-insensitive). `BLAME` is rejected here — blame votes use
`POST /posts/{id}/blame` (T-050).

PUT body:
```json
{ "value": 1, "voter_key": "a:HMAC-sessionKey-targetId" }
```
`voter_key` is **required for ghosts only** and must be `a:` + the base64url HMAC-SHA256 of the target id
under the client-held session key (the server never sees the session key). Registered/pseudonymous voters
are keyed server-side as `u:<userId>`; any `voter_key` they send is ignored.

Both PUT and DELETE return the fresh counters, so the client does not refetch:
```json
{ "data": {
  "target_type": "POST", "target_id": "…", "value": 1,
  "upvote_count": 3, "downvote_count": 0
} }
```
`value` is `null` after DELETE. DELETE is idempotent (removing a vote that is not there returns the current
counters). One vote per target per voter key; repeating PUT with a different value flips the same row.
Unknown post/comment → `404 post_not_found` / `404 comment_not_found`.

## 7. Feed

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/feed/for-you` | no | personalised by area + follows + recency |
| GET | `/feed/trending` | no | time-decayed engagement, all areas |
| GET | `/feed/new` | no | chronological |
| GET | `/feed/nearby?lat=&lng=&radius_m=` | no | distance sorted |

Shared query params: `area_id`, `category_id`, `limit`, `cursor`, `sort`.

## 8. Users & follows

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/users/{id}` | no | public profile (pseudonymous/ghost show alias only) |
| GET | `/users/{id}/posts` | no | their posts |
| POST | `/users/{id}/follow` | yes | follow |
| DELETE | `/users/{id}/follow` | yes | unfollow |
| POST | `/areas/{id}/follow` | yes | follow an area |

## 9. Media

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/media` | yes (+ ghost `owner_key` form field) | multipart upload → `media_id` + `blur_hash` |
| GET | `/media/{id}/signed` | no (signature is the auth) | short-lived signed URL; hidden media is 404 |
| GET | `/media/{id}/file?expires=&sig=` | signed URL | the file itself; only via a valid signature |
| DELETE | `/media/{id}` | owner | delete file + row (T-021) |

Upload is **after** the post exists: `POST /media` takes multipart `file`, `post_id` and (ghost only)
`owner_key`. Only the post's owner may attach media. Accepted types: `image/jpeg`, `image/png`, `image/webp`,
`video/mp4`, `video/quicktime`; `image/heic`/`heif` is rejected for now. Images are sniffed with Pillow (the
extension and declared mime are not trusted) and get a 4×3 blurHash. Size cap: 20 MB.

```json
{ "data": {
  "media_id": "…", "post_id": "…", "kind": "IMAGE", "mime_type": "image/png",
  "bytes": 1234, "width": 1024, "height": 768, "blur_hash": "LEHV6nWB2yk8pyo0adR*.7kCMdnj"
} }
```

`GET /media/{id}/signed` returns a relative URL that expires within 300 seconds:

```json
{ "data": { "url": "/api/v1/media/…/file?expires=…&sig=…",
             "expires_at": "2026-11-01T09:10:00Z" } }
```

There is **no static mount** of the media directory. The signed URL is the only reader, and it stops working
when the signature expires or the `Media` row is deleted. Per-user reveal gating (blurred/flagged content) is
T-035.

## 10. Moderation & reveals

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/reveals` | yes | body: `{ target_type, target_id }` — record "Accept & show" |
| GET | `/reveals` | yes | what you have already revealed |
| POST | `/reports` | yes | report a post/comment/media |
| GET | `/reports` | admin | queue |
| PATCH | `/reports/{id}` | admin | `status` + action |

## 11. Notifications & push

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/notifications` | yes | list, cursor paginated |
| POST | `/notifications/{id}/read` | yes | mark read |
| POST | `/notifications/read-all` | yes | mark all read |
| POST | `/push/subscribe` | yes | store a Web Push subscription |
| DELETE | `/push/subscribe` | yes | remove it |

## 12. Admin

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/admin/moderation` | admin | flagged content queue |
| POST | `/admin/moderation/{id}/resolve` | admin | keep / remove / warn |
| POST | `/admin/users/{id}/ban` | admin | ban |
| POST | `/admin/users/{id}/unban` | admin | unban |

## 13. Health

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | `{ "status": "ok", "db": "ok" }` (`503` → `{ "status": "degraded", "db": "down" }`) |
| GET | `/openapi.json` | the machine-readable spec (also served at `/docs`) |

## 14. Error codes

`unauthorized` · `forbidden` · `not_found` · `validation_error` · `rate_limited` · `content_flagged` ·
`not_owner` · `area_required` · `turnstile_failed` (reserved for launch) · `internal_error` ·
`post_not_found` · `media_not_found` · `unsupported_media_type` · `invalid_image` · `file_too_large` ·
`invalid_signature` · `conflict` (a client-supplied id already exists).
