"""Comment endpoints: threads, edits and deletes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Response

from app.core.deps import Principal, get_principal
from app.schemas.auth import Envelope
from app.schemas.comment import (
    CommentCreate,
    CommentMeta,
    CommentOut,
    CommentOwnerKey,
    CommentPage,
    CommentUpdate,
)
from app.services.comments import (
    comment_to_response,
    create_comment,
    delete_comment,
    list_comments,
    update_comment,
)

router = APIRouter(tags=["comments"])


@router.post(
    "/posts/{post_id}/comments",
    status_code=201,
    response_model=Envelope[CommentOut],
)
async def post_comment(
    post_id: str,
    body: CommentCreate,
    principal: Annotated[Principal, Depends(get_principal)],
) -> Envelope[CommentOut]:
    """Create a top-level comment or a reply (``parent_id``)."""
    comment = await create_comment(principal, post_id, body)
    return Envelope(data=comment_to_response(comment))


@router.get("/posts/{post_id}/comments", response_model=CommentPage)
async def get_comments(
    post_id: str,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
    cursor: Annotated[str | None, Query(max_length=64)] = None,
) -> CommentPage:
    """Flat thread, oldest first; the client rebuilds the tree from parent_id."""
    rows, next_cursor, has_more = await list_comments(post_id, limit, cursor)
    return CommentPage(
        data=[comment_to_response(comment) for comment in rows],
        meta=CommentMeta(cursor=next_cursor, has_more=has_more),
    )


@router.patch("/comments/{comment_id}", response_model=Envelope[CommentOut])
async def edit_comment(
    comment_id: str,
    body: CommentUpdate,
    principal: Annotated[Principal, Depends(get_principal)],
) -> Envelope[CommentOut]:
    comment = await update_comment(principal, comment_id, body)
    return Envelope(data=comment_to_response(comment))


@router.delete("/comments/{comment_id}", status_code=204)
async def remove_comment(
    comment_id: str,
    principal: Annotated[Principal, Depends(get_principal)],
    body: Annotated[CommentOwnerKey | None, Body()] = None,
) -> Response:
    await delete_comment(principal, comment_id, body.owner_key if body else None)
    return Response(status_code=204)
