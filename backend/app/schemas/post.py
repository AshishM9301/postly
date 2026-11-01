"""Request/response shapes for posts.

The response model is an explicit allow-list: ``ghostOwnerKey``, ``secretHash``
and ``tokenHash`` are never fields here, so they cannot leak even if the Prisma
row is included.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from prisma.enums import BlameCategory, MediaKind, ModerationState, PostStatus
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.area import AreaOut, CategoryOut

ALIAS_PATTERN = r"^[A-Za-z0-9_]{3,32}$"


class PostCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=10_000)
    area_id: str = Field(min_length=1, max_length=64)
    category_id: str = Field(min_length=1, max_length=64)
    alias: str | None = Field(default=None, pattern=ALIAS_PATTERN)
    owner_key: str | None = Field(default=None, min_length=1, max_length=512)
    blame_category: BlameCategory | None = None
    blame_label: str | None = Field(default=None, max_length=120)
    status: Literal["OPEN"] = "OPEN"
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    media_ids: list[str] = Field(default_factory=list, max_length=20)

    @field_validator("title", "body")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("blame_label")
    @classmethod
    def _clean_blame_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def _blame_label_needs_category(self) -> PostCreate:
        if self.blame_label is not None and self.blame_category is None:
            raise ValueError("blame_label requires blame_category")
        return self


class PostUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1, max_length=10_000)
    owner_key: str | None = Field(default=None, min_length=1, max_length=512)

    @field_validator("title", "body")
    @classmethod
    def _not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @model_validator(mode="after")
    def _at_least_one_field(self) -> PostUpdate:
        if self.title is None and self.body is None:
            raise ValueError("Provide title and/or body")
        return self


class OwnerKeyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_key: str | None = Field(default=None, min_length=1, max_length=512)


class AuthorOut(BaseModel):
    id: str
    alias: str


class MediaOut(BaseModel):
    id: str
    kind: MediaKind
    blur_hash: str | None
    width: int | None
    height: int | None
    duration_sec: float | None


class PostOut(BaseModel):
    id: str
    alias: str
    is_anonymous: bool
    title: str
    body: str
    status: PostStatus
    moderation_state: ModerationState
    blame_category: BlameCategory | None
    blame_label: str | None
    blame_vote_count: int
    upvote_count: int
    downvote_count: int
    comment_count: int
    view_count: int
    lat: float | None
    lng: float | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    area: AreaOut
    category: CategoryOut
    author: AuthorOut | None
    media: list[MediaOut]
