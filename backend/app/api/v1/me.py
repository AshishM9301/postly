"""Current principal: read it or hard-delete the account behind it."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Response

from app.core.deps import Principal, get_principal, require_user
from app.schemas.auth import Envelope, MeResponse
from app.schemas.deletion import AccountDeleteRequest
from app.services import deletion

router = APIRouter(tags=["me"])


@router.get("/me", response_model=Envelope[MeResponse])
async def me(principal: Annotated[Principal, Depends(get_principal)]) -> Envelope[MeResponse]:
    """Resolve Google, pseudonymous and ghost callers.

    Ghost has no row to look up, so it returns ``mode: "ghost"`` with a null
    alias and the default expiry preference; its ownership lives on each row.
    """
    return Envelope(
        data=MeResponse(
            mode=principal.mode,
            alias=principal.alias,
            user_id=principal.user_id,
            expiry_days=principal.expiry_days,
            is_admin=principal.is_admin,
        )
    )


@router.delete("/me", status_code=204)
async def delete_me(
    principal: Annotated[Principal, Depends(require_user)],
    body: Annotated[AccountDeleteRequest | None, Body()] = None,
) -> Response:
    """Hard delete the account, its content and every row that belongs to it.

    Pseudonymous accounts must repeat their client ``secret`` in the body; a
    Google account is authenticated by its session alone.
    """
    if principal.user_id is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "unauthorized", "message": "Session has no user"},
        )

    await deletion.delete_account(principal.user_id, body.secret if body is not None else None)
    return Response(status_code=204)
