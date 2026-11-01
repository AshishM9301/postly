"""Vote endpoints: cast/change and remove, returning the fresh counters."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends

from app.core.deps import Principal, get_principal
from app.schemas.auth import Envelope
from app.schemas.vote import VoteCast, VoteOut, VoteRemove
from app.services.votes import cast_vote, remove_vote

router = APIRouter(tags=["votes"])


@router.put("/votes/{target_type}/{target_id}", response_model=Envelope[VoteOut])
async def put_vote(
    target_type: str,
    target_id: str,
    body: VoteCast,
    principal: Annotated[Principal, Depends(get_principal)],
) -> Envelope[VoteOut]:
    """Cast or change a vote. Ghosts send the salted ``voter_key``."""
    return Envelope(
        data=await cast_vote(
            principal,
            target_type,
            target_id,
            body.value,
            body.voter_key,
        )
    )


@router.delete("/votes/{target_type}/{target_id}", response_model=Envelope[VoteOut])
async def delete_vote(
    target_type: str,
    target_id: str,
    principal: Annotated[Principal, Depends(get_principal)],
    body: Annotated[VoteRemove | None, Body()] = None,
) -> Envelope[VoteOut]:
    """Remove the caller's vote (idempotent) and return the new counters."""
    return Envelope(
        data=await remove_vote(
            principal,
            target_type,
            target_id,
            body.voter_key if body else None,
        )
    )
