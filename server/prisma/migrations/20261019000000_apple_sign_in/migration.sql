-- Sign in with Apple (19/10): a player has a Google id or an Apple id.
ALTER TABLE "players" ALTER COLUMN "google_sub" DROP NOT NULL;
ALTER TABLE "players" ADD COLUMN "apple_sub" TEXT;
ALTER TABLE "players" ADD COLUMN "apple_refresh" TEXT;

-- CreateIndex
CREATE UNIQUE INDEX "players_apple_sub_key" ON "players"("apple_sub");
