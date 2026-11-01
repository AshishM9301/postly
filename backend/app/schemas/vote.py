"""Request/response shapes for votes."""

from __future__ import annotations

from typing import Literal

from prisma.enums import VoteTarget
from pydantic import BaseModel, ConfigDict, Field


class VoteCast(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Literal[1, -1]
    voter_key: str | None = Field(default=None, max_length=128)


class VoteRemove(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voter_key: str | None = Field(default=None, max_length=128)


class VoteOut(BaseModel):
    target_type: VoteTarget
    target_id: str
    value: Literal[1, -1] | None
    upvote_count: int
    downvote_count: int
