# T-016 · Media upload + blurHash + signed-URL serving

- status: done
- quest: Q1
- depends: T-015
- owner: s-20261101-0810
- updated: 2026-11-01 10:04
- files: backend/app/api/v1/media.py, backend/app/api/v1/router.py, backend/app/services/media.py, backend/app/providers/__init__.py, backend/app/providers/storage/local.py, backend/app/providers/storage/__init__.py, backend/app/schemas/media.py, backend/tests/test_media.py, backend/pyproject.toml, docs/API.md

## Goal

Let people attach a photo (or a short video) to their report, and make sure the file can never be fetched
by someone who should not see it. Files live on local disk behind a `StorageProvider` interface, are served
through a signed-URL route, and images get a blurHash so the client can show a blurred placeholder.

## Done when

- [x] `POST /api/v1/media` accepts a multipart upload, validates the mime type and size, writes the file
      under `backend/media/<yyyy>/<mm>/<uuid>.<ext>` and returns `media_id` + `blur_hash` for images.
- [x] `GET /api/v1/media/{id}/signed` returns a short-lived (≤5 min) HMAC-signed URL for an authorised
      caller, and the URL actually serves the file.
- [x] The **file path itself is not a valid URL** — no static mount exposes `backend/media/`. Fetching the
      raw path returns `404`.
- [x] A signed URL stops working after it expires and after the media row is deleted.
- [x] Non-image uploads are rejected with a clear error; a file that claims to be an image but is not gets
      caught by content sniffing (Pillow), not just by the extension.
      **Manager correction (2026-11-01):** "non-image" means "outside the allow-list" — `video/mp4` and
      `video/quicktime` are accepted (the Notes ask for them); PDFs, HEIC/HEIF and unknown types get a 422,
      and a fake image gets 422 `invalid_image`.
- [x] `pytest -q` covers: happy path, oversize file, wrong mime type, fake image, expired signature,
      deleted media.
- [x] `ruff check .` and `ruff format --check .` are clean.

## Notes / gotchas

- **Do not mount `backend/media/` as a static directory.** That is the whole point of this task: a public
  mount makes every NSFW original permanently reachable by URL, which makes the client-side blur cosmetic.
- Sign the URL with `HMAC-SHA256(SECRET_KEY, f"{media_id}:{expires_at}")` and verify the expiry. Keep the
  signing secret separate from the ownership `PEPPER`.
- The `StorageProvider` interface exists so S3/R2 can replace local disk later (T-063). Keep the interface
  small: `save(stream, ext) -> path`, `delete(path)`, `open(path)`, `signed_url(path, ttl)`.
- Validation: allow `image/jpeg`, `image/png`, `image/webp`, `image/heic` (convert or reject — decide and
  write it down) and `video/mp4`, `video/quicktime`. Cap size at `MAX_UPLOAD_MB` (20 MB default).
- Verify the real content with Pillow (`Image.open(...).verify()`), not just the declared mime type.
- blurHash is computed server-side (Pillow + the `blurhash` encoder). Keep it small: 4×3 components.
- Videos: no transcoding in the MVP. Extract a thumbnail with ffmpeg if it is available; otherwise leave
  `thumbPath` null and let the client show a placeholder. Video moderation (frame sampling) is T-033.
- Write uploads to a temp file, then move into place — never leave a half-written file in the media root.
- The upload directory is on a Docker volume (T-002). Deleting a post must delete the files too (T-021).

## Research notes

The media model: `docs/DATA_MODEL.md` §3. The serving rules: `docs/SECURITY.md` §6. The endpoint contract:
`docs/API.md` §9.

### Findings (2026-11-01)

- **ffmpeg is absent** from the `python:3.13-slim` image (`which ffmpeg` → nothing). Videos are therefore
  stored as-is with `thumbPath = null`; T-033 can add frame sampling when it brings a toolchain.
- **blurHash:** `blurhash==1.1.5` (stable; PyPI only has 1.0.0–1.1.5). Encoder is
  `blurhash.encode(rows, components_x=4, components_y=3)`, where `rows` is a list of `y` rows of `(r,g,b)`
  tuples. The image is reduced to 32×32 first.
- **HEIC/HEIF is rejected**, not converted: Pillow in this image has no HEIF plugin, so sniffing cannot
  succeed. JPEG/PNG/WebP are accepted; the **sniffed** format decides the extension and stored mime type.
- **Videos are not content-sniffed** (no ffmpeg/codec probe); the declared `video/mp4` or
  `video/quicktime` is trusted, and the stored `mimeType` is that declared value.
