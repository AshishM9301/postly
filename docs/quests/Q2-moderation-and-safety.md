# Q2 · Moderation & safety

**Goal:** content that should not be pushed at a reader is blurred behind a warning, the reader can accept
and see it, reports reach a working admin queue, and bots cannot flood a locality.

**Status:** not started (blocked by Q1)

**Done when**
- A post containing abusive language is created with `moderation_state = FLAGGED` and the UI renders it
  blurred with a warning and an "Accept & show" button.
- Accepting and showing records a `UserReveal` and stays revealed on reload.
- An NSFW image is blurred, and its original file cannot be fetched without a valid signed URL.
- A report creates a row in the admin queue; an admin can remove the content and the author sees it gone.
- A spam submission with a filled honeypot field is dropped without an error message.

**Planned tasks** (the manager writes the files when this quest opens)

| ID | Task | Status |
|---|---|---|
| T-030 | Moderation provider interface + result schema + policy mapping | planned |
| T-031 | Rule provider: EN/Hindi lexicons, PII leak, spam heuristics | planned |
| T-032 | OpenAI provider (`omni-moderation-latest`) + thresholds | planned |
| T-033 | Local HuggingFace provider + video frame sampling | planned |
| T-034 | Moderation worker process + queue | planned |
| T-035 | Blur UI + warning + reveal flow + signed media URLs | planned |
| T-036 | Reports + admin moderation queue | planned |
| T-037 | Rate limiting + honeypot + timing heuristic + quotas | planned |

**Notes**
- Threshold tuning needs a small labelled EN + HI sample set (see `docs/BACKLOG.md`).
- Scores are signals. `high` severity routes to humans; only `threat`-class content is server-redacted.
