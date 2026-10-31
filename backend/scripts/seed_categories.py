"""Seed the nine post categories.

Idempotent: keyed on the unique slug, so running it repeatedly leaves exactly
the nine rows.
"""

import asyncio

from prisma import Prisma

CATEGORIES: list[dict[str, object]] = [
    {
        "slug": "pothole",
        "name": "Pothole",
        "icon": "traffic-cone",
        "color": "#f97316",
        "sortOrder": 1,
    },
    {
        "slug": "water",
        "name": "Water Supply",
        "icon": "droplets",
        "color": "#0ea5e9",
        "sortOrder": 2,
    },
    {
        "slug": "garbage",
        "name": "Garbage",
        "icon": "trash-2",
        "color": "#65a30d",
        "sortOrder": 3,
    },
    {
        "slug": "electricity",
        "name": "Electricity",
        "icon": "zap",
        "color": "#eab308",
        "sortOrder": 4,
    },
    {
        "slug": "roads",
        "name": "Roads",
        "icon": "route",
        "color": "#6366f1",
        "sortOrder": 5,
    },
    {
        "slug": "streetlight",
        "name": "Streetlight",
        "icon": "lightbulb",
        "color": "#f59e0b",
        "sortOrder": 6,
    },
    {
        "slug": "noise",
        "name": "Noise",
        "icon": "volume-2",
        "color": "#ec4899",
        "sortOrder": 7,
    },
    {
        "slug": "drainage",
        "name": "Drainage",
        "icon": "waves",
        "color": "#14b8a6",
        "sortOrder": 8,
    },
    {
        "slug": "other",
        "name": "Other",
        "icon": "circle-help",
        "color": "#64748b",
        "sortOrder": 9,
    },
]


async def seed_categories() -> int:
    db = Prisma()
    await db.connect()
    try:
        for category in CATEGORIES:
            await db.category.upsert(
                where={"slug": category["slug"]},
                data={"create": category, "update": category},
            )
        return await db.category.count()
    finally:
        await db.disconnect()


def main() -> None:
    total = asyncio.run(seed_categories())
    print(f"seed_categories: {total} categories present")


if __name__ == "__main__":
    main()
