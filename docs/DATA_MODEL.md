# DATA MODEL

18 tables. `backend/prisma/schema.prisma` is the source of truth — this document explains *why* each table
looks the way it does. T-010 writes the schema; if it and this document disagree, the schema wins and this
document gets updated in the same task.

Prisma naming: models `PascalCase`, fields `camelCase` in the schema, columns snake_case in Postgres via
`@map`. Timestamps are `DateTime @default(now())`.

---

## 1. Identity

### User
| Field | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `alias` | `String @unique` | public display name, e.g. `Neighbor_7f3a` |
| `firebaseUid` | `String? @unique` | Google users only. **Email is never stored.** |
| `secretHash` | `String?` | pseudonymous mode: `HMAC-SHA256(pepper, clientSecret)` |
| `isPseudonymous` | `Boolean @default(false)` | |
| `isGhost` | `Boolean @default(false)` | always false in practice — ghosts have no row |
| `avatarUrl` | `String?` | |
| `bio` | `String?` | signed-in users only |
| `karma` | `Int @default(0)` | signed-in users only; pseudonymous/ghost earn none |
| `isAdmin` | `Boolean @default(false)` | |
| `isBanned` | `Boolean @default(false)` | |
| `bannedReason` | `String?` | |
| `createdAt` | `DateTime` | |

No email, no phone, no IP, no User-Agent, no `deletedAt` (hard delete only).

### Session
| Field | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `userId` | `String` | → `User`, cascade delete |
| `tokenHash` | `String @unique` | `HMAC-SHA256(pepper, opaqueToken)`; the raw token exists only on the client |
| `createdAt` / `expiresAt` | `DateTime` | |
| `revokedAt` | `DateTime?` | |

**Ghosts have no Session row.** Their capability is possession of a client-held secret.

---

## 2. Geography

### Area
One row per **Delhi PIN code**.
| Field | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `pincode` | `String @unique` | 6 digits |
| `name` | `String` | locality name, e.g. `Karol Bagh` |
| `district` | `String` | `NEW DELHI`, `CENTRAL`, `SOUTH WEST`, … (normalised upper-case) |
| `circle` / `region` / `division` | `String?` | India Post structure, kept for future filtering |
| `lat` / `lng` | `Float` | centre of the area (main post office) |
| `radiusMeters` | `Int @default(1500)` | max spread of that PIN's offices |
| `officeCount` | `Int @default(1)` | |
| `isActive` | `Boolean @default(true)` | |

Seed source and rules: `docs/GEO_DATA.md`.

### AreaName
Every distinct locality name a PIN contains, so search matches the neighbourhood people type and not only the
main post office. `Area.name` stays the display name; these rows only widen search.
| Field | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `areaId` | `String` | → `Area`, **cascade delete** |
| `name` | `String` | suffix-stripped office name, e.g. `Karol Bagh` |
| `createdAt` | `DateTime` | |

Indexes: `@@unique([areaId, name])`, `(name)`. Seeded with the areas (549 rows today; 547 distinct names).

---

## 3. Content

### Category
`id`, `name`, `slug @unique`, `icon`, `color`, `sortOrder`, `isActive`.
Seeded: pothole, water, garbage, electricity, roads, streetlight, noise, drainage, other.

### Post
| Field | Type | Notes |
|---|---|---|
| `id` | `String @id @default(uuid())` | **client-generated UUID** so ghosts can pre-compute their HMAC |
| `authorId` | `String?` | → `User`; null for ghost posts |
| `ghostOwnerKey` | `String?` | `HMAC-SHA256(postKey, postId)`; null for registered posts |
| `alias` | `String` | display snapshot (ghost alias is per-session) |
| `isAnonymous` | `Boolean` | true for pseudonymous + ghost |
| `areaId` | `String` | → `Area` |
| `categoryId` | `String` | → `Category` |
| `title` | `String` | |
| `body` | `String` | |
| `status` | `PostStatus` | `OPEN` \| `IN_PROGRESS` \| `SOLVED` \| `CLOSED` |
| `blameCategory` | `BlameCategory?` | `MUNICIPALITY` \| `CONTRACTOR` \| `UTILITY` \| `POLICE` \| `SCHOOL` \| `LANDLORD` \| `UNKNOWN` |
| `blameLabel` | `String?` | free text, public entities/roles only |
| `blameVoteCount` | `Int @default(0)` | |
| `moderationState` | `ModerationState` | `CLEAN` \| `FLAGGED` \| `HIDDEN` |
| `upvoteCount` / `downvoteCount` / `commentCount` / `viewCount` | `Int @default(0)` | denormalised counters |
| `lat` / `lng` | `Float?` | optional precise location, rounded to ~100 m before storage |
| `expiresAt` | `DateTime?` | ghost posts only |
| `createdAt` / `updatedAt` | `DateTime` | |

