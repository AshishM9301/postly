"""Database access: one Prisma client per process."""

from prisma import Prisma

db = Prisma()
