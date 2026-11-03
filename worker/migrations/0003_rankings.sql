-- Rankings v1 (docs/rankings-api.md), for the live D1 database "checkout-saves": paste into the D1 console (or run
-- with wrangler d1 execute checkout-saves --remote --file=migrations/0003_rankings.sql) AFTER 0002_social.sql.
-- RUN IT ONCE: D1 has no "ADD COLUMN IF NOT EXISTS", so a second run stops at the first ALTER with "duplicate column
-- name: xp" (nothing is harmed, but nothing after that line runs either). To check whether it already ran:
--   SELECT name FROM pragma_table_info('profiles') WHERE name = 'league_division';   -- one row = already done
-- The same statements are at the end of schema.sql.

-- Level boards: total XP (second key), when the level was reached (tie-break), the connection's country, the
-- "Aparecer no ranking" switch, anti-cheat, next week's league division, and whether the player has a cloud save.
ALTER TABLE profiles ADD COLUMN xp INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN level_at INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN country TEXT;
ALTER TABLE profiles ADD COLUMN ranking_opt_out INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN ranking_hidden INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN strikes INTEGER NOT NULL DEFAULT 0;
ALTER TABLE profiles ADD COLUMN league_division TEXT NOT NULL DEFAULT 'bronze';
ALTER TABLE profiles ADD COLUMN has_save INTEGER NOT NULL DEFAULT 0;

-- Profiles that already have a cloud save are ranked right away (XP arrives with their next upload; "reached first"
-- = the profile's last change).
UPDATE profiles SET has_save = 1, level_at = updated_at,
	xp = COALESCE((SELECT MAX(0, CAST(json_extract(summary, '$.xp') AS INTEGER)) FROM cloud_saves WHERE player_id = profiles.player_id), 0)
	WHERE EXISTS (SELECT 1 FROM cloud_saves WHERE player_id = profiles.player_id);

-- The boards' sort key, only over ranked players (top N = N index rows; "my rank" = a COUNT over the rows ahead).
CREATE INDEX IF NOT EXISTS profiles_rank ON profiles (level DESC, xp DESC, level_at, player_id) WHERE ranking_hidden = 0 AND ranking_opt_out = 0 AND has_save = 1;
CREATE INDEX IF NOT EXISTS profiles_rank_country ON profiles (country, level DESC, xp DESC, level_at, player_id) WHERE ranking_hidden = 0 AND ranking_opt_out = 0 AND has_save = 1;

-- Weekly league: groups of ≤ 30 players of one division and level band, per ISO week ("2026-W45").
CREATE TABLE IF NOT EXISTS league_groups (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	week TEXT NOT NULL,
	division TEXT NOT NULL,
	level_band INTEGER NOT NULL,
	members INTEGER NOT NULL DEFAULT 0,
	closed INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS league_groups_slot ON league_groups (week, division, level_band, members);
CREATE INDEX IF NOT EXISTS league_groups_open ON league_groups (week) WHERE closed = 0;

-- One row per player per week they sent points: the week total (never goes down) and when it was reached; filled at
-- the end of the week: final place, the division for next week, the diamonds and the coin chest sent.
CREATE TABLE IF NOT EXISTS league_members (
	week TEXT NOT NULL,
	player_id TEXT NOT NULL,
	group_id INTEGER NOT NULL,
	points INTEGER NOT NULL DEFAULT 0,
	points_at INTEGER NOT NULL,
	final_place INTEGER,
	moved_to TEXT,
	diamonds INTEGER,
	chest INTEGER,
	PRIMARY KEY (week, player_id)
);
CREATE INDEX IF NOT EXISTS league_members_group ON league_members (group_id, points DESC, points_at);
CREATE INDEX IF NOT EXISTS league_members_player ON league_members (player_id);
