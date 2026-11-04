import type { D1PreparedStatement, Row } from "./cf.ts";
import { DIVISION_MULTIPLIER, DIVISIONS, PLACE_DIAMONDS, RANKINGS, weekOf, weekStartOf } from "./limits.ts";
import { SHOWN_PHOTO, type Store } from "./store.ts";

/**
 * Rankings v1 storage (docs/rankings-api.md): the level boards over `profiles` and the weekly league
 * (`league_groups`, `league_members`). Every read is one indexed query; every write that must happen once (joining a
 * group, the end of a week) is guarded inside its own D1 batch, so two at once cannot both pass.
 */

/** A ranked profile: on Mundo/País. Written exactly like the partial indexes' WHERE, so SQLite uses them. */
export const RANKED = "ranking_hidden = 0 AND ranking_opt_out = 0 AND has_save = 1";
const rankedAs = (alias: string) => RANKED.split(" AND ").map((term) => `${alias}.${term}`).join(" AND ");
const ORDER = "level DESC, xp DESC, level_at, player_id";
const BOARD_COLUMNS = "player_id, code, market_name, name_hidden, avatar, level, xp, era, country";

const next = (column: string) => `CASE ${column} ${DIVISIONS.map((d, i) => `WHEN '${d}' THEN '${DIVISIONS[Math.min(i + 1, DIVISIONS.length - 1)]}'`).join(" ")} ELSE ${column} END`;
const previous = (column: string) => `CASE ${column} ${DIVISIONS.map((d, i) => `WHEN '${d}' THEN '${DIVISIONS[Math.max(i - 1, 0)]}'`).join(" ")} ELSE ${column} END`;
const baseDiamonds = (column: string) => `CASE ${column} ${PLACE_DIAMONDS.map((d, i) => `WHEN ${i + 1} THEN ${d}`).join(" ")} ELSE 0 END`;
const multiplier = (column: string) => `CASE ${column} ${DIVISIONS.map((d) => `WHEN '${d}' THEN ${DIVISION_MULTIPLIER[d]}`).join(" ")} ELSE 1 END`;

/** The previous ISO week's id. */
export const previousWeek = (now: number) => weekOf(weekStartOf(now) - 1);

export class RankingStore {
	store: Store;
	constructor(store: Store) {
		this.store = store;
	}
	get db() {
		return this.store.db;
	}

	// ── Level boards ────────────────────────────────────────────────────────────────────────────────────────────

	/** The top `limit` ranked players (of a country or the world) and how many are ranked: two statements. */
	top(country: string | null, limit: number): D1PreparedStatement[] {
		const where = country ? `country = ? AND ${RANKED}` : RANKED;
		const values = country ? [country] : [];
		return [
			this.db.prepare(`SELECT ${BOARD_COLUMNS} FROM profiles WHERE ${where} ORDER BY ${ORDER} LIMIT ?`).bind(...values, limit),
			this.db.prepare(`SELECT COUNT(*) AS total FROM profiles WHERE ${where}`).bind(...values),
		];
	}

	/**
	 * My profile and my rank: 1 + the ranked players ahead of me by the sort key (level DESC, xp DESC, level_at,
	 * player_id), as four index range counts (`byCountry`: among my country's players). `rank` is null when I am not
	 * ranked (opt-out, hidden, no save yet; no country for the country board).
	 */
	me(playerId: string, byCountry: boolean): D1PreparedStatement {
		const q = `${rankedAs("q")}${byCountry ? " AND q.country = p.country" : ""}`;
		const ahead = [
			"q.level > p.level",
			"q.level = p.level AND q.xp > p.xp",
			"q.level = p.level AND q.xp = p.xp AND q.level_at < p.level_at",
			"q.level = p.level AND q.xp = p.xp AND q.level_at = p.level_at AND q.player_id < p.player_id",
		].map((cond) => `(SELECT COUNT(*) FROM profiles q WHERE ${q} AND ${cond})`);
		return this.db
			.prepare(
				`SELECT p.*, CASE WHEN ${rankedAs("p")}${byCountry ? " AND p.country IS NOT NULL" : ""} THEN 1 + ${ahead.join(" + ")} END AS rank
				 FROM profiles p WHERE p.player_id = ?`,
			)
			.bind(playerId);
	}

