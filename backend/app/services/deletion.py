"""Hard deletion: posts, accounts and the ghost-session purge.

Deletion is never a flag. Children without a foreign key to their target
(``Vote``, ``UserReveal``, ``Report``) are removed explicitly, because the
database cannot cascade them. Media files are removed through the storage
provider before the rows that point at them disappear.

Ghost content stores ``ghostOwnerKey = HMAC-SHA256(secret, targetId)``. The
purge receives the base64url **session** secret, recomputes that key for each
candidate row and compares in constant time. Only rows matching this secret are
touched. The server never persists the session secret.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from collections.abc import Sequence
from dataclasses import dataclass

from fastapi import HTTPException
from prisma.enums import ReportStatus, VoteTarget
from prisma.models import Post, Report

from app.core.security import hash_secret, secure_compare
from app.db.client import db
from app.services.comments import _promote_children
from app.services.posts import delete_media_files

TARGET_POST = "POST"
TARGET_COMMENT = "COMMENT"
TARGET_MEDIA = "MEDIA"
REMOVAL_REQUEST_REASON = "removal_request"


@dataclass(frozen=True)
class PurgeResult:
    posts: int
    comments: int
    votes: int


def _post_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "post_not_found", "message": "No such post"},
    )


def _unauthorized(message: str = "Session has no user") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": "unauthorized", "message": message},
    )


def _invalid_secret() -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": "invalid_secret", "message": "The secret does not match this account"},
    )


def _invalid_session_key() -> HTTPException:
    return HTTPException(
        status_code=422,
        detail={
            "code": "validation_error",
            "message": "session_key must be the base64url encoding of the 32-byte ghost secret",
        },
    )


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _decode_session_key(value: str) -> bytes:
    """Decode the canonical base64url (no padding) form of a 32-byte secret."""
    try:
        padded = value + "=" * (-len(value) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
    except Exception as exc:
        raise _invalid_session_key() from exc

    if len(raw) != 32 or _b64url(raw) != value:
        raise _invalid_session_key()
    return raw


def ghost_owner_key(secret: bytes, target_id: str) -> str:
    digest = hmac.new(secret, target_id.encode("utf-8"), hashlib.sha256).digest()
    return _b64url(digest)


def ghost_voter_key(secret: bytes, target_id: str) -> str:
    return f"a:{ghost_owner_key(secret, target_id)}"


async def _delete_target_rows(tx, target_type: str, target_ids: Sequence[str]) -> None:
    """Remove the polymorphic children that have no foreign key to a target."""
    if not target_ids:
        return

    ids = list(target_ids)
    if target_type in {TARGET_POST, TARGET_COMMENT}:
        await tx.vote.delete_many(
            where={"targetType": VoteTarget(target_type), "targetId": {"in": ids}}
        )
    await tx.userreveal.delete_many(where={"targetType": target_type, "targetId": {"in": ids}})
    await tx.report.delete_many(where={"targetType": target_type, "targetId": {"in": ids}})


async def _remove_comment(tx, comment_id: str) -> bool:
    """Delete one comment, keeping its replies by promoting them."""
    comment = await tx.comment.find_unique(where={"id": comment_id})
    if comment is None:
        return False

    await _delete_target_rows(tx, TARGET_COMMENT, [comment.id])
    await _promote_children(tx, comment.id, -(comment.depth + 1), True)
    await tx.comment.delete(where={"id": comment.id})
    await tx.post.update(
        where={"id": comment.postId},
        data={"commentCount": {"increment": -1}},
    )
    return True


async def _delete_post_rows(tx, post_id: str) -> bool:
    """Delete a post and every child row that does not cascade by itself."""
    post = await tx.post.find_unique(where={"id": post_id})
    if post is None:
        return False

    comments = await tx.comment.find_many(where={"postId": post_id})
    media = await tx.media.find_many(where={"postId": post_id})
    comment_ids = [comment.id for comment in comments]
    media_ids = [row.id for row in media]

    await _delete_target_rows(tx, TARGET_POST, [post_id])
    await _delete_target_rows(tx, TARGET_COMMENT, comment_ids)
    await _delete_target_rows(tx, TARGET_MEDIA, media_ids)

    # Post cascades remove Media, Comment, BlameVote and PostView rows.
    await tx.post.delete(where={"id": post_id})
    return True


async def delete_post(post: Post) -> None:
    """Delete one post, its files and all of its descendants."""
    delete_media_files(post)
    async with db.tx() as tx:
        await _delete_post_rows(tx, post.id)


async def delete_account(user_id: str, secret: str | None) -> None:
    """Delete a user and every row that belongs to them.

    Pseudonymous identities must supply the same client secret they signed up
    with; a Google account only needs its session.
    """
    user = await db.user.find_unique(where={"id": user_id})
    if user is None:
        raise _unauthorized()

    if user.isPseudonymous and not secure_compare(
        hash_secret(secret) if secret else None, user.secretHash
    ):
        raise _invalid_secret()

    posts = await db.post.find_many(
        where={"authorId": user_id},
        include={"media": True},
    )
    comments = await db.comment.find_many(where={"authorId": user_id})
    own_post_ids = {post.id for post in posts}

    for post in posts:
        delete_media_files(post)

    async with db.tx() as tx:
        for post in posts:
            await _delete_post_rows(tx, post.id)
        for comment in comments:
            # Comments on their own posts are already gone with the post.
            if comment.postId not in own_post_ids:
                await _remove_comment(tx, comment.id)

        # Sessions, votes, blame votes, follows, area follows, reveals,
        # notifications and push subscriptions cascade from the user row.
        await tx.user.delete(where={"id": user_id})


async def purge_ghost(session_key: str) -> PurgeResult:
    """Delete every post, comment and vote made with this ghost session secret.

    Candidate rows are compared one by one with ``HMAC(secret, targetId)``.
    The sweep is O(n) over ghost content; fine at this scale, and a later task
    can add an index or a marker column if the table grows.
    """
    secret = _decode_session_key(session_key)

    posts = await db.post.find_many(include={"media": True})
    matched_posts = [
        post
        for post in posts
        if post.ghostOwnerKey is not None
        and secure_compare(ghost_owner_key(secret, post.id), post.ghostOwnerKey)
    ]
    matched_post_ids = {post.id for post in matched_posts}

    comments = await db.comment.find_many()
    matched_comments = [
        comment
        for comment in comments
        if comment.ghostOwnerKey is not None
        and secure_compare(ghost_owner_key(secret, comment.id), comment.ghostOwnerKey)
    ]

    cascaded_comments = (
        await db.comment.find_many(where={"postId": {"in": list(matched_post_ids)}})
        if matched_post_ids
        else []
    )
    engagement_comment_ids = {comment.id for comment in cascaded_comments} | {
        comment.id for comment in matched_comments
    }

    votes = await db.vote.find_many()
    matched_votes = [
        vote
        for vote in votes
        if vote.voterKey.startswith("a:")
        and secure_compare(ghost_voter_key(secret, vote.targetId), vote.voterKey)
    ]

    media = [row for post in matched_posts for row in (post.media or [])]
    for post in matched_posts:
        delete_media_files(post)

    async with db.tx() as tx:
        await _delete_target_rows(tx, TARGET_POST, list(matched_post_ids))
        await _delete_target_rows(tx, TARGET_COMMENT, list(engagement_comment_ids))
        await _delete_target_rows(tx, TARGET_MEDIA, [row.id for row in media])

        if matched_votes:
            await tx.vote.delete_many(where={"id": {"in": [vote.id for vote in matched_votes]}})

        for comment in matched_comments:
            if comment.postId not in matched_post_ids:
                await _remove_comment(tx, comment.id)

        for post in matched_posts:
            await _delete_post_rows(tx, post.id)

    return PurgeResult(
        posts=len(matched_posts),
        comments=len(matched_comments),
        votes=len(matched_votes),
    )


async def create_removal_request(post_id: str, details: str, reporter_id: str | None) -> Report:
    """Let anyone ask a moderator to remove a post they can no longer prove."""
    post = await db.post.find_unique(where={"id": post_id})
    if post is None:
        raise _post_not_found()

    return await db.report.create(
        data={
            "targetType": TARGET_POST,
            "targetId": post_id,
            "reporterId": reporter_id,
            "reason": REMOVAL_REQUEST_REASON,
            "details": details,
            "status": ReportStatus.OPEN,
        }
    )
