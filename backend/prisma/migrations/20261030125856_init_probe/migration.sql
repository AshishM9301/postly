-- CreateTable
CREATE TABLE "SpikeRow" (
    "id" SERIAL NOT NULL,
    "note" TEXT NOT NULL,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "SpikeRow_pkey" PRIMARY KEY ("id")
);