	/**
	 * Me and my friends (hidden friends are off every board) with this week's league points and the market rating and,
	 * with the photo columns (`withPhotos`), the Google photo each lets friends see (only this board: its rows are
	 * friends or me).
	 */
	friends(playerId: string, week: string, withPhotos = false): D1PreparedStatement {
		return this.db
			.prepare(
				`SELECT pr.*, COALESCE(m.points, 0) AS week_points, json_extract(pr.public_json, '$.marketRating') AS market_rating${withPhotos ? `, ${SHOWN_PHOTO} AS photo` : ""}
				 FROM profiles pr LEFT JOIN league_members m ON m.week = ?1 AND m.player_id = pr.player_id${withPhotos ? " LEFT JOIN players pl ON pl.id = pr.player_id" : ""}
				 WHERE pr.player_id = ?2 OR (pr.ranking_hidden = 0 AND pr.player_id IN (SELECT friend_id FROM friends WHERE player_id = ?2))`,
			)
			.bind(week, playerId);
	}

	async setOptOut(playerId: string, optOut: boolean, ensure: D1PreparedStatement[]) {
		await this.db.batch([...ensure, this.db.prepare("UPDATE profiles SET ranking_opt_out = ? WHERE player_id = ?").bind(optOut ? 1 : 0, playerId)]);
	}

	// ── Weekly league ───────────────────────────────────────────────────────────────────────────────────────────

	/**
	 * My profile plus my league state: this week's group and points, a group of mine from a past week that was not
	 * closed yet (it must close before I join a new one: it decides my division), and whether any past group is open.
	 */
	state(playerId: string, week: string): D1PreparedStatement {
		return this.db
			.prepare(
				`SELECT p.*,
				   (SELECT group_id FROM league_members WHERE week = ?1 AND player_id = p.player_id) AS group_id,
				   (SELECT points FROM league_members WHERE week = ?1 AND player_id = p.player_id) AS week_points,
				   (SELECT m.group_id FROM league_members m JOIN league_groups g ON g.id = m.group_id AND g.closed = 0
				    WHERE m.player_id = p.player_id AND m.week < ?1 LIMIT 1) AS stale_group,
				   EXISTS (SELECT 1 FROM league_groups WHERE closed = 0 AND week < ?1) AS stale_any
				 FROM profiles p WHERE p.player_id = ?2`,
			)
			.bind(week, playerId);
	}

	/** My group this week, best first (points DESC, then who reached the total first); hidden players only as myself. */
	group(playerId: string, week: string): D1PreparedStatement {
		return this.db
			.prepare(
				`SELECT m.player_id, m.points, m.points_at, pr.code, pr.market_name, pr.name_hidden, pr.avatar, pr.level,
				   EXISTS (SELECT 1 FROM friends WHERE player_id = ?2 AND friend_id = m.player_id) AS is_friend
				 FROM league_members m JOIN profiles pr ON pr.player_id = m.player_id
				 WHERE m.group_id = (SELECT group_id FROM league_members WHERE week = ?1 AND player_id = ?2) AND (pr.ranking_hidden = 0 OR m.player_id = ?2)
				 ORDER BY m.points DESC, m.points_at, m.player_id`,
			)
			.bind(week, playerId);
	}

	/** How my (closed) group of a past week ended for me. */
	lastWeek(playerId: string, week: string): D1PreparedStatement {
		return this.db
			.prepare(
				`SELECT g.division, m.final_place, m.moved_to FROM league_members m JOIN league_groups g ON g.id = m.group_id AND g.closed = 1
				 WHERE m.week = ?1 AND m.player_id = ?2`,
			)
			.bind(week, playerId);
	}

