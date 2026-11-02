# SECURITY — the anonymity design

This app lets people complain about local problems and about who is responsible. That combination has a
real legal and social risk for the person posting. The design goal is therefore:

> A ghost user's content must be **unlinkable to them by the operator**, while still being **deletable by
> them**, and the operator must still be able to remove harmful content.

Those two goals look contradictory. They are reconciled by keeping the secret **on the client**.

## 1. Never collect what you cannot protect

| Never stored | Why |
|---|---|
| Email | Firebase holds it; we keep only the uid. Google users can still delete their account in our DB without touching Google. |
| Phone number | not needed for anything |
| IP address | only a **rotating daily salt** hash, used for rate limiting, unrecoverable after 24h |
| User-Agent | no need; a per-device random id is enough for vote dedupe |
| Precise GPS | optional, rounded to ~100 m, and only when the user opts in |

A database dump must not be able to identify a person. That is the property we test (Q3).

## 2. The three modes

### Google (registered)
`firebase-admin` verifies the Firebase ID token. We store `User.firebaseUid` and an alias. The token is
exchanged for our own opaque session token so the browser stops re-verifying Firebase on every call.

### Pseudonymous
The client generates a 256-bit `secret` and sends it once. The server stores
`secretHash = HMAC-SHA256(PEPPER, secret)` and never the secret. The client keeps the secret (and can
export it). The server issues an opaque session token.

- Posts are linked to one alias (that is the point of a pseudonym — reputation).
- No karma, no followers, no public profile.
- Deleting the account requires the secret.

### Ghost
There is **no user row and no session row**. The server cannot even say "this ghost posted three things".

Per-row ownership proof:
```
client generates   postId = uuid4, postKey = 32 random bytes
client computes    ownerKey = HMAC-SHA256(postKey, postId)
client sends       { postId, ownerKey, … }        ← postKey never leaves the device
server stores      { id: postId, ghostOwnerKey: ownerKey, alias }
delete             client recomputes HMAC(postKey, postId) → server compares → hard delete
```
Because `postId` is part of the HMAC, two ghost posts have unrelated `ownerKey` values: the server cannot
link them, and neither can a database thief. The same pattern applies to comments.

Votes use `voterKey = HMAC-SHA256(sessionKey, targetId)` — salted per target, so one ghost's votes cannot
be joined across posts, while still allowing one-vote-per-post.

Registered and pseudonymous users use `voterKey = "u:<userId>"`, so the same unique constraint serves both.

## 3. What the operator can and cannot do

| Request | Answer | Mechanism |
|---|---|---|
| "Identify the author of this post" | **No** for ghost content | no link exists; the secret is client-only |
| "Remove this post" | **Yes** | content removal by id/URL — does not require identity |
| "Delete my account" | **Yes** | registered: session; pseudonymous: session + secret; ghost: `ownerKey` per post or the vault purge |
| "Delete everything" | **Yes** | `POST /ghost/purge` with the session key → server sweeps rows whose salted key matches |

The honest caveat: **a pseudonymous user is linkable to their alias by anyone who notices it.** That is
visible to the community, not just to us, and it is unavoidable if an alias is stable. Ghost mode avoids it
only if the ghost also rotates their alias; the alias is stable per session by design, and "rotate alias" is
one tap away.

## 4. Deletion semantics

Deletion is always **hard**: rows and files on disk, never a `deletedAt` flag. A soft delete would keep the
data we promised to erase.

- **Delete post** (`DELETE /posts/{id}`, owner session or ghost `owner_key`) → the post row, its media rows
  **and the files in `backend/media/`**, its comments, votes on the post and on those comments, blame votes,
  `UserReveal` rows, `PostView` rows and `Report` rows. `Vote`, `UserReveal` and `Report` have no foreign key
  to a post/comment, so the service deletes them explicitly before the row cascade.
- **Delete account** (`DELETE /me`) → every post above, the user's comments on other posts (their replies
  are kept and promoted to top level), votes, blame votes, follows, area follows, reveals, notifications,
  sessions and push subscriptions. A Google account needs its session; a **pseudonymous account must also
  send its client secret**, checked against `secretHash`, or the request is `403 invalid_secret`. Reports
  the user made or handled are anonymised by the schema's `SetNull`, not deleted.
- **Ghost purge** (`POST /ghost/purge`) → every post, comment and vote made with that **session key**. The
  client sends the base64url form of the raw 32-byte secret; the server decodes it, recomputes
  `HMAC-SHA256(secret, targetId)` (owner key) or `a:<same>` (voter key) for candidate rows, and deletes only
  rows whose stored key matches in constant time. The secret is never stored. The sweep is O(n) over ghost
  content. Content created with a distinct **per-post key** is not found by the session sweep — it is
  deleted with that post's `owner_key` or through a removal request.
- **Delete session** → that token only.
- **Lost the key** → `POST /posts/{id}/removal-request` creates an `OPEN` `Report` for the admin queue. No
  ownership proof is required; a moderator checks the details (exact wording, timestamp) and removes the
  content. Human judgement, not cryptography.

## 5. Expiry

Ghost posts expire. Default **90 days**, configurable per session (7 / 30 / 90 / 365). A background sweep
deletes expired rows and their media files.

On logout the app warns: *"N anonymous posts will stay up and can no longer be deleted by you — they will be
deleted on <date>."* with an **Export my keys** button, because the keys live in the browser.

## 6. Media is never public

Serving media from a static mount would make every NSFW original permanently reachable by URL, which makes
the client-side blur cosmetic. Instead:

- Files live in `backend/media/` with UUID names, outside every static route.
- `GET /media/{id}/signed` checks the caller and the reveal state, then returns a **short-lived (~5 min)
  HMAC-signed URL**.
- No image processing happens at request time, so the "less server load" goal of client-side blur holds.

## 7. Abuse controls that do not require identity

| Control | Implementation |
|---|---|
| Bot form fill | hidden honeypot field; filled ⇒ drop the submission silently |
| Too-fast humans | form filled and submitted in < 1.5 s ⇒ flag for review |
| Rate limits | `HMAC(dailySalt, ip)` → max posts per hour/day; daily salt rotates so the hash is useless later |
| Per-area flood cap | max posts per hour per area |
| Session quota | max ghost posts per session, max posts per alias |
| Duplicate collapse | same body + area within 24 h ⇒ flagged |
| Captcha | **none for now** (localhost MVP). A captcha (Cloudflare Turnstile / hCaptcha) is added at public launch. |

## 8. Secret handling

- `SECRET_KEY` (session tokens, signed media URLs) and `PEPPER` (hashes) are environment variables, never in
  the repo. `.env` is gitignored; only `.env.example` is committed.
- Rotating `PEPPER` invalidates every pseudonymous secret and every ghost ownership key — ghost posts
  become undeletable by their owners (but remain unlinkable). Rotate deliberately.
- Logging rules: never log request bodies for `/auth/*`, never log tokens, never log `owner_key` values.

## 9. Threat model (short)

| Threat | Mitigation |
|---|---|
| Operator compelled to identify a ghost | impossible by construction; we hold no secret |
| DB leak identifies users | no email/phone/IP; ghost keys are salted per target and unlinkable |
| Someone else deletes a ghost post | needs the client-side key, which is 256-bit random |
| NSFW original fetched directly | signed URLs, reveal check, no public static mount |
| Mass harassment from a ghost | alias cap, session cap, rate limits, moderator queue, ban list |
| Impersonation of a public entity | blame targets limited to public entities/roles by policy |
| Stale anonymous content | 90-day expiry + moderator removal request |
