# PLAN — Postly

## 1. The idea

People post **real problems in their locality** — potholes, water supply, garbage, streetlights, broken
roads — with photos and videos. Every post is tied to an **area** (a Delhi PIN code). The community
**votes**; a time-decayed ranking produces a local "news panel" of what matters right now. Posts can name
a **blame target** (municipality, contractor, utility, police) and the argument happens in threaded
comments. Abusive or NSFW content is **blurred behind a warning**; the reader decides to look.

The audience is a person standing in front of a broken water pipe who wants to know (a) has anyone else
reported this, (b) is anyone else doing anything about it, and (c) who is responsible.

## 2. Non-goals

- Not a directory of government services, not a complaint filing system.
- Not a chat app. The comment thread is a debate attached to a post, not messaging.
- Not a marketplace, not a service directory, not a job board.
- Not a location tracker. Precise GPS is optional and coarse.

## 3. Users

| | |
|---|---|
| **Signed-in (Google)** | Full account: profile, follows, karma, notifications. Email is never stored in our DB. |
| **Pseudonymous** | Alias + a secret only the device holds. Posts, votes, comments. No karma, no profile, no followers. |
| **Ghost** | No account record at all. Posts, votes, comments. Posts auto-expire (90 days default, configurable per session). The server cannot identify the author — by construction, not by policy. |

## 4. Feature list

### Core loop (Q1)
- Create a post: title, body, category, area, 0–n photos/videos.
- Feed tabs: **For You** (personalised), **Trending** (time-decayed), **New** (chronological), **Nearby** (GPS radius / selected area).
- Upvote / downvote posts and comments; one vote per target per session.
- Threaded comments (reply to a comment).
- Profiles and follows (signed-in only).
- Area resolution: enter a **PIN code**, or let the browser **detect GPS** and match the nearest area, or search by name.

### Moderation & safety (Q2)
- Text + image moderation with a blurred warning state and a per-user **"Accept & show"** reveal that persists.
- Automatic categories: abusive language, hate, threats, sexual/NSFW, graphic violence, PII leaks (phone/email/Aadhaar in a post), spam.
- Human review queue: report a post/comment → admin queue → keep / remove / warn / ban.
- Anti-spam without identity: honeypot field, form-timing heuristic, rotating-IP-hash rate limits, per-session and per-area quotas.

### Privacy hardening (Q3)
- Ghost post expiry job (90 days default, per-session configurable).
- Logout warning + key export so anonymous users can delete their own content later.
- Deletion: one post, whole account, everything ghost, or a moderator-assisted removal request.
- Unlinkability audit test proving a database dump cannot join two ghost posts.

### Community (Q4)
- Post status workflow: `OPEN → IN_PROGRESS → SOLVED`.
- Blame target with its own community vote.
- Notifications (in-app + Web Push).
- Search, share links, Open Graph images.

### Mobile-ready (Q5)
- Versioned API, published OpenAPI spec, notes for Retrofit / SwiftGen codegen.
- Refresh-token rotation, session management.
- `StorageProvider` swap to S3-compatible object storage with presigned uploads.

## 5. Ranking (how "trending" works)

```
engagement = 1.0*log10(max(1, net_votes) + 2) + 0.6*comments + 0.05*views
score     = engagement * exp(-age_hours / HALF_LIFE) * area_boost * affinity_boost
```
`HALF_LIFE` = 12h for For You, 18h for Trending. A diversity penalty stops one author or one area from
owning the panel. Counters are denormalised on the post row and updated in the same transaction as the vote;
the score is computed at query time (materialised snapshots later).

## 6. Milestones

| Quest | Goal |
|---|---|
| **Q0** Foundation | Docker Compose runs Postgres + FastAPI + Next; a session can pick up work without re-researching |
| **Q1** Core posting loop | A signed-in, pseudonymous or ghost user can post text+photo in a Delhi area and see it in the feed with working votes and comments |
| **Q2** Moderation & safety | Flagged content is blurred with a warning; reveals persist; reports reach a working admin queue |
| **Q3** Privacy hardening | Expiry, key export, deletion flows, unlinkability proof |
| **Q4** Community layer | Status workflow, blame votes, profiles, follows, notifications |
| **Q5** Mobile-ready | Versioned API, codegen notes, S3 storage, token rotation |

## 7. Success criteria for the MVP

1. A user can pick their area from a PIN code or GPS and post a photo problem in under a minute.
2. The feed shows the same post with different rankings depending on the tab, and a fresh post can reach
   the top of Trending within the hour.
3. A comment thread can be read and voted on, and abusive content in it is blurred until accepted.
4. A ghost user can delete their post, and the server cannot name them afterwards.
5. The whole thing runs from `docker compose up` on a laptop, and the API spec is good enough to build a
   Kotlin client against.
