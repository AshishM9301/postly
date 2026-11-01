"""Media endpoints: upload, short-lived signed URLs, and the file itself."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated, BinaryIO

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from prisma.enums import ModerationState

from app.core.deps import Principal, get_principal
from app.db.client import db
from app.schemas.auth import Envelope
from app.schemas.media import MediaUploadOut, SignedUrlOut
from app.services.media import (
    open_media_file,
    signature_is_valid,
    signed_url_for,
    store_upload,
)
from app.services.posts import assert_post_owner

router = APIRouter(tags=["media"])

_FILE_CHUNK = 64 * 1024


def _media_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "media_not_found", "message": "No such media"},
    )


def _iter_file(handle: BinaryIO) -> Iterator[bytes]:
    try:
        while chunk := handle.read(_FILE_CHUNK):
            yield chunk
    finally:
        handle.close()


@router.post("/media", status_code=201, response_model=Envelope[MediaUploadOut])
async def upload_media(
    principal: Annotated[Principal, Depends(get_principal)],
    file: Annotated[UploadFile, File()],
    post_id: Annotated[str, Form()],
    owner_key: Annotated[str | None, Form()] = None,
) -> Envelope[MediaUploadOut]:
    """Attach one image/video to a post. Only the post's owner may upload.

    Ghosts prove ownership with ``owner_key`` in the multipart form, exactly as
    they do for PATCH/DELETE.
    """
    post = await db.post.find_unique(where={"id": post_id})
    if post is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "post_not_found", "message": "No such post"},
        )

    assert_post_owner(post, principal, owner_key)
    media = await store_upload(file, post_id)

    return Envelope(
        data=MediaUploadOut(
            media_id=media.id,
            post_id=media.postId,
            kind=media.kind,
            mime_type=media.mimeType,
            bytes=media.bytes,
            width=media.width,
            height=media.height,
            blur_hash=media.blurHash,
        )
    )


@router.get("/media/{media_id}/signed", response_model=Envelope[SignedUrlOut])
async def signed_media_url(media_id: str) -> Envelope[SignedUrlOut]:
    """Return a ≤5-minute signed URL for an existing, visible media row.

    Public media is part of a public post, so no session is required; the
    signature is the authorization. Hidden media (moderation) is 404, and a
    deleted row can never be signed again.
    """
    media = await db.media.find_unique(where={"id": media_id})
    if media is None or media.moderationState == ModerationState.HIDDEN:
        raise _media_not_found()

    url, expires_at = signed_url_for(media.id)
    return Envelope(data=SignedUrlOut(url=url, expires_at=expires_at))


@router.get("/media/{media_id}/file")
async def serve_media_file(
    media_id: str,
    expires: Annotated[int, Query()],
    sig: Annotated[str, Query(min_length=1, max_length=128)],
) -> StreamingResponse:
    """Serve the file only with a valid, unexpired signature and a live row."""
    if not signature_is_valid(media_id, expires, sig):
        raise HTTPException(
            status_code=403,
            detail={"code": "invalid_signature", "message": "Signed URL is invalid or expired"},
        )

    media = await db.media.find_unique(where={"id": media_id})
    if media is None or media.moderationState == ModerationState.HIDDEN:
        raise _media_not_found()

    try:
        handle = open_media_file(media.path)
    except FileNotFoundError as exc:
        raise _media_not_found() from exc

    return StreamingResponse(
        _iter_file(handle),
        media_type=media.mimeType,
        headers={"Cache-Control": "private, no-store"},
    )
