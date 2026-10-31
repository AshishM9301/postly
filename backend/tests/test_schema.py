"""Round-trip the generated client across Post, Comment and Vote."""

import asyncio
from uuid import uuid4

from prisma import Prisma
from prisma.enums import ModerationState, PostStatus, VoteTarget


async def _round_trip() -> None:
    db = Prisma()
    await db.connect()
    suffix = uuid4().hex
    pincode = f"9{int(suffix[:5], 16) % 100_000:05d}"

    user = None
    area = None
    category = None

    try:
        user = await db.user.create(data={"alias": f"Tester_{suffix[:8]}", "isPseudonymous": True})
        area = await db.area.create(
            data={
                "pincode": pincode,
                "name": "Test Area",
                "district": "TEST",
                "lat": 28.61,
                "lng": 77.21,
            }
        )
        category = await db.category.create(
            data={
                "name": "Test Category",
                "slug": f"test-category-{suffix[:8]}",
                "icon": "circle-help",
                "color": "#000000",
                "sortOrder": 999,
            }
        )

        post = await db.post.create(
            data={
                "alias": f"Tester_{suffix[:8]}",
                "isAnonymous": True,
                "title": "Test pothole",
                "body": "A pothole that needs fixing.",
                "status": PostStatus.OPEN,
                "moderationState": ModerationState.CLEAN,
                "author": {"connect": {"id": user.id}},
                "area": {"connect": {"id": area.id}},
                "category": {"connect": {"id": category.id}},
            }
        )
        comment = await db.comment.create(
            data={
                "alias": f"Tester_{suffix[:8]}",
                "body": "Confirmed, I saw it too.",
                "moderationState": ModerationState.CLEAN,
                "post": {"connect": {"id": post.id}},
                "author": {"connect": {"id": user.id}},
            }
        )
        vote = await db.vote.create(
            data={
                "targetType": VoteTarget.POST,
                "targetId": post.id,
                "voterKey": f"u:{user.id}",
                "value": 1,
                "voter": {"connect": {"id": user.id}},
            }
        )

        stored_post = await db.post.find_unique(
            where={"id": post.id},
            include={"author": True, "area": True, "category": True, "comments": True},
        )
        stored_comment = await db.comment.find_unique(where={"id": comment.id})
        stored_vote = await db.vote.find_unique(where={"id": vote.id})

        assert stored_post is not None
        assert stored_post.title == "Test pothole"
        assert stored_post.author is not None
        assert stored_post.author.id == user.id
        assert stored_post.area is not None
        assert stored_post.area.pincode == pincode
        assert stored_post.category is not None
        assert stored_post.category.slug == category.slug
        assert [row.id for row in stored_post.comments] == [comment.id]

        assert stored_comment is not None
        assert stored_comment.postId == post.id
        assert stored_comment.depth == 0

        assert stored_vote is not None
        assert stored_vote.targetType == VoteTarget.POST
        assert stored_vote.targetId == post.id
        assert stored_vote.value == 1
    finally:
        if user is not None:
            await db.user.delete(where={"id": user.id})
        if area is not None:
            await db.area.delete(where={"id": area.id})
        if category is not None:
            await db.category.delete(where={"id": category.id})
        await db.disconnect()


def test_post_comment_vote_round_trip() -> None:
    asyncio.run(_round_trip())
