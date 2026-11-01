"""Post categories: the nine seeded rows, in display order."""

from fastapi import APIRouter

from app.db.client import db
from app.schemas.area import CategoryOut
from app.schemas.auth import Envelope

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=Envelope[list[CategoryOut]])
async def list_categories() -> Envelope[list[CategoryOut]]:
    rows = await db.category.find_many(order={"sortOrder": "asc"})
    return Envelope(
        data=[
            CategoryOut(
                id=row.id,
                name=row.name,
                slug=row.slug,
                icon=row.icon,
                color=row.color,
                sort_order=row.sortOrder,
            )
            for row in rows
        ]
    )
