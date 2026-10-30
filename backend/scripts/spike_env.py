"""T-001 environment proof: write one row and read it back through prisma-client-py."""

import asyncio

from prisma import Prisma


async def main() -> None:
    db = Prisma()
    await db.connect()
    try:
        created = await db.spikerow.create(data={"note": "spike"})
        read = await db.spikerow.find_unique(where={"id": created.id})
        assert read is not None, "row was not found after write"
        assert read.id == 1, f"expected row 1, got {read.id}"
        assert read.note == "spike", f"unexpected note: {read.note!r}"
        print(f"SPIKE OK: wrote and read row {read.id}")
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
