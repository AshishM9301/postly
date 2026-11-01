"""Post ownership, alias snapshots and the explicit response mapping."""

from __future__ import annotations

from fastapi import HTTPException
from prisma.models import Post

from app.core.deps import Principal
from app.schemas.area import AreaOut, CategoryOut
from app.schemas.post import AuthorOut, MediaOut, PostOut
from app.services.ghost import assert_ghost_owner

NOT_OWNER = {"code": "not_owner", "message": "This post belongs to someone else"}


def round_coordinate(value: float | None) -> float | None:
    """Store ~100 m precision; the exact device fix is not the app's business."""
    return None if value is None else round(value, 3)


def alias_snapshot(principal: Principal, requested: str | None) -> str:
    """Google/pseudonymous use their account alias; ghosts must send the alias."""
    if principal.mode == "ghost":
        if requested is None:
            raise HTTPException(
                status_code=422,
                detail={"code": "validation_error", "message": "Ghost posts require an alias"},
            )
        return requested
    if principal.alias is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "Session has no alias"},
        )
    return principal.alias


def require_owner_key(principal: Principal, owner_key: str | None) -> None:
    if principal.mode == "ghost" and owner_key is None:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "validation_error",
                "message": "Ghost posts require owner_key",
            },
        )


def assert_post_owner(post: Post, principal: Principal, owner_key: str | None) -> None:
    """Session owners match ``authorId``; ghosts match the stored HMAC key."""
    if principal.mode == "ghost":
        assert_ghost_owner(owner_key, post.ghostOwnerKey)
        return
    if post.authorId is None or post.authorId != principal.user_id:
        raise HTTPException(status_code=403, detail=dict(NOT_OWNER))


def delete_media_files(post: Post) -> None:
    """Seam filled by T-016.

    The DB rows cascade when the post is deleted; this hook owns removing the
    files from disk. Until media exists it is intentionally a no-op.
    """
    return None


def post_to_response(post: Post) -> PostOut:
    area = post.area
    category = post.category
    if area is None or category is None:
        raise RuntimeError("post relations were not included in the query")

    author = post.author
    return PostOut(
        id=post.id,
        alias=post.alias,
        is_anonymous=post.isAnonymous,
        title=post.title,
        body=post.body,
        status=post.status,
        moderation_state=post.moderationState,
        blame_category=post.blameCategory,
        blame_label=post.blameLabel,
        blame_vote_count=post.blameVoteCount,
        upvote_count=post.upvoteCount,
        downvote_count=post.downvoteCount,
        comment_count=post.commentCount,
        view_count=post.viewCount,
        lat=post.lat,
        lng=post.lng,
        expires_at=post.expiresAt,
        created_at=post.createdAt,
        updated_at=post.updatedAt,
        area=AreaOut(
            id=area.id,
            pincode=area.pincode,
            name=area.name,
            district=area.district,
            lat=area.lat,
            lng=area.lng,
        ),
        category=CategoryOut(
            id=category.id,
            name=category.name,
            slug=category.slug,
            icon=category.icon,
            color=category.color,
            sort_order=category.sortOrder,
        ),
        author=AuthorOut(id=author.id, alias=author.alias) if author is not None else None,
        media=[
            MediaOut(
                id=media.id,
                kind=media.kind,
                blur_hash=media.blurHash,
                width=media.width,
                height=media.height,
                duration_sec=media.durationSec,
            )
            for media in (post.media or [])
        ],
    )
