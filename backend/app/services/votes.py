"""Vote casting: one vote per voter key, counters updated in the same transaction.

The dedup key is ``u:<userId>`` for a session and a client-computed
``a:<HMAC-SHA256(sessionKey, targetId)>`` for ghosts. The server never sees the
ghost's session key, only the per-target HMAC it was given.
"""

from __future__ import annotations

import re
from typing import Literal

from fastapi import HTTPException
from prisma.enums import VoteTarget

from app.core.deps import Principal
from app.db.client import db
from app.schemas.vote import VoteOut

GHOST_VOTER_KEY = re.compile(r"^a:[A-Za-z0-9_-]{43}$")


def _target_type(raw: str) -> VoteTarget:
    normalized = raw.strip().upper()
    if normalized == "BLAME":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_error",
                "message": "BLAME votes use POST /posts/{id}/blame (T-050)",
            },
        )
    if normalized not in {"POST", "COMMENT"}:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_error",
                "message": "target_type must be POST or COMMENT",
            },
        )
    return VoteTarget(normalized)


def _voter_key(principal: Principal, provided: str | None) -> str:
    if principal.mode == "ghost":
        if provided is None:
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "voter_key_required",
                    "message": "Ghost voters must send voter_key",
                },
            )
        if not GHOST_VOTER_KEY.match(provided):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "validation_error",
                    "message": "Ghost voter_key must be a:<base64url HMAC-SHA256>",
                },
            )
        return provided
    if principal.user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "Session has no user"},
        )
    return f"u:{principal.user_id}"


async def _require_target(tx, target_type: VoteTarget, target_id: str):
    if target_type == VoteTarget.POST:
        target = await tx.post.find_unique(where={"id": target_id})
        not_found = ("post_not_found", "No such post")
    else:
        target = await tx.comment.find_unique(where={"id": target_id})
        not_found = ("comment_not_found", "No such comment")

    if target is None:
        raise HTTPException(
            status_code=404,
            detail={"code": not_found[0], "message": not_found[1]},
        )
    return target


async def _update_counters(
    tx, target_type: VoteTarget, target_id: str, up_delta: int, down_delta: int
) -> tuple[int, int]:
    if target_type == VoteTarget.POST:
        updated = await tx.post.update(
            where={"id": target_id},
            data={
                "upvoteCount": {"increment": up_delta},
                "downvoteCount": {"increment": down_delta},
            },
        )
    else:
        updated = await tx.comment.update(
            where={"id": target_id},
            data={
                "upvoteCount": {"increment": up_delta},
                "downvoteCount": {"increment": down_delta},
            },
        )
    return updated.upvoteCount, updated.downvoteCount


async def cast_vote(
    principal: Principal,
    target_type_raw: str,
    target_id: str,
    value: Literal[1, -1],
    voter_key: str | None,
) -> VoteOut:
    target_type = _target_type(target_type_raw)
    key = _voter_key(principal, voter_key)

    async with db.tx() as tx:
        await _require_target(tx, target_type, target_id)
        existing = await tx.vote.find_unique(
            where={
                "targetType_targetId_voterKey": {
                    "targetType": target_type,
                    "targetId": target_id,
                    "voterKey": key,
                }
            }
        )

        if existing is None:
            await tx.vote.create(
                data={
                    "targetType": target_type,
                    "targetId": target_id,
                    "voterId": principal.user_id,
                    "voterKey": key,
                    "value": value,
                }
            )
            up_delta = 1 if value == 1 else 0
            down_delta = 1 if value == -1 else 0
        elif existing.value == value:
            up_delta = down_delta = 0
        else:
            await tx.vote.update(
                where={"id": existing.id},
                data={"value": value, "voterId": principal.user_id},
            )
            # Flip: move one count from the old side to the new side.
            up_delta = 1 if value == 1 else -1
            down_delta = -1 if value == 1 else 1

        upvote_count, downvote_count = await _update_counters(
            tx, target_type, target_id, up_delta, down_delta
        )

    return VoteOut(
        target_type=target_type,
        target_id=target_id,
        value=value,
        upvote_count=upvote_count,
        downvote_count=downvote_count,
    )


async def remove_vote(
    principal: Principal,
    target_type_raw: str,
    target_id: str,
    voter_key: str | None,
) -> VoteOut:
    target_type = _target_type(target_type_raw)
    key = _voter_key(principal, voter_key)

    async with db.tx() as tx:
        target = await _require_target(tx, target_type, target_id)
        existing = await tx.vote.find_unique(
            where={
                "targetType_targetId_voterKey": {
                    "targetType": target_type,
                    "targetId": target_id,
                    "voterKey": key,
                }
            }
        )

        if existing is None:
            return VoteOut(
                target_type=target_type,
                target_id=target_id,
                value=None,
                upvote_count=target.upvoteCount,
                downvote_count=target.downvoteCount,
            )

        await tx.vote.delete(where={"id": existing.id})
        up_delta = -1 if existing.value == 1 else 0
        down_delta = -1 if existing.value == -1 else 0
        upvote_count, downvote_count = await _update_counters(
            tx, target_type, target_id, up_delta, down_delta
        )

    return VoteOut(
        target_type=target_type,
        target_id=target_id,
        value=None,
        upvote_count=upvote_count,
        downvote_count=downvote_count,
    )
