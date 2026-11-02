-- Social v1 (docs/social-api.md), for the live D1 database "checkout-saves": paste into the D1 console (or run with
-- wrangler d1 execute checkout-saves --remote --file=migrations/0002_social.sql). Only creates what is missing, so it
-- is safe to run again. The same tables are at the end of schema.sql.

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