	/**
	 * Stores my week total (already capped): joins a group first when I have none this week — the open group (< 30
	 * members) of my division and level band, else a new one — then keeps the larger total (never goes down; `points_at`
	 * moves only when it grows). Group choice, insert and member count are one transaction, so a group never passes 30.
	 * `strike`: also one anti-cheat strike. Answers my stored points, place and group size.
	 */
	async sendPoints(playerId: string, week: string, band: number, points: number, joined: boolean, strike: boolean) {
		const now = this.store.clock();
		const division = "(SELECT league_division FROM profiles WHERE player_id = ?2)";
		const slot = `week = ?1 AND division = ${division} AND level_band = ?3 AND members < ${RANKINGS.groupSize} AND closed = 0`;
		const statements: D1PreparedStatement[] = [];
		if (!joined)
			statements.push(
				this.db
					.prepare(
						`INSERT INTO league_groups (week, division, level_band, members) SELECT ?1, ${division}, ?3, 0
						 WHERE NOT EXISTS (SELECT 1 FROM league_groups WHERE ${slot}) AND NOT EXISTS (SELECT 1 FROM league_members WHERE week = ?1 AND player_id = ?2)`,
					)
					.bind(week, playerId, band),
			);
		// A member: only a larger total is written. Joining: the open slot (or, when a second request of mine joined
		// first, my group — SQLite checks NOT NULL before the conflict clause).
		statements.push(
			joined
				? this.db.prepare("UPDATE league_members SET points = ?3, points_at = ?4 WHERE week = ?1 AND player_id = ?2 AND points < ?3").bind(week, playerId, points, now)
				: this.db
						.prepare(
							`INSERT INTO league_members (week, player_id, group_id, points, points_at)
							 SELECT ?1, ?2, COALESCE((SELECT id FROM league_groups WHERE ${slot} ORDER BY id LIMIT 1), (SELECT group_id FROM league_members WHERE week = ?1 AND player_id = ?2)), ?4, ?5
							 ON CONFLICT (week, player_id) DO UPDATE SET points = MAX(points, excluded.points),
							   points_at = CASE WHEN excluded.points > points THEN excluded.points_at ELSE points_at END`,
						)
						.bind(week, playerId, band, points, now),
		);
		if (!joined)
			statements.push(
				this.db
					.prepare("UPDATE league_groups SET members = (SELECT COUNT(*) FROM league_members WHERE group_id = league_groups.id) WHERE id = (SELECT group_id FROM league_members WHERE week = ?1 AND player_id = ?2)")
					.bind(week, playerId),
			);
		if (strike) statements.push(strikeStatement(this.store, playerId));
		statements.push(
			this.db
				.prepare(
					`SELECT m.points,
					   1 + (SELECT COUNT(*) FROM league_members o JOIN profiles op ON op.player_id = o.player_id AND op.ranking_hidden = 0
					        WHERE o.group_id = m.group_id AND o.player_id != m.player_id
					          AND (o.points > m.points OR (o.points = m.points AND (o.points_at < m.points_at OR (o.points_at = m.points_at AND o.player_id < m.player_id))))) AS place,
					   (SELECT COUNT(*) FROM league_members o JOIN profiles op ON op.player_id = o.player_id
					    WHERE o.group_id = m.group_id AND (op.ranking_hidden = 0 OR o.player_id = m.player_id)) AS size
					 FROM league_members m WHERE m.week = ?1 AND m.player_id = ?2`,
				)
				.bind(week, playerId),
		);
		const results = await this.db.batch(statements);
		const row = results[results.length - 1].results[0] ?? {};
		return { points: Number(row.points ?? 0), place: row.place == null ? null : Number(row.place), groupSize: Number(row.size ?? 0) };
	}

