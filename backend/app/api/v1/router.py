"""API v1 router tree."""

from fastapi import APIRouter

from app.api.v1 import areas, auth, categories, health, me, posts

router = APIRouter()
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(me.router)
router.include_router(areas.router)
router.include_router(categories.router)
router.include_router(posts.router)
