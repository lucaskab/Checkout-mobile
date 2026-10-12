-- CreateTable
CREATE TABLE "players" (
    "id" TEXT NOT NULL,
    "google_sub" TEXT NOT NULL,
    "email" TEXT,
    "name" TEXT,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "last_seen" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "players_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "cloud_saves" (
    "player_id" TEXT NOT NULL,
    "revision" INTEGER NOT NULL,
    "data" TEXT NOT NULL,
    "summary" JSONB NOT NULL,
    "device_id" TEXT NOT NULL,
    "updated_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "cloud_saves_pkey" PRIMARY KEY ("player_id")
);

-- CreateTable
CREATE TABLE "save_history" (
    "id" BIGSERIAL NOT NULL,
    "player_id" TEXT NOT NULL,
    "revision" INTEGER NOT NULL,
    "data" TEXT NOT NULL,
    "summary" JSONB NOT NULL,
    "device_id" TEXT NOT NULL,
    "saved_at" TIMESTAMP(3) NOT NULL,

    CONSTRAINT "save_history_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE UNIQUE INDEX "players_google_sub_key" ON "players"("google_sub");

-- CreateIndex
CREATE INDEX "save_history_player_id_saved_at_idx" ON "save_history"("player_id", "saved_at");

-- AddForeignKey
ALTER TABLE "cloud_saves" ADD CONSTRAINT "cloud_saves_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "save_history" ADD CONSTRAINT "save_history_player_id_fkey" FOREIGN KEY ("player_id") REFERENCES "players"("id") ON DELETE CASCADE ON UPDATE CASCADE;