	async strike(playerId: string) {
		await strikeStatement(this.store, playerId).run();
	}

	// ── End of the week ─────────────────────────────────────────────────────────────────────────────────────────

	/** Open groups of weeks before `week`, oldest first. */
	async staleGroups(week: string, limit: number): Promise<number[]> {
		const { results } = await this.db.prepare("SELECT id FROM league_groups WHERE closed = 0 AND week < ? ORDER BY id LIMIT ?").bind(week, limit).all<Row>();
		return results.map((row) => Number(row.id));
	}

	/**
	 * Closes groups of a finished week, all in SQL, in one D1 batch (one transaction):
	 * 1. final order of the ranked members (hidden players get no place): points DESC, points_at ASC, player id; with
	 *    n players and zone = min(5, n / 2): places ≤ zone with ≥ 1 point move up (not above diamond) and get the coin
	 *    chest; places > n − zone or 0 points move down (not below bronze); diamonds = base(place) × multiplier,
	 *    rounded down, only with ≥ 1 point;
	 * 2. next week's division onto the profiles;
	 * 3. one `league_reward` inbox item per ranked member (also checked against an earlier item of that week), with
	 *    the group's podium as `top` (places 1–3: id, code, marketName (null when hidden, except for the receiver),
	 *    avatar, points), my week's `points` and the group's placed `size`;
	 * 4. the groups marked closed.
	 * Every statement only touches groups still open and the mark is written last, so a second run (cron and a lazy
	 * close at once, or the cron twice) changes nothing and never pays twice. Answers how many groups it closed.
	 */
	async closeGroups(ids: number[]): Promise<number> {
		if (!ids.length) return 0;
		const now = this.store.clock();
		const set = JSON.stringify(ids);
		const results = await this.db.batch([
			this.db
				.prepare(
					`UPDATE league_members AS m SET final_place = r.place,
					   moved_to = CASE WHEN r.points >= 1 AND r.place <= r.zone THEN ${next("r.division")}
					                   WHEN r.points = 0 OR r.place > r.n - r.zone THEN ${previous("r.division")}
					                   ELSE r.division END,
					   diamonds = CASE WHEN r.points >= 1 THEN CAST(${baseDiamonds("r.place")} * ${multiplier("r.division")} AS INTEGER) ELSE 0 END,
					   chest = CASE WHEN r.points >= 1 AND r.place <= r.zone THEN 1 ELSE 0 END
					 FROM (
					   SELECT x.*, MIN(${RANKINGS.zone}, x.n / 2) AS zone FROM (
					     SELECT lm.week, lm.player_id, lm.points, g.division,
					       ROW_NUMBER() OVER (PARTITION BY lm.group_id ORDER BY lm.points DESC, lm.points_at, lm.player_id) AS place,
					       COUNT(*) OVER (PARTITION BY lm.group_id) AS n
					     FROM league_members lm JOIN league_groups g ON g.id = lm.group_id AND g.closed = 0
					       JOIN profiles p ON p.player_id = lm.player_id AND p.ranking_hidden = 0
					     WHERE lm.group_id IN (SELECT value FROM json_each(?1))
					   ) x
					 ) r WHERE m.week = r.week AND m.player_id = r.player_id`,
				)
				.bind(set),
			this.db
				.prepare(
					`UPDATE profiles SET league_division = m.moved_to
					 FROM league_members m JOIN league_groups g ON g.id = m.group_id AND g.closed = 0
					 WHERE m.player_id = profiles.player_id AND m.group_id IN (SELECT value FROM json_each(?1)) AND m.moved_to IS NOT NULL`,
				)
				.bind(set),
			this.db
				.prepare(
					`INSERT INTO inbox (player_id, kind, from_id, payload, created_at)
					 SELECT m.player_id, 'league_reward', NULL,
					   json_object('week', m.week, 'division', g.division, 'place', m.final_place, 'diamonds', m.diamonds,
					     'chest', json(CASE WHEN m.chest = 1 THEN 'true' ELSE 'false' END), 'movedTo', m.moved_to,
					     'points', m.points, 'size', (SELECT COUNT(*) FROM league_members x WHERE x.group_id = m.group_id AND x.final_place IS NOT NULL),
					     'top', (SELECT json_group_array(json_object('id', t.player_id, 'code', t.code,
					         'marketName', CASE WHEN t.name_hidden = 1 AND t.player_id <> m.player_id THEN NULL ELSE t.market_name END,
					         'avatar', t.avatar, 'points', t.points))
					       FROM (SELECT t2.player_id, t2.points, tp.code, tp.market_name, tp.name_hidden, tp.avatar
					             FROM league_members t2 JOIN profiles tp ON tp.player_id = t2.player_id
					             WHERE t2.group_id = m.group_id AND t2.final_place BETWEEN 1 AND 3 ORDER BY t2.final_place) t)), ?2
					 FROM league_members m JOIN league_groups g ON g.id = m.group_id AND g.closed = 0
					 WHERE m.group_id IN (SELECT value FROM json_each(?1)) AND m.final_place IS NOT NULL
					   AND NOT EXISTS (SELECT 1 FROM inbox i WHERE i.player_id = m.player_id AND i.kind = 'league_reward' AND json_extract(i.payload, '$.week') = m.week)`,
				)
				.bind(set, now),
			this.db.prepare("UPDATE league_groups SET closed = 1 WHERE id IN (SELECT value FROM json_each(?1)) AND closed = 0").bind(set),
		]);
		return results[3].meta.changes;
	}