- The signed URL signs `HMAC-SHA256(SECRET_KEY, f"{media_id}:{expires}")` and points at
  `/api/v1/media/{id}/file`; the route re-loads the `Media` row, so a deleted row revokes a still-valid
  signature. The provider interface keeps `signed_url(resource_key, ttl)` and adds
  `verify_signed_url(resource_key, expires, sig)` — the local provider signs the media id, while a future
  S3 provider will presign its storage key.
- The upload route requires `post_id` because `Media.postId` is non-null; the flow is post → upload (not the
  T-015 `media_ids` array, which remains reserved).

## Work log

- 2026-11-01 s-20261101-0810: implemented the local storage provider, multipart upload with Pillow sniffing
  + 4×3 blurHash, signed URLs and the signed file route; 9 media tests, 65 total pass.

## Report

### 2026-11-01 · worker s-20261101-0810

- changed:
  - `backend/app/providers/storage/__init__.py` — small `StorageProvider` protocol (`save`, `delete`,
    `open`, `signed_url`, `verify_signed_url`).
  - `backend/app/providers/storage/local.py` — local disk under `media/yyyy/mm/<uuid>.<ext>`, atomic
    `.part` → rename, traversal guard, HMAC signing with `SECRET_KEY`.
  - `backend/app/services/media.py` — 20 MB cap, async spool to a temp file, declared-mime allow-list,
    Pillow `verify()`/`load()` sniffing, 32×32 → 4×3 blurHash, video pass-through, DB row creation with
    file cleanup on failure.
  - `backend/app/api/v1/media.py` — `POST /media` (post owner only; ghost `owner_key` form field),
    `GET /media/{id}/signed` (300 s URL) and `GET /media/{id}/file` (signature + live row required).
  - `backend/app/schemas/media.py` — upload and signed-URL response models.
  - `backend/app/api/v1/router.py` — wire the media router.
  - `backend/tests/test_media.py` — 9 tests: image happy path + raw path 404, oversize, PDF, HEIC, fake
    image, non-owner, video, expired signature, deleted media.
  - `backend/pyproject.toml` — pin `blurhash==1.1.5`.
  - `docs/API.md` §9 — upload fields, response shapes, signed-file route, auth and revocation semantics.
- verified (real output):
  - `python -m pytest -q` → **65 passed** (9 new); `ruff check .` → all checks passed;
    `ruff format --check .` → all files already formatted.
  - Live ghost smoke: upload of an 86-byte PNG → `MEDIA`, blurHash `L90036fZfQfZfZfSfQfSfQfQfQfQ`; signed
    URL served → `200 86 image/png`; the raw storage path → `404`; deleting the post removed the media row
    and the signed URL then returned `404`.
- issues / notes:
  - `GET /media/{id}/signed` is **public** (posts are public; the signature is the authorization). Hidden
    media returns 404. Per-user reveal gating is T-035, as `docs/SECURITY.md` §6 anticipates.
  - The "non-image uploads are rejected" done-when is implemented as "non-allowed types are rejected":
    `video/mp4` and `video/quicktime` are allowed by the Notes, while PDFs, HEIC and unknown types get a 422.
  - No `DELETE /media/{id}` endpoint yet; post deletion cascades the row but the **file remains on disk**
    until T-021 fills the `delete_media_files` seam. The tests use a temp storage root, and the live smoke
    removed its file manually.
  - `blurhash` was installed into the running container for the session; the image rebuild will install it
    from the new `pyproject.toml` pin.
  - Video thumbnails are null (ffmpeg absent); recorded above for T-033.
- next: T-017 (votes) and T-018 (comments) depend on T-015; T-021 must delete media files.

## Manager review

### 2026-11-01 · manager s-20261101-0813

- verdict: **accepted**. I exercised the whole media surface myself — upload, sniffing, the size cap, the
  signed URL, its tampering, its expiry and its revocation — and checked the one thing that matters most
  here: that the file on disk is unreachable except through a valid signature.
