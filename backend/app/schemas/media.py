"""Response shapes for media upload and signed URLs."""

from datetime import datetime

from prisma.enums import MediaKind
from pydantic import BaseModel


class MediaUploadOut(BaseModel):
    media_id: str
    post_id: str
    kind: MediaKind
    mime_type: str
    bytes: int
    width: int | None
    height: int | None
    blur_hash: str | None


class SignedUrlOut(BaseModel):
    url: str
    expires_at: datetime