	/**
	 * Closes up to `chunks` × RANKINGS.closeChunk open groups of past weeks. Answers how many it closed and whether
	 * more are left (the next cron run or league call goes on).
	 */
	async closeStale(now: number, chunks: number) {
		const week = weekOf(now);
		let closed = 0;
		for (let i = 0; i < chunks; i++) {
			const ids = await this.staleGroups(week, RANKINGS.closeChunk);
			if (!ids.length) return { closed, more: false };
			closed += await this.closeGroups(ids);
			if (ids.length < RANKINGS.closeChunk) return { closed, more: false };
		}
		return { closed, more: (await this.staleGroups(week, 1)).length > 0 };
	}

	/** League rows older than RANKINGS.keepWeeks weeks (closed groups only). */
	async housekeeping(now: number) {
		const oldest = weekOf(weekStartOf(now) - RANKINGS.keepWeeks * 7 * 24 * 60 * 60_000);
		await this.db.batch([
			this.db.prepare("DELETE FROM league_members WHERE week < ? AND group_id IN (SELECT id FROM league_groups WHERE closed = 1)").bind(oldest),
			this.db.prepare("DELETE FROM league_groups WHERE week < ? AND closed = 1").bind(oldest),
		]);
	}
}

/** One anti-cheat strike; the third hides the player from every board. */
function strikeStatement(store: Store, playerId: string) {
	return store.db
		.prepare(
			`UPDATE profiles SET ranking_hidden = CASE WHEN strikes + 1 >= ${RANKINGS.strikesToHide} THEN 1 ELSE ranking_hidden END, strikes = strikes + 1 WHERE player_id = ?`,
		)
		.bind(playerId);
}

/**
 * The cron (Monday 00:05 UTC): closes every open group of the finished week(s), chunk after chunk, then drops old
 * league rows. A run that stops half way (time, error) leaves the rest open: the next run, or the first league calls of
 * the week, close them.
 */
export async function closeWeeks(store: Store, now: number, log: (line: string) => void, maxChunks = 200) {
	const rankings = new RankingStore(store);
	const { closed, more } = await rankings.closeStale(now, maxChunks);
	if (!more) await rankings.housekeeping(now);
	log(`league close ${weekOf(now)}: ${closed} groups closed${more ? ", more left" : ""}`);
	return { closed, more };
}
