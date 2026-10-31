"""Current principal."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import Principal, get_principal
from app.schemas.auth import Envelope, MeResponse

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
