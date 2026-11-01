-- CreateTable
CREATE TABLE "area_names" (
    "id" TEXT NOT NULL,
    "area_id" TEXT NOT NULL,
    "name" TEXT NOT NULL,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "area_names_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "area_names_name_idx" ON "area_names"("name");

-- CreateIndex
CREATE UNIQUE INDEX "area_names_area_id_name_key" ON "area_names"("area_id", "name");

-- AddForeignKey
ALTER TABLE "area_names" ADD CONSTRAINT "area_names_area_id_fkey" FOREIGN KEY ("area_id") REFERENCES "areas"("id") ON DELETE CASCADE ON UPDATE CASCADE;
