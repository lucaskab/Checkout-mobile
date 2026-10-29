-- D1 database "checkout-saves" (see worker/README.md). Times are milliseconds since 1970 (UTC).
-- The saves themselves live in R2 (bucket "checkout-saves"); body_key says where.

-- A player who signed in with Google or with Apple. One account = one save. The ids of players copied from the
-- Render database are kept, so the session tokens the game already holds stay valid.
CREATE TABLE IF NOT EXISTS players (
	id TEXT PRIMARY KEY,
	google_sub TEXT UNIQUE,
	apple_sub TEXT UNIQUE,
	apple_refresh TEXT,
	email TEXT,
	name TEXT,
	created_at INTEGER NOT NULL,
	last_seen INTEGER NOT NULL
);

-- The player's current progress. revision goes up by one on every upload.
-- render_revision: the Render revision this row was copied from (null for players who started here); a row still
-- at that revision has not been touched by the Worker since the copy.
CREATE TABLE IF NOT EXISTS cloud_saves (
	player_id TEXT PRIMARY KEY,
	revision INTEGER NOT NULL,
	summary TEXT NOT NULL,
	device_id TEXT NOT NULL,
	updated_at INTEGER NOT NULL,
	body_key TEXT NOT NULL,
	bytes INTEGER NOT NULL,
	render_revision INTEGER
);

-- The last saves a player replaced (restore points; the newest 10 are kept).
-- old_id: where a copied row came from ("h:<id>" = Render's save_history row, "s:<player>:<revision>" = a Render
-- save that arrived after the player had already moved on here), so the copy can run again without duplicates.
CREATE TABLE IF NOT EXISTS save_history (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	player_id TEXT NOT NULL,
	revision INTEGER NOT NULL,
	summary TEXT NOT NULL,
	device_id TEXT NOT NULL,
	saved_at INTEGER NOT NULL,
	body_key TEXT NOT NULL,
	bytes INTEGER NOT NULL,
	old_id TEXT UNIQUE
);
CREATE INDEX IF NOT EXISTS save_history_player ON save_history (player_id, saved_at);
