"""Post CRUD: create, read, edit and hard delete, for all three identity modes."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Response
from prisma.enums import ModerationState, PostStatus
from prisma.models import Post

from app.core.deps import Principal, get_principal
from app.db.client import db
from app.schemas.auth import Envelope
from app.schemas.post import OwnerKeyBody, PostCreate, PostOut, PostUpdate
from app.services.posts import (
    alias_snapshot,
    assert_post_owner,
    delete_media_files,
    post_to_response,
    require_owner_key,
    round_coordinate,
)

router = APIRouter(tags=["posts"])

_POST_INCLUDE = {"area": True, "category": True, "author": True, "media": True}


def _post_not_found() -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"code": "post_not_found", "message": "No such post"},
    )


async def _load_post(post_id: str) -> Post:
    post = await db.post.find_unique(where={"id": post_id}, include=_POST_INCLUDE)
    if post is None:
        raise _post_not_found()
    return post


@router.post("/posts", status_code=201, response_model=Envelope[PostOut])
async def create_post(
    body: PostCreate,
    principal: Annotated[Principal, Depends(get_principal)],
) -> Envelope[PostOut]:
    """Create a post as a Google user, a pseudonymous user or a ghost.

    The id is client-generated when supplied (required for ghosts so they can
    pre-compute ``owner_key``); otherwise the server generates a UUID.
    """
    if body.media_ids:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "media_not_supported",
                "message": "Media upload is implemented in T-016; send no media_ids yet",
            },
        )

    area = await db.area.find_unique(where={"id": body.area_id})
    if area is None or not area.isActive:
        raise HTTPException(
            status_code=422,
            detail={"code": "area_required", "message": "Unknown or inactive area"},
        )

    category = await db.category.find_unique(where={"id": body.category_id})
    if category is None or not category.isActive:
        raise HTTPException(
            status_code=422,
            detail={"code": "validation_error", "message": "Unknown category"},
        )

    require_owner_key(principal, body.owner_key)
    alias = alias_snapshot(principal, body.alias)

    post_id = str(body.id) if body.id is not None else str(uuid4())
    if body.id is not None and await db.post.find_unique(where={"id": post_id}) is not None:
        raise HTTPException(
            status_code=409,
            detail={"code": "conflict", "message": "A post with that id already exists"},
        )

    data: dict[str, object] = {
        "id": post_id,
        "title": body.title,
        "body": body.body,
        "alias": alias,
        "isAnonymous": principal.mode != "google",
        "status": PostStatus.OPEN,
        "moderationState": ModerationState.CLEAN,
        "blameCategory": body.blame_category,
        "blameLabel": body.blame_label,
        "lat": round_coordinate(body.lat),
        "lng": round_coordinate(body.lng),
        "area": {"connect": {"id": body.area_id}},
        "category": {"connect": {"id": body.category_id}},
    }
    if principal.user_id is not None:
        data["author"] = {"connect": {"id": principal.user_id}}
    if principal.mode == "ghost":
        data["ghostOwnerKey"] = body.owner_key

    post = await db.post.create(data=data, include=_POST_INCLUDE)
    return Envelope(data=post_to_response(post))


@router.get("/posts/{post_id}", response_model=Envelope[PostOut])
async def get_post(post_id: str) -> Envelope[PostOut]:
    """Public read. The response model is the allow-list; no ownership secrets."""
    return Envelope(data=post_to_response(await _load_post(post_id)))


@router.patch("/posts/{post_id}", response_model=Envelope[PostOut])
async def update_post(
    post_id: str,
    body: PostUpdate,
    principal: Annotated[Principal, Depends(get_principal)],
) -> Envelope[PostOut]:
    """Edit the title/body. Ghosts must include ``owner_key`` in the body."""
    post = await db.post.find_unique(where={"id": post_id})
    if post is None:
        raise _post_not_found()

    assert_post_owner(post, principal, body.owner_key)

    changes: dict[str, object] = {}
    if body.title is not None:
        changes["title"] = body.title
    if body.body is not None:
        changes["body"] = body.body

    updated = await db.post.update(where={"id": post_id}, data=changes, include=_POST_INCLUDE)
    return Envelope(data=post_to_response(updated))


@router.delete("/posts/{post_id}", status_code=204)
async def delete_post(
    post_id: str,
    principal: Annotated[Principal, Depends(get_principal)],
    body: Annotated[OwnerKeyBody | None, Body()] = None,
) -> Response:
    """Hard delete. DB rows cascade; files are removed by the T-016 seam."""
    post = await db.post.find_unique(where={"id": post_id}, include={"media": True})
    if post is None:
        raise _post_not_found()

    assert_post_owner(post, principal, body.owner_key if body else None)
    delete_media_files(post)
    await db.post.delete(where={"id": post_id})
    return Response(status_code=204)
