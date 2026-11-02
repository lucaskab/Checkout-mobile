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

-- ── Social v1 (docs/social-api.md) ── the same statements as migrations/0002_social.sql (the live database gets them
-- from there). Two rows per friendship. Everything a friend does to a player becomes an inbox item; the player's game
-- applies it to its own save.

-- One per player who opened the social page: invite code, market name, level/era (refreshed by PUT /v1/save), the
-- public block sent with the save, and the invite state (invited_by: who invited this player, '' = an account since
-- deleted; invite_rewarded: both rewards sent; invites_rewarded: this player's rewarded invites).
CREATE TABLE IF NOT EXISTS profiles (
	player_id TEXT PRIMARY KEY,
	code TEXT NOT NULL UNIQUE,
	market_name TEXT,
	avatar TEXT,
	level INTEGER NOT NULL DEFAULT 1,
	era TEXT NOT NULL DEFAULT '',
	likes_total INTEGER NOT NULL DEFAULT 0,
	public_json TEXT,
	invited_by TEXT,
	invite_rewarded INTEGER NOT NULL DEFAULT 0,
	invites_rewarded INTEGER NOT NULL DEFAULT 0,
	name_hidden INTEGER NOT NULL DEFAULT 0,
	created_at INTEGER NOT NULL,
	updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS profiles_invited_by ON profiles (invited_by) WHERE invited_by IS NOT NULL;

CREATE TABLE IF NOT EXISTS friends (
	player_id TEXT NOT NULL,
	friend_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	PRIMARY KEY (player_id, friend_id)
);

CREATE TABLE IF NOT EXISTS friend_requests (
	from_id TEXT NOT NULL,
	to_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	PRIMARY KEY (from_id, to_id)
);
CREATE INDEX IF NOT EXISTS friend_requests_to ON friend_requests (to_id);

CREATE TABLE IF NOT EXISTS inbox (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	player_id TEXT NOT NULL,
	kind TEXT NOT NULL,
	from_id TEXT,
	payload TEXT NOT NULL DEFAULT '{}',
	created_at INTEGER NOT NULL,
	acked_at INTEGER
);
CREATE INDEX IF NOT EXISTS inbox_player ON inbox (player_id, acked_at);

CREATE TABLE IF NOT EXISTS daily_actions (
	player_id TEXT NOT NULL,
	day INTEGER NOT NULL,
	kind TEXT NOT NULL,
	target TEXT NOT NULL,
	PRIMARY KEY (player_id, day, kind, target)
);

CREATE TABLE IF NOT EXISTS build_helps (
	owner_id TEXT NOT NULL,
	build_id TEXT NOT NULL,
	helper_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	PRIMARY KEY (owner_id, build_id, helper_id)
);
CREATE INDEX IF NOT EXISTS build_helps_helper ON build_helps (helper_id, created_at);

CREATE TABLE IF NOT EXISTS product_requests (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	player_id TEXT NOT NULL,
	product_id TEXT NOT NULL,
	qty INTEGER NOT NULL,
	status TEXT NOT NULL DEFAULT 'open',
	fulfilled_by TEXT,
	created_at INTEGER NOT NULL,
	expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS product_requests_player ON product_requests (player_id, status);

CREATE TABLE IF NOT EXISTS name_reports (
	target_id TEXT NOT NULL,
	reporter_id TEXT NOT NULL,
	created_at INTEGER NOT NULL,
	PRIMARY KEY (target_id, reporter_id)
);