- checked (re-run by the manager; nothing taken from the worker's report):
  - **Upload.** A 93-byte PNG → **201** with `media_id`, `post_id`, `kind: IMAGE`, `mime_type: image/png`,
    `bytes: 93`, `width: 32`, `height: 24`, `blur_hash: "L9TI:j|cfQ|c|co1fQo1fQfQfQfQ"`. The file landed at
    `media/2026/11/09c44cc49a9b4da59954b555bf142c09.png` — the required `media/<yyyy>/<mm>/<uuid>.<ext>`
    layout, and the response never exposes the storage path.
  - **The signed URL really serves the file.** `GET /media/{id}/signed` →
    `/api/v1/media/{id}/file?expires=…&sig=<64 hex>`, `expires_at` = **now + 300 s** (≤ 5 min). Fetching it
    → **200**, `content-type: image/png`, `cache-control: private, no-store`, and the downloaded bytes are
    **byte-identical** to the upload (same SHA-256).
  - **The file path is not a URL.** `GET /media/2026/11/….png` → **404**, `GET
    /api/v1/media/2026/11/….png` → **404**. There is no `StaticFiles` mount in `backend/app/main.py`, and the
    `postly_media` volume is mounted **only** into the `api` container — I checked inside the `web`
    container: `/app/media` does not exist there.
  - **The signature is enforced.** Tampered `sig` → **403 `invalid_signature`**; tampered `expires` → **403**
    (the expiry is inside the signed message); an expired URL → **403**; media 1's signature replayed against
    media 2's id → **403**. I also recomputed the signature inside the container: it is
    `HMAC-SHA256(SECRET_KEY, f"{media_id}:{expires}")` — it matches `SECRET_KEY`, **not** the `PEPPER`, and the
    two secrets differ. The task's "keep the signing secret separate from the ownership pepper" holds.
  - **Revocation.** Deleting the `Media` row → the already-issued signed URL → **404 `media_not_found`**, and
    `GET /media/{id}/signed` → **404**. Deleting the post cascaded the media rows (`posts 0, media 0`).
  - **Content sniffing.** A text file declared `image/png` → **422 `invalid_image`** (Pillow, not the
    extension); a PDF → **422 `unsupported_media_type`**; `image/heic` → **422** with the explicit
    "HEIC/HEIF is not supported yet" message.
  - **Size cap.** A 21 MB upload → **413 `file_too_large`** ("Media is limited to 20 MB").
  - **Ownership.** Another pseudonymous user → **403 `not_owner`**; a ghost with the right `owner_key` form
    field → **201**; a ghost with a wrong key → **403**.
  - **Tests.** `docker compose exec api python -m pytest -q` → `65 passed, 1 warning` (the pre-existing
    Starlette `httpx` deprecation). The new file covers the happy path + raw-path 404, oversize, PDF, HEIC,
    the fake image, a non-owner, a video, an expired signature and a deleted row.
  - **Lint / format.** `ruff check .` → `All checks passed!`; `ruff format --check .` → `41 files already
    formatted`.
  - **The pin is current.** `pip index versions blurhash` → `1.1.5` is the newest release on PyPI (available:
    1.1.5, 1.1.4, 1.1.3, 1.1.0, 1.0.0); `pyproject.toml` pins it exactly, no range.
  - **I left the environment clean:** 0 posts, 0 media rows, 0 files in the media volume, and the two
    pseudonymous identities my smoke tests created are deleted (the one remaining user, `Neighbor_jqr8`,
    predates this session).
- one correction I made (manager owns the docs):
  - `docs/API.md` §14 listed the error codes but not `conflict` (T-015's 409 for a duplicate client id) —
    added.
- notes (no action required, carried forward):
  - **The running container's `blurhash` is a manual user-site install**, not part of the image
    (`/home/appuser/.local/lib/python3.13/site-packages/blurhash`). The pin is in `pyproject.toml`, so
    `docker compose build api` installs it — but until the image is rebuilt, a clean `docker compose up`
    would fail the import. Rebuild the `api` image before relying on the stack.
  - **`GET /media/{id}/signed` is public** — posts are public, so the signature is the authorisation. The
    API.md says so honestly ("no (signature is the auth)"). The gating that actually matters (NSFW reveal,
    hidden posts) is T-035's job; that task must gate both this endpoint and the file route on the post's
    moderation state and the per-user reveal.
  - **Videos are not content-sniffed** — no ffmpeg/codec probe in the image, so a file declared `video/mp4`
    is stored as-is. T-033 brings frame sampling and video moderation.
  - **Deleting a post cascades the media row but leaves the file on the volume** until T-021 fills the
    `delete_media_files()` seam. The file is unreachable (the row is gone, so no signature can be issued),
    but it still occupies disk.
  - The signed URL is **relative** (`/api/v1/media/…`). Fine for the web client through the proxy, but a
    mobile client needs an absolute URL — T-060/T-063 must decide whether the API should return one.
  - `LocalStorageProvider()` is built at import time with `root = Path("media")`, i.e. relative to the
    process CWD. In the container that is `/app/media` (the volume), but another CWD would silently create a
    second media tree. T-063 should make the root a setting.
  - `expires_at` is computed as `datetime.now(UTC) + 300` while the signature uses `int(time.time()) + ttl` —
    a sub-second difference between the two, harmless but worth aligning when the TTL is configurable.
- next: **T-017** (votes) and **T-018** (comments) are unblocked; **T-021** must delete the media files, and
  **T-033**/**T-035** own the video and reveal flows.
