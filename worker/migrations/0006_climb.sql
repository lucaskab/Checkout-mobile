-- Anti-cheat climb clock (worker/src/store.ts afterUpload, RANKINGS.climbMsPerLevel / climbBurstLevels), for the live D1
-- database "checkout-saves": paste into the D1 console (or run
-- wrangler d1 execute checkout-saves --remote --file=migrations/0006_climb.sql) AFTER 0005_push.sql.
-- RUN IT ONCE: the ALTER stops a second run with "duplicate column name: climb_at" (nothing is harmed).
-- To check whether it already ran:  SELECT name FROM pragma_table_info('profiles') WHERE name = 'climb_at';  -- one row = done
-- The same statement is at the end of schema.sql. Until it runs, the Worker works as before (the older checks only).

-- When the player's climb "budget" is spent up to (ms since 1970; 0 = full budget): each level past the early levels
-- moves it 20 minutes ahead of max(climb_at, now); more than 10 levels ahead of now is an anti-cheat strike.
ALTER TABLE profiles ADD COLUMN climb_at INTEGER NOT NULL DEFAULT 0;
