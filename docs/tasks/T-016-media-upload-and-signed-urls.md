# T-016 · Media upload + blurHash + signed-URL serving

- status: ready
- quest: Q1
- depends: T-015
- owner: -
- updated: -
- files: backend/app/api/v1/media.py, backend/app/services/media.py, backend/app/providers/storage/local.py, backend/app/providers/storage/__init__.py, backend/app/schemas/media.py, backend/tests/test_media.py, backend/pyproject.toml

## Goal

Let people attach a photo (or a short video) to their report, and make sure the file can never be fetched
by someone who should not see it. Files live on local disk behind a `StorageProvider` interface, are served
through a signed-URL route, and images get a blurHash so the client can show a blurred placeholder.

## Done when

- [ ] `POST /api/v1/media` accepts a multipart upload, validates the mime type and size, writes the file
      under `backend/media/<yyyy>/<mm>/<uuid>.<ext>` and returns `media_id` + `blur_hash` for images.
- [ ] `GET /api/v1/media/{id}/signed` returns a short-lived (≤5 min) HMAC-signed URL for an authorised
      caller, and the URL actually serves the file.
- [ ] The **file path itself is not a valid URL** — no static mount exposes `backend/media/`. Fetching the
      raw path returns `404`.
- [ ] A signed URL stops working after it expires and after the media row is deleted.
- [ ] Non-image uploads are rejected with a clear error; a file that claims to be an image but is not gets
      caught by content sniffing (Pillow), not just by the extension.
- [ ] `pytest -q` covers: happy path, oversize file, wrong mime type, fake image, expired signature,
      deleted media.
- [ ] `ruff check .` and `ruff format --check .` are clean.

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

Add the working ffmpeg invocation (or the fact that ffmpeg is absent) and the blurHash component choice to
this task's `## Research notes`.

## Work log

## Report

## Manager review