Indexes: `(areaId, createdAt)`, `(createdAt)`, `(moderationState)`, `(areaId, moderationState, createdAt)`.

### Media
`id`, `postId` → `Post` (cascade), `kind` (`IMAGE`|`VIDEO`), `path`, `thumbPath?`, `blurHash?`, `mimeType`,
`bytes`, `width?`, `height?`, `durationSec?`, `moderationState`, `nsfwScore?`, `createdAt`.

### Comment
| Field | Type | Notes |
|---|---|---|
| `id` | `String @id @default(uuid())` | client-generated |
| `postId` | `String` | → `Post` |
| `parentId` | `String?` | self relation for threads |
| `authorId` | `String?` | null for ghost comments |
| `ghostOwnerKey` | `String?` | `HMAC-SHA256(commentKey, commentId)` |
| `alias` | `String` | |
| `body` | `String` | |
| `depth` | `Int @default(0)` | max 3 |
| `moderationState` | `ModerationState` | |
| `upvoteCount` / `downvoteCount` | `Int @default(0)` | |
| `createdAt` | `DateTime` | |

Index: `(postId, createdAt)`.

---

## 4. Interaction

### Vote
| Field | Type | Notes |
|---|---|---|
| `id` | `String @id @default(cuid())` | |
| `targetType` | `VoteTarget` | `POST` \| `COMMENT` \| `BLAME` |
| `targetId` | `String` | |
| `voterId` | `String?` | → `User` for registered/pseudonymous |
| `voterKey` | `String` | `u:<userId>` or `a:HMAC(sessionKey, targetId)` for ghosts |
| `value` | `Int` | `1` or `-1` |

`@@unique([targetType, targetId, voterKey])` — one vote per target per session, for everybody.
`voterKey` is salted per target for ghosts, so one ghost's votes cannot be joined across posts.

### BlameVote
`id`, `postId`, `voterId?`, `voterKey`, `createdAt`. `@@unique([postId, voterKey])`.

### Follow
`id`, `followerId`, `followingId`, `createdAt`. `@@unique([followerId, followingId])`.

### AreaFollow
`id`, `userId`, `areaId`, `createdAt`. `@@unique([userId, areaId])`.

---

## 5. Safety

### ModerationRecord
`id`, `targetType`, `targetId`, `category`, `severity`, `score`, `provider`, `model`, `rawResponse?`,
`status` (`PENDING`|`FLAGGED`|`CONFIRMED`|`REJECTED`|`APPROVED`), `reviewedBy?`, `reviewedAt?`,
`createdAt`.

### UserReveal
`id`, `userId` → `User`, `targetType`, `targetId`, `createdAt`. `@@unique([userId, targetType, targetId])`.
This is the "Accept & show" record — it survives reloads and devices.

### Report
`id`, `targetType`, `targetId`, `reporterId?`, `reason`, `details?`, `status`
(`OPEN`|`REVIEWING`|`ACTIONED`|`DISMISSED`), `handledBy?`, `handledAt?`, `createdAt`.

---

## 6. Reach

### Notification
`id`, `userId`, `type`, `payload` (JSON), `isRead`, `createdAt`. Index `(userId, isRead, createdAt)`.

### PushSubscription
`id`, `userId`, `endpoint @unique`, `p256dh`, `auth`, `createdAt`.

### PostView
`id`, `postId`, `viewerKey`, `createdAt`. `@@unique([postId, viewerKey])` — feeds velocity, no identity.

---

## 7. Enums

```
PostStatus       OPEN IN_PROGRESS SOLVED CLOSED
BlameCategory    MUNICIPALITY CONTRACTOR UTILITY POLICE SCHOOL LANDLORD UNKNOWN
ModerationState  CLEAN FLAGGED HIDDEN
ModerationStatus PENDING FLAGGED CONFIRMED REJECTED APPROVED   (ModerationRecord.status)
VoteTarget       POST COMMENT BLAME
MediaKind        IMAGE VIDEO
ReportStatus     OPEN REVIEWING ACTIONED DISMISSED
```
Enums are Prisma enums → Postgres enums. `prisma-client-py 0.15` maps them to Python `Enum`; if a
generated enum turns out to be awkward, the fallback is `String` + a check constraint (record the change in
`docs/DECISIONS.md`).

---

## 8. Deletion cascade

Deleting a post removes: the post row, its `Media` rows **and the files on disk**, its comments, its votes,
its blame votes, its `UserReveal` rows, its `PostView` rows, its reports. Deleting a user removes:
their posts (same cascade), comments, votes, follows, reveals, notifications, sessions, push subscriptions.
Deleting a session revokes only that token.
