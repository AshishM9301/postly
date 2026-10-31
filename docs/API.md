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
| GET | `/areas/search?q=` | no | search areas by name / PIN code |
| GET | `/areas/detect?lat=&lng=` | no | nearest area for a coordinate (Haversine) |
| GET | `/areas/{id}` | no | one area with post counts |
| GET | `/categories` | no | all categories |

`/areas/detect` response:
```json
{ "data": { "id": "…", "pincode": "110019", "name": "Kirti Nagar",
             "district": "NORTH WEST", "lat": 28.63, "lng": 77.07,
             "distance_meters": 412 } }
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

Create body:
```json
{
  "id": "3f2c…uuid",
  "title": "Deep pothole near the gate",
  "body": "Three bikes have crashed here this week.",
  "area_id": "…",
  "category_id": "…",
  "media_ids": ["…"],
  "owner_key": "HMAC(postKey, id)",     // ghost only
  "lat": 28.63, "lng": 77.07            // optional, rounded server-side
}
```

## 5. Comments

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/posts/{id}/comments` | no | threaded comments (flat list + `parent_id`) |
| POST | `/posts/{id}/comments` | yes | reply (ghost: `owner_key`) |
| PATCH | `/comments/{id}` | owner | edit body |
| DELETE | `/comments/{id}` | owner | delete |
| GET | `/comments/{id}/replies` | no | one level of replies |

## 6. Votes

| Method | Path | Auth | Purpose |
|---|---|---|---|
| PUT | `/votes/{target_type}/{target_id}` | yes | cast or change a vote (body: `{ value: 1 \| -1 }`) |
| DELETE | `/votes/{target_type}/{target_id}` | yes | remove your vote |
| GET | `/me/votes` | yes | your votes |

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
| POST | `/media` | yes | multipart upload → returns `media_id` + `blur_hash` |
| GET | `/media/{id}/signed` | yes | short-lived signed URL; honours the reveal state |
| DELETE | `/media/{id}` | owner | delete file + row |

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
`not_owner` · `area_required` · `turnstile_failed` (reserved for launch) · `internal_error`.
