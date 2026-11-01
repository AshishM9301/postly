"""Comment creation, threading, ownership and the post's comment counter."""

from __future__ import annotations

from uuid import uuid4

from fastapi import HTTPException
from prisma.enums import ModerationState
from prisma.models import Comment

from app.core.deps import Principal
from app.db.client import db
from app.schemas.comment import CommentCreate, CommentOut, CommentUpdate
from app.schemas.post import AuthorOut
from app.services.ghost import assert_ghost_owner
from app.services.posts import alias_snapshot, require_owner_key

MAX_COMMENT_DEPTH = 3

NOT_OWNER = {"code": "not_owner", "message": "This comment belongs to someone else"}


def _post_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "post_not_found", "message": "No such post"},
    )


def _comment_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "comment_not_found", "message": "No such comment"},
    )


def assert_comment_owner(comment: Comment, principal: Principal, owner_key: str | None) -> None:
    if principal.mode == "ghost":
        assert_ghost_owner(owner_key, comment.ghostOwnerKey)
        return
    if comment.authorId is None or comment.authorId != principal.user_id:
        raise HTTPException(status_code=403, detail=dict(NOT_OWNER))


def comment_to_response(comment: Comment) -> CommentOut:
    author = comment.author
    return CommentOut(
        id=comment.id,
        post_id=comment.postId,
        parent_id=comment.parentId,
        alias=comment.alias,
        body=comment.body,
        depth=comment.depth,
        moderation_state=comment.moderationState,
        upvote_count=comment.upvoteCount,
        downvote_count=comment.downvoteCount,
        created_at=comment.createdAt,
        author=AuthorOut(id=author.id, alias=author.alias) if author is not None else None,
    )


async def create_comment(principal: Principal, post_id: str, body: CommentCreate) -> Comment:
    require_owner_key(principal, body.owner_key)
    alias = alias_snapshot(principal, body.alias)
    comment_id = str(body.id) if body.id is not None else str(uuid4())

    async with db.tx() as tx:
        post = await tx.post.find_unique(where={"id": post_id})
        if post is None:
            raise _post_not_found()

        depth = 0
        if body.parent_id is not None:
            parent = await tx.comment.find_unique(where={"id": body.parent_id})
            if parent is None:
                raise _comment_not_found()
            if parent.postId != post_id:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "validation_error",
                        "message": "parent_id belongs to a different post",
                    },
                )
            depth = parent.depth + 1
            if depth > MAX_COMMENT_DEPTH:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "code": "max_depth_exceeded",
                        "message": f"Comments nest at most {MAX_COMMENT_DEPTH} levels deep",
                    },
                )

        if body.id is not None and (
            await tx.comment.find_unique(where={"id": comment_id}) is not None
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "conflict",
                    "message": "A comment with that id already exists",
                },
            )

        data: dict[str, object] = {
            "id": comment_id,
            "postId": post_id,
            "parentId": body.parent_id,
            "alias": alias,
            "body": body.body,
            "depth": depth,
            "moderationState": ModerationState.CLEAN,
        }
        if principal.user_id is not None:
            data["authorId"] = principal.user_id
        if principal.mode == "ghost":
            data["ghostOwnerKey"] = body.owner_key

        comment = await tx.comment.create(data=data, include={"author": True})
        await tx.post.update(where={"id": post_id}, data={"commentCount": {"increment": 1}})

    return comment


async def update_comment(principal: Principal, comment_id: str, body: CommentUpdate) -> Comment:
    comment = await db.comment.find_unique(where={"id": comment_id})
    if comment is None:
        raise _comment_not_found()

    assert_comment_owner(comment, principal, body.owner_key)
    return await db.comment.update(
        where={"id": comment_id},
        data={"body": body.body},
        include={"author": True},
    )


async def _promote_children(tx, parent_id: str, delta: int, detach: bool) -> None:
    """Shift a subtree up by ``delta``; the direct children become top-level."""
    children = await tx.comment.find_many(where={"parentId": parent_id})
    for child in children:
        data: dict[str, object] = {"depth": max(0, child.depth + delta)}
        if detach:
            data["parentId"] = None
        await tx.comment.update(where={"id": child.id}, data=data)
        await _promote_children(tx, child.id, delta, False)


async def delete_comment(principal: Principal, comment_id: str, owner_key: str | None) -> None:
    async with db.tx() as tx:
        comment = await tx.comment.find_unique(where={"id": comment_id})
        if comment is None:
            raise _comment_not_found()

        assert_comment_owner(comment, principal, owner_key)

        # Keep replies: detach the direct children and shift the subtree up so
        # the promoted roots are depth 0.
        await _promote_children(tx, comment.id, -(comment.depth + 1), True)
        await tx.comment.delete(where={"id": comment.id})
        await tx.post.update(where={"id": comment.postId}, data={"commentCount": {"increment": -1}})


async def list_comments(
    post_id: str, limit: int, cursor: str | None
) -> tuple[list[Comment], str | None, bool]:
    post = await db.post.find_unique(where={"id": post_id})
    if post is None:
        raise _post_not_found()

    if cursor is not None:
        anchor = await db.comment.find_unique(where={"id": cursor})
        if anchor is None or anchor.postId != post_id:
            raise HTTPException(
                status_code=422,
                detail={"code": "validation_error", "message": "Invalid cursor"},
            )

    query: dict[str, object] = {
        "where": {"postId": post_id},
        "include": {"author": True},
        "order": [{"createdAt": "asc"}, {"id": "asc"}],
        "take": limit + 1,
    }
    if cursor is not None:
        query["cursor"] = {"id": cursor}
        query["skip"] = 1

    rows = await db.comment.find_many(**query)
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = page[-1].id if has_more and page else None
    return page, next_cursor, has_more
