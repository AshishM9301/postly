# Q5 · Mobile-ready

**Goal:** a Kotlin or Swift team can build a client against this API without asking us questions.

**Status:** not started (blocked by Q4)

**Done when**
- The API is versioned (`/api/v1`) and the OpenAPI spec is exported and committed.
- Codegen notes exist for Retrofit (Kotlin) and SwiftGen (Swift), including auth, uploads and pagination.
- Refresh tokens rotate and old ones are revoked; sessions can be listed and revoked by the user.
- The storage provider can be switched to S3-compatible object storage with presigned uploads, with no
  change to the API surface.

**Planned tasks**

| ID | Task | Status |
|---|---|---|
| T-060 | API versioning + exported OpenAPI spec | planned |
| T-061 | Retrofit + SwiftGen codegen notes | planned |
| T-062 | Refresh-token rotation + session management UI | planned |
| T-063 | S3/R2 storage provider + presigned uploads | planned |

**Notes**
- The API must not grow web-only concepts (server-side rendering assumptions, cookie sessions).
