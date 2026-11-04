-- Friends see each other's Google profile photo (docs/social-api.md › Photos), for the live D1 database
-- "checkout-saves": paste into the D1 console (or run with
-- wrangler d1 execute checkout-saves --remote --file=migrations/0004_photos.sql) AFTER 0003_rankings.sql.
-- RUN IT ONCE: D1 has no "ADD COLUMN IF NOT EXISTS", so a second run stops at the first ALTER with "duplicate column
-- name: photo_url" (nothing is harmed, but nothing after that line runs either). To check whether it already ran:
--   SELECT name FROM pragma_table_info('players') WHERE name = 'photo_hidden';   -- one row = already done
-- The same statements are at the end of schema.sql. Until it runs, the Worker works as before without photos.

-- The Google profile photo of the player's latest Google login (the ID token's "picture", https on
-- lh3…lh6.googleusercontent.com; null for Apple accounts and logins without one), and the profile switch
-- "Mostrar minha foto do Google para amigos" (0 = friends see it, the default; 1 = they see the avatar).
ALTER TABLE players ADD COLUMN photo_url TEXT;
ALTER TABLE players ADD COLUMN photo_hidden INTEGER NOT NULL DEFAULT 0;
