"""Feed response shapes."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.post import PostOut


class FeedPost(PostOut):
    """A post plus the tab-specific extras (rank score / distance)."""

    score: float | None = None
    distance_meters: int | None = None


class FeedMeta(BaseModel):
    cursor: str | None
    has_more: bool


class FeedPage(BaseModel):
    data: list[FeedPost]
    meta: FeedMeta
