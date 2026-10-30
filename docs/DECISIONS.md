# DECISIONS

ADR-style. Newest first. Each entry: what was decided, why, and what it costs us.

---

## AD-009 — Three identity modes, not one
**Decision.** Google / pseudonymous / ghost.
**Why.** The owner wants people to post freely without legal exposure, but the app also needs reputation
and accountability. One mode cannot do both.
**Cost.** Three auth paths, three sets of capabilities, more edge cases in the delete flows.

## AD-008 — Ghost secrets live on the client, ownership keys are salted per target
**Decision.** The client sends `HMAC-SHA256(clientSecret, targetId)`; the server never receives the secret.
**Why.** The only way to have "we cannot identify the author" *and* "the author can delete their post" is
for the operator to hold no secret. Salting per target also means two ghost posts cannot be linked by us or
by a database thief.
**Cost.** If a user loses the key they cannot delete their own content — hence the moderator removal-request
fallback and the 90-day expiry.

## AD-007 — Ghost alias is stable per session
**Decision.** One alias per browser session, with a manual "rotate alias" action.
**Why.** A per-post random alias looks broken to users and destroys any sense of continuity.
**Cost.** Anyone who notices the alias can link those posts together. It is public information, and it does
not identify the person.

## AD-006 — No captcha for now
**Decision.** Dropped Cloudflare Turnstile. Anti-spam is honeypot + form-timing + rotating-IP-hash rate
limits + session/area/alias quotas + duplicate collapse.
**Why.** Turnstile's test keys always pass (no real protection locally) and a production sitekey needs a
real domain and hostname management. Localhost MVP does not justify it.
**Cost.** Weaker bot defence until launch. A captcha goes in the backlog for the public launch.

## AD-005 — Areas are Delhi PIN codes
**Decision.** One `Area` per PIN code, seeded from a CC0 India Post dataset (103 Delhi PINs).
**Why.** PIN codes are what people can actually type, and the source data has coordinates and a permissive
licence. Wards would be nicer but need boundary polygons.
**Cost.** Less precise than wards. Ward-level upgrade tracked for Q4.

## AD-004 — Pin Prisma to 5.19.0 via prisma-client-py; npm Prisma is never installed
**Decision.** The pip `prisma` package (0.15.0) ships its own Prisma CLI **5.19.0** and Rust query engine.
No `prisma` / `@prisma/client` in package.json. `pyproject.toml` pins `prisma_version` and
`expected_engine_version` so a future pip release cannot silently jump to an RC.
**Why.** npm's `prisma` `latest` tag points at `8.0.0-rc.29` — a release candidate. Prisma 6/7 changed
generator semantics, which prisma-client-py 0.15 is not written against.
**Cost.** We are on an older Prisma than the newest stable (7.10.1). Acceptable: the schema we need is
fully expressible in 5.19.

## AD-003 — No tRPC, no NextAuth
**Decision.** The web app is a plain REST client of FastAPI. Types come from the OpenAPI spec.
**Why.** One API surface for web, future Kotlin and future Swift. tRPC would be a second, parallel contract.
**Cost.** No end-to-end type sharing; the OpenAPI→TS step has to be part of the build.

## AD-002 — Backend is FastAPI + Postgres + Prisma (Prisma from Python)
**Decision.** `schema.prisma` is the single source of truth; the Python side uses `prisma-client-py`.
**Why.** The owner wants Prisma and one schema; the API has to serve mobile clients.
**Cost.** Prisma-from-Python is a community project, not an official Prisma product. It is a moving target —
hence the explicit version pins and the fallback plan (keep `schema.prisma`, swap the Python data layer to
SQLAlchemy + Alembic) written into T-001.

## AD-001 — Moderation: OpenAI's free endpoint primary, local models as fallback
**Decision.** `rules → openai → local-hf`, switchable by env var.
**Why.** OpenAI's `omni-moderation-latest` moderation endpoint is free, handles text *and* images, and its
`hate` category explicitly covers caste — which matters for this audience. Local HuggingFace models keep us
working offline and cost nothing.
**Cost.** An API key is required for the good path; without it, Hindi coverage is noticeably weaker.
