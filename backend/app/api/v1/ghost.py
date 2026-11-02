"""Ghost-session purge: delete every row made with one client-held secret."""

from fastapi import APIRouter

from app.schemas.auth import Envelope
from app.schemas.deletion import GhostPurgeRequest, GhostPurgeResult
from app.services.deletion import purge_ghost

router = APIRouter(tags=["ghost"])


@router.post("/ghost/purge", response_model=Envelope[GhostPurgeResult])
async def purge_ghost_session(body: GhostPurgeRequest) -> Envelope[GhostPurgeResult]:
    """Sweep posts, comments and votes whose salted key matches this secret.

    The session secret travels in the request and is never persisted. Rows
    created with a different secret (another ghost session) are untouched.
    """
    result = await purge_ghost(body.session_key)
    return Envelope(
        data=GhostPurgeResult(
            posts=result.posts,
            comments=result.comments,
            votes=result.votes,
        )
    )
