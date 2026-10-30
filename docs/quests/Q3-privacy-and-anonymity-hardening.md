# Q3 · Privacy & anonymity hardening

**Goal:** the privacy promises in `docs/SECURITY.md` are enforced by code and proven by tests.

**Status:** not started (blocked by Q1)

**Done when**
- A ghost post older than its expiry is deleted by the sweep job, together with its media files.
- Logging out shows the warning about anonymous posts and offers a key export.
- The unlinkability test dumps the relevant tables and proves two ghost posts share no derivable
  identifier.
- `DELETE /api/v1/me` removes the user and every trace of them, including files on disk.
- `docs/SECURITY.md` and a plain-language privacy policy exist and match the implementation.

**Planned tasks**

| ID | Task | Status |
|---|---|---|
| T-040 | Ghost expiry sweep + per-session expiry preference | planned |
| T-041 | Logout warning + key export/import UI | planned |
| T-042 | Unlinkability audit test + deletion completeness test | planned |
| T-043 | Privacy policy + security docs pass | planned |

**Notes**
- T-042 is the proof that the whole design rests on. It must actually inspect what is stored.
