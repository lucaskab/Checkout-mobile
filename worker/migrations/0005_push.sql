-- Push notifications (worker/src/push.ts), for the live D1 database "checkout-saves": paste into the D1 console (or run
-- wrangler d1 execute checkout-saves --remote --file=migrations/0005_push.sql) AFTER 0004_photos.sql.
-- RUN IT ONCE: the ALTER stops a second run with "duplicate column name: pushed_at" (the tables are kept).
-- To check whether it already ran:  SELECT name FROM pragma_table_info('inbox') WHERE name = 'pushed_at';  -- one row = done
-- The same statements are at the end of schema.sql. Until it runs, the Worker works as before without pushes.

-- One row per phone: its Firebase Cloud Messaging token, the signed-in player, the game's language and the push
-- kinds left on in Opções › Avisos ("amigos,eventos"). A token that moves to another account moves with it.
CREATE TABLE IF NOT EXISTS push_devices (
	token TEXT PRIMARY KEY,
	player_id TEXT NOT NULL,
	platform TEXT NOT NULL,
	lang TEXT NOT NULL,
	categories TEXT NOT NULL,
	updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS push_devices_player ON push_devices (player_id);

-- When an inbox item was turned into a push (null = not yet; items older than an hour are never pushed).
ALTER TABLE inbox ADD COLUMN pushed_at INTEGER;
