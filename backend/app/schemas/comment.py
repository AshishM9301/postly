"""Request/response shapes for comments and threads."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from prisma.enums import ModerationState
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.post import ALIAS_PATTERN, AuthorOut


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID | None = None
    body: str = Field(min_length=1, max_length=5000)
    parent_id: str | None = Field(default=None, max_length=64)
    alias: str | None = Field(default=None, pattern=ALIAS_PATTERN)
    owner_key: str | None = Field(default=None, min_length=1, max_length=512)

    @field_validator("body")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("parent_id")
    @classmethod
    def _clean_parent(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class CommentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=5000)
    owner_key: str | None = Field(default=None, min_length=1, max_length=512)

    @field_validator("body")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped


class CommentOwnerKey(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_key: str | None = Field(default=None, min_length=1, max_length=512)


class CommentOut(BaseModel):
    id: str
    post_id: str
    parent_id: str | None
    alias: str
    body: str
    depth: int
    moderation_state: ModerationState
    upvote_count: int
    downvote_count: int
    created_at: datetime
    author: AuthorOut | None


class CommentMeta(BaseModel):
    cursor: str | None
    has_more: bool


class CommentPage(BaseModel):
    data: list[CommentOut]
    meta: CommentMeta
