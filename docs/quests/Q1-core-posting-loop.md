# Q1 · Core posting loop

**Goal:** a signed-in, pseudonymous or ghost user can post text + photo in a Delhi area, see it in the feed,
and the community can vote and argue in comments.

**Status:** in progress (T-010 … T-025 done; T-026 … T-029 + T-038 are the last tasks)

**Done when**
- A post created with a photo appears in `/feed/new` and `/feed/for-you` within 5 seconds.
- Upvote and downvote work on a post and on a comment; counters on the card update.
- A reply can be posted under a comment (3 levels deep).
- A ghost user can create a post, and the response contains no identifier for them.
- Area selection works by PIN code, by GPS, and by name search.
- The post composer supports image upload with a blurHash placeholder.

**Tasks**

| ID | Task | Status |
|---|---|---|
| T-010 | Prisma schema (18 models) + migration + seed categories | done |
| T-011 | Auth: Google + pseudonymous + ghost, session middleware | done |
| T-012 | Ghost crypto helpers + local key vault + export | done |
| T-013 | Delhi area seed script (pincode.csv, CC0) | done |
| T-014 | Areas API: PIN lookup, GPS nearest, name search | done |
| T-014b | Area name aliases: search every locality name of a PIN | done |
| T-015 | Post CRUD + client-generated ids + alias snapshot | done |
| T-016 | Media upload + blurHash + signed-URL serving | done |
| T-017 | Votes (up/down) + salted voter keys + counters | done |
| T-018 | Comments + nested threads + comment votes | done |
| T-019 | Feed tabs (for-you / trending / new / nearby) + ranking | done |
| T-020 | Frontend: feed UI, post card, composer, vote buttons | done |
| T-021 | Delete flows: post, account, ghost purge, removal request | done |
| T-022 | Frontend shell: left nav rail, mobile tab bar, black/red/white theme | done |
| T-023 | Frontend comments: thread view, replies and comment votes | done |
| T-024 | Frontend deletion UI: delete my post, delete my account, ghost purge, removal request | done |
| T-025 | Frontend sign-in: pseudonymous session, session restore, sign-out | done |
| T-026 | App shell refinement: centred rail, user / night mode / Report on the left, no app name | ready |
| T-027 | Deleting a comment must sweep its votes, reveals and reports | ready |
| T-028 | AI-assisted posts: the category is detected, the title is derived, 300 words max | ready |
| T-029 | The area is resolved, not asked for: GPS, PIN at first open, internet fallback | ready |
| T-038 | The composer: drop a photo or write 300 words — nothing else | ready |

**Notes**
- Ghost identity is the riskiest part of this quest. T-012 and T-021 must be reviewed carefully by the
  manager; the invariant is "the server holds no secret for ghost content".
- T-013's dataset is CC0 and already verified: 103 Delhi PINs, all with coordinates.
- The product owner wants the post to be **one action**: drop a photo or write ≤ 300 words. The category is
  detected (T-028), the area is resolved (T-029), the title is derived (T-028) — T-038 is the screen that
  makes it one box.
