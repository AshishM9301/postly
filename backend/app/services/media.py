"""Media upload: content sniffing, blurHash and short-lived signed URLs.

Local disk is the default provider. Media is deliberately **not** mounted as a
static directory; the only way to read a file is a signed URL that names the
media row, so deleting the row revokes access even if the file lingers.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import BinaryIO

import blurhash
from fastapi import HTTPException, UploadFile
from PIL import Image
from prisma.enums import MediaKind, ModerationState
from prisma.models import Media

from app.db.client import db
from app.providers.storage import StorageProvider
from app.providers.storage.local import LocalStorageProvider

MAX_UPLOAD_MB = 20
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
SIGNED_URL_TTL_SECONDS = 300

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
REJECTED_IMAGE_TYPES = {"image/heic", "image/heif"}
ALLOWED_VIDEO_TYPES = {"video/mp4", "video/quicktime"}

EXT_BY_FORMAT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
MIME_BY_FORMAT = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}
EXT_BY_VIDEO_TYPE = {"video/mp4": "mp4", "video/quicktime": "mov"}

BLURHASH_COMPONENTS_X = 4
BLURHASH_COMPONENTS_Y = 3
BLURHASH_SAMPLE_SIZE = 32

storage: StorageProvider = LocalStorageProvider()


def _unsupported(message: str) -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={"code": "unsupported_media_type", "message": message},
    )


def _inspect_image(path: Path) -> tuple[str, int, int, str]:
    """Sniff with Pillow, return (format, width, height, blurHash)."""
    try:
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            image.load()
            image_format = image.format or ""
            width, height = image.size
            sample = image.convert("RGB").resize(
                (BLURHASH_SAMPLE_SIZE, BLURHASH_SAMPLE_SIZE),
                Image.Resampling.LANCZOS,
            )
    except Exception as exc:
        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_image", "message": "File is not a valid image"},
        ) from exc

    if image_format not in EXT_BY_FORMAT:
        raise _unsupported(f"Unsupported image format: {image_format or 'unknown'}")

    pixels = list(sample.get_flattened_data())
    sample_width = sample.width
    rows = [pixels[row * sample_width : (row + 1) * sample_width] for row in range(sample.height)]
    encoded = blurhash.encode(
        rows,
        components_x=BLURHASH_COMPONENTS_X,
        components_y=BLURHASH_COMPONENTS_Y,
    )
    return image_format, width, height, encoded


async def _spool(upload: UploadFile) -> tuple[Path, int]:
    """Copy the upload to a temp file, enforcing the size cap as we read."""
    handle = tempfile.NamedTemporaryFile(delete=False)
    path = Path(handle.name)
    size = 0
    try:
        while chunk := await upload.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail={
                        "code": "file_too_large",
                        "message": f"Media is limited to {MAX_UPLOAD_MB} MB",
                    },
                )
            handle.write(chunk)
        handle.close()
        if size == 0:
            raise HTTPException(
                status_code=422,
                detail={"code": "empty_file", "message": "The uploaded file is empty"},
            )
        return path, size
    except Exception:
        handle.close()
        path.unlink(missing_ok=True)
        raise


async def store_upload(upload: UploadFile, post_id: str) -> Media:
    """Validate an upload, persist the file and create its ``Media`` row."""
    declared = (upload.content_type or "").split(";")[0].strip().lower()

    if declared in REJECTED_IMAGE_TYPES:
        raise _unsupported("HEIC/HEIF is not supported yet; upload JPEG, PNG or WebP")
    if declared not in ALLOWED_IMAGE_TYPES and declared not in ALLOWED_VIDEO_TYPES:
        raise _unsupported(f"Unsupported content type: {declared or 'missing'}")

    temp_path, size = await _spool(upload)
    stored_path: str | None = None
    try:
        if declared in ALLOWED_IMAGE_TYPES:
            image_format, width, height, blur_hash = _inspect_image(temp_path)
            mime_type = MIME_BY_FORMAT[image_format]
            extension = EXT_BY_FORMAT[image_format]
            kind = MediaKind.IMAGE
        else:
            width = height = None
            blur_hash = None
            mime_type = declared
            extension = EXT_BY_VIDEO_TYPE[declared]
            kind = MediaKind.VIDEO

        with temp_path.open("rb") as stream:
            stored_path = storage.save(stream, extension)

        try:
            return await db.media.create(
                data={
                    "postId": post_id,
                    "kind": kind,
                    "path": stored_path,
                    "mimeType": mime_type,
                    "bytes": size,
                    "width": width,
                    "height": height,
                    "blurHash": blur_hash,
                    "moderationState": ModerationState.CLEAN,
                }
            )
        except Exception:
            storage.delete(stored_path)
            raise
    finally:
        temp_path.unlink(missing_ok=True)


def signed_url_for(media_id: str) -> tuple[str, datetime]:
    url = storage.signed_url(media_id, SIGNED_URL_TTL_SECONDS)
    expires_at = datetime.now(UTC) + timedelta(seconds=SIGNED_URL_TTL_SECONDS)
    return url, expires_at


def signature_is_valid(media_id: str, expires: int, signature: str) -> bool:
    return storage.verify_signed_url(media_id, expires, signature)


def open_media_file(path: str) -> BinaryIO:
    return storage.open(path)
