"""Request/response shapes for the hard-deletion flows."""

from __future__ import annotations

from datetime import datetime

from prisma.enums import ReportStatus
from pydantic import BaseModel, ConfigDict, Field


class AccountDeleteRequest(BaseModel):
    """Pseudonymous accounts must prove ownership with their client secret."""

    model_config = ConfigDict(extra="forbid")

    secret: str | None = Field(default=None, min_length=1, max_length=512)


class GhostPurgeRequest(BaseModel):
    """The base64url-encoded 32-byte ghost session secret, never stored."""

    model_config = ConfigDict(extra="forbid")

    session_key: str = Field(min_length=1, max_length=512)


class GhostPurgeResult(BaseModel):
    posts: int
    comments: int
    votes: int


class RemovalRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    details: str = Field(min_length=1, max_length=2000)


class RemovalRequestOut(BaseModel):
    id: str
    target_type: str
    target_id: str
    status: ReportStatus
    created_at: datetime
