import type { D1Database, D1PreparedStatement, D1Result, R2Bucket, Row } from "./cf.ts";
import { newCode } from "./codes.ts";
import { DAY_MS, dayOf, MAX_LEVEL, RANKINGS, SOCIAL } from "./limits.ts";
import { cleanSummary, HISTORY_EVERY_MS, HISTORY_KEPT, type SaveMeta, type SaveSummary } from "./save.ts";

/** Who vouches for the player: Google (Android, PC, iPhone) or Apple (iPhone). */
export type Provider = "google" | "apple";
export type PlayerRecord = {
	id: string;
	provider: Provider;
	googleSub: string | null;
	appleSub: string | null;
	email: string | null;
	name: string | null;
	/** Apple's refresh token (revoked when the account is deleted), when the server has the Apple key. */
	appleRefresh: string | null;
};

export type ReplaceResult = { ok: true; save: SaveMeta } | { ok: false; current: SaveMeta | null };

/** What PUT /v1/save needs to know about the player's social profile (read with the player, no extra round trip).
 * `ranked`: the rankings columns (null until migrations/0003_rankings.sql has run). */
export type SocialSnapshot = {
	level: number;
	era: string;
	publicJson: string | null;
	rewardPending: boolean;
	ranked: { xp: number; country: string | null; hasSave: boolean } | null;
};

/** A row of `profiles` (docs/social-api.md › Data). */
export type Profile = {
	id: string;
	code: string;
	marketName: string | null;
	avatar: string | null;
	level: number;
	era: string;
	likes: number;
	publicJson: string | null;
	invitedBy: string | null;
	inviteRewarded: boolean;
	invitesRewarded: number;
	nameHidden: boolean;
	createdAt: number;
	// Rankings v1 (docs/rankings-api.md); defaults until migrations/0003_rankings.sql has run.
	xp: number;
	levelAt: number;
	country: string | null;
	optOut: boolean;
	hidden: boolean;
	strikes: number;
	division: string;
	hasSave: boolean;
};

/** A friend as the friend list and the visit see them (public_json stays raw text: spliced into the answer). */
export type FriendRow = Profile & { lastSeen: number; giftedToday: boolean; likedToday: boolean };

export type RequestRow = { id: number; owner: string; productId: string; qty: number; createdAt: number; expiresAt: number };

export type InboxRow = {
	id: number;
	kind: string;
	payload: string;
	createdAt: number;
	from: { id: string; code: string; marketName: string | null; avatar: string | null } | null;
};

/** How another player stands to the signed-in one (friend add / accept / invite redeem). */
export type Relation = {
	id: string;
	areFriends: boolean;
	/** Who invited them (to refuse circular invites). */
	invitedBy: string | null;
	/** They asked me. */
	incoming: boolean;
	/** I asked them. */
	outgoing: boolean;
	myFriends: number;
	theirFriends: number;
	myOutgoing: number;
};

export type HelpResult = { ok: true; helps: number } | { ok: false; error: "not-friends" | "already-helped" | "build-full" | "daily-limit" };

/**
 * Players and saves: D1 (SQLite) holds the players and what each save is (revision, summary, device, date, where it
 * is); R2 holds the saves themselves (up to 2 MB each, more than a D1 row may hold) and the restore points.
 *
 * An upload never overwrites an object: the new save goes to a new key, and D1 switches to it only if the cloud is
 * still at the revision the device built on (a conditional update — two phones uploading at once cannot both win).
 * Only after D1 switched is the replaced object deleted, or kept as a restore point (no copy: the history row just
 * points at it). A failure at any step leaves the previous save in place.
 */
export class Store {
	db: D1Database;
	bucket: R2Bucket;
	clock: () => number;
	historyEveryMs: number;
	log: (line: string) => void;

	constructor(db: D1Database, bucket: R2Bucket, options: { clock?: () => number; historyEveryMs?: number; log?: (line: string) => void } = {}) {
		this.db = db;
		this.bucket = bucket;
		this.clock = options.clock ?? Date.now;
		this.historyEveryMs = options.historyEveryMs ?? HISTORY_EVERY_MS;
		this.log = options.log ?? (() => {});
	}

	/**
	 * Finds or creates the player of that Google or Apple account, and reads their save (one round trip). A missing
	 * e-mail or name keeps the one saved (Apple sends the name only on the very first login).
	 */
	async signIn(provider: Provider, sub: string, email: string | null, name: string | null) {
		const column = provider === "apple" ? "apple_sub" : "google_sub";
		const now = this.clock();
		const [player, save] = await this.db.batch([
			this.db
				.prepare(
					`INSERT INTO players (id, ${column}, email, name, created_at, last_seen) VALUES (?, ?, ?, ?, ?, ?)
					 ON CONFLICT(${column}) DO UPDATE SET email = COALESCE(excluded.email, players.email),
					   name = COALESCE(excluded.name, players.name), last_seen = excluded.last_seen
					 RETURNING *`,
				)
				.bind(crypto.randomUUID(), sub, email, name, now, now),
			this.db.prepare(`SELECT * FROM cloud_saves WHERE player_id = (SELECT id FROM players WHERE ${column} = ?)`).bind(sub),
		]);
		return { player: toPlayer(player.results[0]), save: save.results[0] ? toSave(save.results[0]) : null };
	}

	async setAppleRefresh(playerId: string, token: string | null) {
		await this.db.prepare("UPDATE players SET apple_refresh = ? WHERE id = ?").bind(token, playerId).run();
	}

	/**
	 * Until migrations/0002_social.sql has run on the live database, the save routes must keep working exactly as
	 * before: a "no such table" error turns the social reads off for a minute (the social routes then answer 500).
	 */
	socialOffUntil = 0;
	socialTables() {
		return this.clock() >= this.socialOffUntil;
	}
	missingSocial(error: unknown) {
		if (!/no such table: (profiles|friends|friend_requests|inbox|daily_actions|build_helps|product_requests|name_reports)\b/i.test(String((error as Error)?.message ?? error)))
			return false;
		this.socialOffUntil = this.clock() + 60_000;
		this.log("social tables missing: run worker/migrations/0002_social.sql in the D1 console");
		return true;
	}

	/**
	 * The same for rankings: until migrations/0003_rankings.sql has run, the profile has none of its columns. A "no such
	 * column" (or a missing league table) turns the ranking columns off for a minute: saves, social and account deletion
	 * work as before; only the /v1/rankings routes answer 500.
	 */
	rankingsOffUntil = 0;
	rankingColumns() {
		return this.socialTables() && this.clock() >= this.rankingsOffUntil;
	}
	missingRankings(error: unknown) {
		if (!/no such column|has no column named|no such table: league_/i.test(String((error as Error)?.message ?? error))) return false;
		this.rankingsOffUntil = this.clock() + 60_000;
		this.log("ranking columns missing: run worker/migrations/0003_rankings.sql in the D1 console");
		return true;
	}

	/** The player, their save's description and their social snapshot (one round trip). Null when the player is gone. */
	async getPlayer(id: string): Promise<{ player: PlayerRecord; save: SaveMeta | null; social: SocialSnapshot | null } | null> {
		const withSocial = this.socialTables();
		const withRankings = withSocial && this.rankingColumns();
		const statements = [this.db.prepare("SELECT * FROM players WHERE id = ?").bind(id), this.db.prepare("SELECT * FROM cloud_saves WHERE player_id = ?").bind(id)];
		if (withSocial)
			statements.push(
				this.db.prepare(`SELECT level, era, public_json, invited_by, invite_rewarded${withRankings ? ", xp, country, has_save" : ""} FROM profiles WHERE player_id = ?`).bind(id),
			);
		let results: D1Result[];
		try {
			results = await this.db.batch<Row>(statements);
		} catch (error) {
			if (withSocial && (this.missingSocial(error) || (withRankings && this.missingRankings(error)))) return this.getPlayer(id);
			throw error;
		}
		const [player, save, profile] = results;
		if (!player.results[0]) return null;
		const p = profile?.results[0];
		const social = p
			? {
					level: Number(p.level),
					era: String(p.era),
					publicJson: str(p.public_json),
					rewardPending: p.invited_by !== null && !Number(p.invite_rewarded),
					ranked: withRankings ? { xp: Number(p.xp ?? 0), country: str(p.country), hasSave: flag(p.has_save) } : null,
				}
			: null;
		return { player: toPlayer(player.results[0]), save: save.results[0] ? toSave(save.results[0]) : null, social };
	}

	async getSave(playerId: string): Promise<SaveMeta | null> {
		const row = await this.db.prepare("SELECT * FROM cloud_saves WHERE player_id = ?").bind(playerId).first();
		return row ? toSave(row) : null;
	}

	/**
	 * The save itself (its JSON string literal) and its description. Retries when an upload replaced it between
	 * reading D1 and reading R2 (the replaced object may already be gone).
	 */
	async readSave(playerId: string, known: SaveMeta | null): Promise<{ save: SaveMeta; body: ArrayBuffer } | null> {
		let save = known;
		for (let attempt = 0; attempt < 4 && save; attempt++) {
			const object = await this.bucket.get(save.key);
			if (object) return { save, body: await object.arrayBuffer() };
			save = await this.getSave(playerId);
		}
		if (save) throw new Error(`save object missing for ${playerId}`);
		return null;
	}

	/**
	 * Replaces `current` (what the caller read and checked) with the upload, atomically: refused when another upload
	 * got there first. The replaced save becomes a restore point when it is old enough (or when the player forced the
	 * replacement); the newest HISTORY_KEPT are kept.
	 */
	async replaceSave(
		playerId: string,
		current: SaveMeta | null,
		upload: { literal: Uint8Array; summary: SaveSummary; deviceId: string; keepReplaced?: boolean },
		/** More statements for the same batch, given the new save's key (they must check the upload won, see afterUpload). */
		extra?: (key: string) => D1PreparedStatement[],
	): Promise<ReplaceResult> {
		const now = this.clock();
		const revision = (current?.revision ?? 0) + 1;
		const key = saveKey(playerId, String(revision));
		const object = await this.bucket.put(key, upload.literal, { httpMetadata: { contentType: "application/json" } });
		const bytes = object?.size ?? upload.literal.length;
		const summary = JSON.stringify(upload.summary);
		const keep = !!current && (upload.keepReplaced === true || now - current.updatedAt >= this.historyEveryMs);
		let won: boolean;
		let pruned: string[] = [];
		const more = extra ? extra(key) : [];
		if (!current) {
			const insert = this.db
				.prepare(
					`INSERT INTO cloud_saves (player_id, revision, summary, device_id, updated_at, body_key, bytes) VALUES (?, ?, ?, ?, ?, ?, ?)
					 ON CONFLICT(player_id) DO NOTHING`,
				)
				.bind(playerId, revision, summary, upload.deviceId, now, key, bytes);
			const result = more.length ? (await this.db.batch([insert, ...more]))[0] : await insert.run();
			won = result.meta.changes === 1;
		} else {
			const statements = [
				this.db
					.prepare(
						`UPDATE cloud_saves SET revision = ?, summary = ?, device_id = ?, updated_at = ?, body_key = ?, bytes = ?
						 WHERE player_id = ? AND revision = ? AND body_key = ?`,
					)
					.bind(revision, summary, upload.deviceId, now, key, bytes, playerId, current.revision, current.key),
			];
			if (keep)
				statements.push(
					// Only when the update above won (the save now points at the new object).
					this.db
						.prepare(
							`INSERT INTO save_history (player_id, revision, summary, device_id, saved_at, body_key, bytes)
							 SELECT ?, ?, ?, ?, ?, ?, ? WHERE EXISTS (SELECT 1 FROM cloud_saves WHERE player_id = ? AND body_key = ?)`,
						)
						.bind(playerId, current.revision, JSON.stringify(current.summary), current.deviceId, current.updatedAt, current.key, current.bytes, playerId, key),
					pruneHistory(this.db, playerId),
				);
			statements.push(...more);
			const results = await this.db.batch<{ body_key: string }>(statements);
			won = results[0].meta.changes === 1;
			if (keep) pruned = results[2].results.map((row) => row.body_key);
		}
		const garbage = [...pruned];
		if (!won) garbage.push(key);
		else if (current && !keep) garbage.push(current.key);
		await this.deleteObjects(garbage);
		if (!won) return { ok: false, current: await this.getSave(playerId) };
		return { ok: true, save: { revision, summary: upload.summary, deviceId: upload.deviceId, updatedAt: now, key, bytes } };
	}

	/**
	 * The player, their save and every restore point, for good — and every social row: profile, both sides of each
	 * friendship, friend requests both ways, inbox, product requests, helps, daily counters, reports by and about them.
	 * What they sent to others stays (a gift or a delivery is the receiver's now) without their id; players they
	 * invited keep "already invited" (invited_by '').
	 */
	async deletePlayer(id: string): Promise<void> {
		const withRankings = this.rankingColumns();
		const social = this.socialTables() ? [...(withRankings ? leagueDeletes(this.db, id) : []), ...socialDeletes(this.db, id)] : [];
		let results: D1Result[];
		try {
			results = await this.db.batch([
				this.db.prepare("DELETE FROM cloud_saves WHERE player_id = ? RETURNING body_key").bind(id),
				this.db.prepare("DELETE FROM save_history WHERE player_id = ? RETURNING body_key").bind(id),
				this.db.prepare("DELETE FROM players WHERE id = ?").bind(id),
				...social,
			]);
		} catch (error) {
			if (social.length && (this.missingSocial(error) || (withRankings && this.missingRankings(error)))) return this.deletePlayer(id);
			throw error;
		}
		const [save, history] = results as unknown as { results: { body_key: string }[] }[];
		await this.deleteObjects([...save.results, ...history.results].map((row) => row.body_key));
	}

	// ── Social v1 (docs/social-api.md) ──────────────────────────────────────────────────────────────────────────

	/**
	 * The signed-in player's profile, created on first use (new code; level and era from the cloud save's summary), and
	 * when their account was created. One round trip. Null when the player is gone. `counts`: also the number of
	 * friends and the inviter's code (GET/PUT /v1/social/me).
	 */
	async socialMe(
		playerId: string,
		counts = false,
		country: string | null = null,
	): Promise<{ profile: Profile; accountCreatedAt: number; friends: number; inviterCode: string | null } | null> {
		const extra = counts
			? ", (SELECT COUNT(*) FROM friends WHERE player_id = pl.id) AS friend_count, (SELECT code FROM profiles WHERE player_id = pr.invited_by) AS inviter_code"
			: "";
		for (let attempt = 0; attempt < 4; attempt++) {
			const withRankings = this.rankingColumns();
			const ensure = this.ensureProfile(playerId, country, withRankings);
			let results: D1Result[];
			try {
				results = await this.db.batch([
					...ensure,
					this.db.prepare(`SELECT pl.created_at AS account_created_at, pr.*${extra} FROM players pl LEFT JOIN profiles pr ON pr.player_id = pl.id WHERE pl.id = ?`).bind(playerId),
				]);
			} catch (error) {
				if (withRankings && this.missingRankings(error)) continue;
				throw error;
			}
			const row = results[ensure.length].results[0];
			if (!row) return null;
			// No profile yet means the random code was someone else's: draw another.
			if (row.player_id)
				return { profile: toProfile(row), accountCreatedAt: Number(row.account_created_at), friends: Number(row.friend_count ?? 0), inviterCode: str(row.inviter_code) };
		}
		throw new Error("no free invite code");
	}

	/**
	 * Statements that create the player's profile when it is missing (new code; level, era, XP from the cloud save's
	 * summary) and, with the ranking columns, keep its country: written only when it changed (`country` is the
	 * connection's, already checked: null = unknown, keep the old one).
	 */
	ensureProfile(playerId: string, country: string | null, withRankings = this.rankingColumns()): D1PreparedStatement[] {
		const now = this.clock();
		const fromSave = (field: string) => `(SELECT json_extract(summary, '$.${field}') FROM cloud_saves WHERE player_id = p.id)`;
		const hasSave = "EXISTS (SELECT 1 FROM cloud_saves WHERE player_id = p.id)";
		const statements = [
			withRankings
				? this.db
						.prepare(
							`INSERT INTO profiles (player_id, code, level, era, created_at, updated_at, xp, has_save, level_at, country)
							 SELECT p.id, ?, COALESCE(${fromSave("level")}, 1), COALESCE(${fromSave("era")}, ''), ?, ?,
							   MAX(0, CAST(COALESCE(${fromSave("xp")}, 0) AS INTEGER)), ${hasSave}, CASE WHEN ${hasSave} THEN ? ELSE 0 END, ?
							 FROM players p WHERE p.id = ? AND NOT EXISTS (SELECT 1 FROM profiles WHERE player_id = p.id) ON CONFLICT DO NOTHING`,
						)
						.bind(newCode(), now, now, now, country, playerId)
				: this.db
						.prepare(
							`INSERT INTO profiles (player_id, code, level, era, created_at, updated_at)
							 SELECT p.id, ?, COALESCE(${fromSave("level")}, 1), COALESCE(${fromSave("era")}, ''), ?, ?
							 FROM players p WHERE p.id = ? AND NOT EXISTS (SELECT 1 FROM profiles WHERE player_id = p.id) ON CONFLICT DO NOTHING`,
						)
						.bind(newCode(), now, now, playerId),
		];
		if (withRankings && country) statements.push(this.db.prepare("UPDATE profiles SET country = ? WHERE player_id = ? AND country IS NOT ?").bind(country, playerId, country));
		return statements;
	}

	/** Changes the market name and/or avatar (undefined = unchanged). A new name clears the reports and the hiding. */
	async updateProfile(playerId: string, changes: { marketName?: string; avatar?: string | null; clearReports?: boolean }) {
		const sets = ["updated_at = ?"];
		const values: unknown[] = [this.clock()];
		if (changes.marketName !== undefined) {
			sets.push("market_name = ?");
			values.push(changes.marketName);
		}
		if (changes.avatar !== undefined) {
			sets.push("avatar = ?");
			values.push(changes.avatar);
		}
		if (changes.clearReports) sets.push("name_hidden = 0");
		const statements = [this.db.prepare(`UPDATE profiles SET ${sets.join(", ")} WHERE player_id = ?`).bind(...values, playerId)];
		if (changes.clearReports) statements.push(this.db.prepare("DELETE FROM name_reports WHERE target_id = ?").bind(playerId));
		await this.db.batch(statements);
	}

	/**
	 * After an upload won: the profile's level and era from the save's summary, the public block when one was sent
	 * (undefined = keep), and the invite reward when it is due (self-guarded, see inviteReward). Only an existing profile.
	 */
	async refreshProfile(playerId: string, summary: { level: number; era: string }, publicJson: string | null | undefined) {
		const now = this.clock();
		const withPublic = publicJson !== undefined;
		await this.db.batch([
			this.db
				.prepare(`UPDATE profiles SET level = ?, era = ?, ${withPublic ? "public_json = ?, " : ""}updated_at = ? WHERE player_id = ?`)
				.bind(...[summary.level, summary.era, ...(withPublic ? [publicJson] : []), now, playerId]),
			...inviteReward(this.db, playerId, now),
		]);
	}

	/**
	 * After an upload (ranking columns present), as statements for the upload's own batch — no extra round trip: the
	 * profile's level, era, XP, has_save, the public block when sent (undefined = keep), the country when known and
	 * changed, `level_at` when the level went up (or was never set), and the anti-cheat strike (a jump of more than
	 * RANKINGS.maxLevelJump levels past the early levels since the last upload, or a level above MAX_LEVEL; the level is
	 * stored anyway). All guarded by "this upload won" (the save now points at `key`), and only an existing profile.
	 * Then the invite reward when it is due.
	 */
	afterUpload(
		playerId: string,
		key: string,
		summary: { level: number; era: string; xp: number },
		publicJson: string | null | undefined,
		country: string | null,
		rewardDue: boolean,
	): D1PreparedStatement[] {
		const now = this.clock();
		const withPublic = publicJson !== undefined;
		// SET expressions all read the row as it was before the update (SQLite), so `level` here is the old level.
		const strike = `(CASE WHEN ?1 > ${MAX_LEVEL} OR (has_save = 1 AND ?1 - level > ${RANKINGS.maxLevelJump} AND ?1 > ${RANKINGS.earlyLevels}) THEN 1 ELSE 0 END)`;
		const statements = [
			this.db
				.prepare(
					`UPDATE profiles SET level = ?1, era = ?2, xp = ?3, has_save = 1,
					   level_at = CASE WHEN ?1 > level OR level_at = 0 THEN ?4 ELSE level_at END,
					   country = COALESCE(?5, country),
					   ranking_hidden = CASE WHEN strikes + ${strike} >= ${RANKINGS.strikesToHide} THEN 1 ELSE ranking_hidden END,
					   strikes = strikes + ${strike},
					   ${withPublic ? "public_json = ?8, " : ""}updated_at = ?4
					 WHERE player_id = ?6 AND EXISTS (SELECT 1 FROM cloud_saves WHERE player_id = ?6 AND body_key = ?7)`,
				)
				.bind(...[summary.level, summary.era, summary.xp, now, country, playerId, key, ...(withPublic ? [publicJson] : [])]),
		];
		if (rewardDue) statements.push(...inviteReward(this.db, playerId, now));
		return statements;
	}

	/** The friend list (most recently seen first), their open product requests, and friend requests both ways. */
	async friendsOf(playerId: string) {
		const now = this.clock();
		const [friends, requests, incoming, outgoing] = await this.db.batch([
			this.db.prepare(`${FRIEND_SELECT} WHERE f.player_id = ? ORDER BY last_seen DESC`).bind(dayOf(now), dayOf(now), playerId),
			this.db
				.prepare(
					`SELECT r.* FROM friends f JOIN product_requests r ON r.player_id = f.friend_id AND r.status = 'open' AND r.expires_at > ?
					 WHERE f.player_id = ? ORDER BY r.id`,
				)
				.bind(now, playerId),
			this.db.prepare("SELECT pr.* FROM friend_requests q JOIN profiles pr ON pr.player_id = q.from_id WHERE q.to_id = ? ORDER BY q.created_at").bind(playerId),
			this.db.prepare("SELECT pr.* FROM friend_requests q JOIN profiles pr ON pr.player_id = q.to_id WHERE q.from_id = ? ORDER BY q.created_at").bind(playerId),
		]);
		return {
			friends: friends.results.map(toFriend),
			requests: requests.results.map(toRequest),
			incoming: incoming.results.map(toProfile),
			outgoing: outgoing.results.map(toProfile),
		};
	}

	/** A friend's profile, open requests and save description, for a visit. Null when they are not friends. */
	async friendMarket(playerId: string, friendId: string) {
		const now = this.clock();
		const [friend, requests, save] = await this.db.batch([
			this.db.prepare(`${FRIEND_SELECT} WHERE f.player_id = ? AND f.friend_id = ?`).bind(dayOf(now), dayOf(now), playerId, friendId),
			this.db.prepare("SELECT * FROM product_requests WHERE player_id = ? AND status = 'open' AND expires_at > ? ORDER BY id").bind(friendId, now),
			this.db.prepare("SELECT * FROM cloud_saves WHERE player_id = ? AND EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?)").bind(friendId, playerId, friendId),
		]);
		if (!friend.results[0]) return null;
		return { friend: toFriend(friend.results[0]), requests: requests.results.map(toRequest), save: save.results[0] ? toSave(save.results[0]) : null };
	}

	/** How the player found by code (or id) stands to me. Null when there is no such profile. */
	async relation(playerId: string, other: { code: string } | { id: string }): Promise<Relation | null> {
		const row = await this.db
			.prepare(
				`SELECT pr.player_id AS id, pr.invited_by,
				   EXISTS (SELECT 1 FROM friends WHERE player_id = ?1 AND friend_id = pr.player_id) AS are_friends,
				   EXISTS (SELECT 1 FROM friend_requests WHERE from_id = pr.player_id AND to_id = ?1) AS incoming,
				   EXISTS (SELECT 1 FROM friend_requests WHERE from_id = ?1 AND to_id = pr.player_id) AS outgoing,
				   (SELECT COUNT(*) FROM friends WHERE player_id = ?1) AS my_friends,
				   (SELECT COUNT(*) FROM friends WHERE player_id = pr.player_id) AS their_friends,
				   (SELECT COUNT(*) FROM friend_requests WHERE from_id = ?1) AS my_outgoing
				 FROM profiles pr WHERE ${"code" in other ? "pr.code" : "pr.player_id"} = ?2`,
			)
			.bind(playerId, "code" in other ? other.code : other.id)
			.first();
		if (!row) return null;
		return {
			id: String(row.id),
			invitedBy: str(row.invited_by),
			areFriends: !!Number(row.are_friends),
			incoming: !!Number(row.incoming),
			outgoing: !!Number(row.outgoing),
			myFriends: Number(row.my_friends),
			theirFriends: Number(row.their_friends),
			myOutgoing: Number(row.my_outgoing),
		};
	}

	/** A friend request (and its inbox item), unless one is already pending or the outgoing limit is reached. */
	async requestFriend(fromId: string, toId: string) {
		const now = this.clock();
		const allowed = `NOT EXISTS (SELECT 1 FROM friend_requests WHERE from_id = ? AND to_id = ?) AND (SELECT COUNT(*) FROM friend_requests WHERE from_id = ?) < ${SOCIAL.maxOutgoingRequests}`;
		const guard = [fromId, toId, fromId];
		const [, inserted] = await this.db.batch([
			this.db.prepare(`INSERT INTO inbox (player_id, kind, from_id, payload, created_at) SELECT ?, 'friend_request', ?, '{}', ? WHERE ${allowed}`).bind(toId, fromId, now, ...guard),
			this.db.prepare(`INSERT INTO friend_requests (from_id, to_id, created_at) SELECT ?, ?, ? WHERE ${allowed} ON CONFLICT DO NOTHING`).bind(fromId, toId, now, ...guard),
		]);
		return inserted.meta.changes === 1;
	}

	/**
	 * Makes two players friends — both rows, unless either already has the maximum (checked inside the write, so two
	 * accepts at once cannot pass it) — clears the requests between them and tells `notify` (friend_added). Answers
	 * whether they are friends now.
	 */
	async befriend(a: string, b: string, via: "code" | "invite", notify: string) {
		const statements = befriendStatements(this.db, a, b, via, notify, this.clock());
		const results = await this.db.batch([...statements, this.db.prepare("SELECT EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?) AS friends").bind(a, b)]);
		return { friends: !!Number(results[results.length - 1].results[0]?.friends), made: results[1].meta.changes === 1 };
	}

	/**
	 * Redeems an invite: records who invited me (only if nobody did yet), makes us friends when both have room, and
	 * sends the invite rewards right away if I am already at the reward level. One transaction.
	 */
	async redeemInvite(playerId: string, inviterId: string) {
		const now = this.clock();
		const unclaimed = "(SELECT invited_by FROM profiles WHERE player_id = ?) IS NULL";
		const statements = befriendStatements(this.db, playerId, inviterId, "invite", inviterId, now, { sql: unclaimed, values: [playerId] });
		const results = await this.db.batch([
			...statements,
			this.db.prepare("UPDATE profiles SET invited_by = ?, updated_at = ? WHERE player_id = ? AND invited_by IS NULL").bind(inviterId, now, playerId),
			...inviteReward(this.db, playerId, now),
			this.db.prepare("SELECT EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?) AS friends").bind(playerId, inviterId),
		]);
		return { claimed: results[statements.length].meta.changes === 1, friends: !!Number(results[results.length - 1].results[0]?.friends) };
	}

	async declineFriend(playerId: string, fromId: string) {
		await this.db.prepare("DELETE FROM friend_requests WHERE from_id = ? AND to_id = ?").bind(fromId, playerId).run();
	}

	/** Ends a friendship (both rows) and drops any friend request between the two. */
	async removeFriend(playerId: string, friendId: string) {
		await this.db.batch([
			this.db.prepare("DELETE FROM friends WHERE (player_id = ? AND friend_id = ?) OR (player_id = ? AND friend_id = ?)").bind(playerId, friendId, friendId, playerId),
			this.db.prepare("DELETE FROM friend_requests WHERE (from_id = ? AND to_id = ?) OR (from_id = ? AND to_id = ?)").bind(playerId, friendId, friendId, playerId),
		]);
	}

	/** A market-name report; the third distinct reporter hides the name. False when there is no such player. */
	async reportName(reporterId: string, targetId: string) {
		const now = this.clock();
		const [, , found] = await this.db.batch([
			this.db
				.prepare(
					`INSERT INTO name_reports (target_id, reporter_id, created_at) SELECT ?, ?, ?
					 WHERE EXISTS (SELECT 1 FROM profiles WHERE player_id = ? AND market_name IS NOT NULL) ON CONFLICT DO NOTHING`,
				)
				.bind(targetId, reporterId, now, targetId),
			this.db
				.prepare(`UPDATE profiles SET name_hidden = 1 WHERE player_id = ? AND name_hidden = 0 AND (SELECT COUNT(*) FROM name_reports WHERE target_id = ?) >= ${SOCIAL.reportsToHide}`)
				.bind(targetId, targetId),
			this.db.prepare("SELECT 1 AS found FROM profiles WHERE player_id = ?").bind(targetId),
		]);
		return found.results.length > 0;
	}

	/**
	 * A once-a-day action towards a friend (gift or like): the inbox item, the daily mark (and the like counter) are
	 * written together, all guarded by "friends and not yet today" inside the write. Answers the outcome and, for a
	 * like, the friend's likes.
	 */
	async daily(kind: "gift" | "like", fromId: string, toId: string): Promise<{ result: "ok" | "not-friends" | "already-today"; likes: number }> {
		const now = this.clock();
		const day = dayOf(now);
		const guard = `EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?)
			AND NOT EXISTS (SELECT 1 FROM daily_actions WHERE player_id = ? AND day = ? AND kind = '${kind}' AND target = ?)`;
		const values = [fromId, toId, fromId, day, toId];
		const statements = [
			this.db.prepare(`INSERT INTO inbox (player_id, kind, from_id, payload, created_at) SELECT ?, '${kind}', ?, '{}', ? WHERE ${guard}`).bind(toId, fromId, now, ...values),
		];
		if (kind === "like") statements.push(this.db.prepare(`UPDATE profiles SET likes_total = likes_total + 1 WHERE player_id = ? AND ${guard}`).bind(toId, ...values));
		statements.push(
			this.db.prepare(`INSERT INTO daily_actions (player_id, day, kind, target) SELECT ?, ?, '${kind}', ? WHERE ${guard} ON CONFLICT DO NOTHING`).bind(fromId, day, toId, ...values),
			this.db.prepare("DELETE FROM daily_actions WHERE player_id = ? AND day < ?").bind(fromId, day),
			this.db
				.prepare("SELECT EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?) AS friends, (SELECT likes_total FROM profiles WHERE player_id = ?) AS likes")
				.bind(fromId, toId, toId),
		);
		const results = await this.db.batch(statements);
		const marked = results[statements.length - 3].meta.changes === 1;
		const check = results[statements.length - 1].results[0] ?? {};
		return { result: marked ? "ok" : Number(check.friends) ? "already-today" : "not-friends", likes: Number(check.likes ?? 0) };
	}

	/** The friend's public block (to check a build id) and whether we are friends. */
	async helpTarget(helperId: string, ownerId: string) {
		const row = await this.db
			.prepare("SELECT public_json, EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?) AS friends FROM profiles WHERE player_id = ?")
			.bind(helperId, ownerId, ownerId)
			.first();
		return { friends: !!Number(row?.friends), publicJson: str(row?.public_json) };
	}

	/**
	 * A help on a friend's build: one per helper per build, at most SOCIAL.maxHelpsPerBuild per build and
	 * SOCIAL.maxHelpsGivenPerDay per helper per UTC day — all checked inside the write (two helps at once cannot pass
	 * the maximum). The inbox item is written with it.
	 */
	async help(helperId: string, ownerId: string, buildId: string): Promise<HelpResult> {
		const now = this.clock();
		const dayStart = dayOf(now) * DAY_MS;
		const guard = `EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?)
			AND NOT EXISTS (SELECT 1 FROM build_helps WHERE owner_id = ? AND build_id = ? AND helper_id = ?)
			AND (SELECT COUNT(*) FROM build_helps WHERE owner_id = ? AND build_id = ?) < ${SOCIAL.maxHelpsPerBuild}
			AND (SELECT COUNT(*) FROM build_helps WHERE helper_id = ? AND created_at >= ?) < ${SOCIAL.maxHelpsGivenPerDay}`;
		const values = [helperId, ownerId, ownerId, buildId, helperId, ownerId, buildId, helperId, dayStart];
		const payload = JSON.stringify({ buildId, minutes: SOCIAL.helpMinutes });
		const [, inserted, , check] = await this.db.batch([
			this.db.prepare(`INSERT INTO inbox (player_id, kind, from_id, payload, created_at) SELECT ?, 'help', ?, ?, ? WHERE ${guard}`).bind(ownerId, helperId, payload, now, ...values),
			this.db.prepare(`INSERT INTO build_helps (owner_id, build_id, helper_id, created_at) SELECT ?, ?, ?, ? WHERE ${guard} ON CONFLICT DO NOTHING`).bind(ownerId, buildId, helperId, now, ...values),
			this.db.prepare("DELETE FROM build_helps WHERE owner_id = ? AND created_at < ?").bind(ownerId, now - SOCIAL.keepHelpsMs),
			this.db
				.prepare(
					`SELECT (SELECT COUNT(*) FROM build_helps WHERE owner_id = ? AND build_id = ?) AS helps,
					   EXISTS (SELECT 1 FROM build_helps WHERE owner_id = ? AND build_id = ? AND helper_id = ?) AS helped,
					   (SELECT COUNT(*) FROM build_helps WHERE helper_id = ? AND created_at >= ?) AS today,
					   EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?) AS friends`,
				)
				.bind(ownerId, buildId, ownerId, buildId, helperId, helperId, dayStart, helperId, ownerId),
		]);
		const c = check.results[0] ?? {};
		if (inserted.meta.changes === 1) return { ok: true, helps: Number(c.helps) };
		if (!Number(c.friends)) return { ok: false, error: "not-friends" };
		if (Number(c.helped)) return { ok: false, error: "already-helped" };
		if (Number(c.helps) >= SOCIAL.maxHelpsPerBuild) return { ok: false, error: "build-full" };
		return { ok: false, error: "daily-limit" };
	}

	/** My open requests and my friends' (not expired). */
	async requestsFor(playerId: string) {
		const now = this.clock();
		const [mine, friends] = await this.db.batch([
			this.db.prepare("SELECT * FROM product_requests WHERE player_id = ? AND status = 'open' AND expires_at > ? ORDER BY id").bind(playerId, now),
			this.db
				.prepare(
					`SELECT r.* FROM friends f JOIN product_requests r ON r.player_id = f.friend_id AND r.status = 'open' AND r.expires_at > ?
					 WHERE f.player_id = ? ORDER BY r.id`,
				)
				.bind(now, playerId),
		]);
		return { mine: mine.results.map(toRequest), friends: friends.results.map(toRequest) };
	}

	/** A new product request, unless SOCIAL.maxOpenRequests are open (checked inside the write). Null = limit. */
	async createRequest(playerId: string, productId: string, qty: number): Promise<RequestRow | null> {
		const now = this.clock();
		const [, , created] = await this.db.batch([
			// Housekeeping first: expired ones stop counting, old closed ones go.
			this.db.prepare("UPDATE product_requests SET status = 'expired' WHERE player_id = ? AND status = 'open' AND expires_at <= ?").bind(playerId, now),
			this.db.prepare("DELETE FROM product_requests WHERE player_id = ? AND status != 'open' AND created_at < ?").bind(playerId, now - SOCIAL.keepClosedRequestsMs),
			this.db
				.prepare(
					`INSERT INTO product_requests (player_id, product_id, qty, status, created_at, expires_at)
					 SELECT ?, ?, ?, 'open', ?, ? WHERE (SELECT COUNT(*) FROM product_requests WHERE player_id = ? AND status = 'open') < ${SOCIAL.maxOpenRequests}
					 RETURNING *`,
				)
				.bind(playerId, productId, qty, now, now + SOCIAL.requestTtlMs, playerId),
		]);
		return created.results[0] ? toRequest(created.results[0]) : null;
	}

	/** Cancels one of my open requests. False when there is no such open request of mine. */
	async cancelRequest(playerId: string, requestId: number) {
		const result = await this.db.prepare("UPDATE product_requests SET status = 'cancelled' WHERE id = ? AND player_id = ? AND status = 'open'").bind(requestId, playerId).run();
		return result.meta.changes === 1;
	}

	/**
	 * Fulfils a friend's request — atomically: the two inbox items (delivery + request_fulfilled) are inserted in the
	 * same transaction as `UPDATE … WHERE status = 'open' AND expires_at > now`, all guarded by that same condition and
	 * written before the update flips it, so either all three happen or none. The update's changes decide the answer;
	 * when it lost (someone else first, cancelled, expired) nothing was delivered.
	 */
	async fulfillRequest(playerId: string, requestId: number): Promise<"ok" | "not-found" | "not-friends" | "taken"> {
		const now = this.clock();
		const guard = `r.id = ? AND r.status = 'open' AND r.expires_at > ? AND EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = r.player_id)`;
		const values = [requestId, now, playerId];
		const results = await this.db.batch([
			this.db
				.prepare(
					`INSERT INTO inbox (player_id, kind, from_id, payload, created_at)
					 SELECT r.player_id, 'delivery', ?, json_object('requestId', r.id, 'productId', r.product_id, 'qty', r.qty), ? FROM product_requests r WHERE ${guard}`,
				)
				.bind(playerId, now, ...values),
			this.db
				.prepare(
					`INSERT INTO inbox (player_id, kind, from_id, payload, created_at)
					 SELECT r.player_id, 'request_fulfilled', ?, json_object('requestId', r.id), ? FROM product_requests r WHERE ${guard}`,
				)
				.bind(playerId, now, ...values),
			this.db
				.prepare(
					`UPDATE product_requests SET status = 'fulfilled', fulfilled_by = ? WHERE id = ? AND status = 'open' AND expires_at > ?
					 AND EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = product_requests.player_id)`,
				)
				.bind(playerId, requestId, now, playerId),
			this.db
				.prepare("SELECT r.player_id, EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = r.player_id) AS friends FROM product_requests r WHERE r.id = ?")
				.bind(playerId, requestId),
		]);
		if (results[2].meta.changes === 1) return "ok";
		const row = results[3].results[0];
		if (!row) return "not-found";
		return Number(row.friends) ? "taken" : "not-friends";
	}

	/**
	 * Unacked inbox items, oldest first, at most SOCIAL.inboxPage. Gifts beyond what the player may still claim today
	 * (SOCIAL.maxGiftsClaimedPerDay minus gifts acked today) stay on the server for the next days.
	 */
	async inbox(playerId: string): Promise<InboxRow[]> {
		const dayStart = dayOf(this.clock()) * DAY_MS;
		const { results } = await this.db
			.prepare(
				`SELECT i.id, i.kind, i.payload, i.created_at, i.from_id, pr.code, pr.market_name, pr.avatar, pr.name_hidden FROM (
				   SELECT *, CASE WHEN kind = 'gift' THEN ROW_NUMBER() OVER (PARTITION BY kind = 'gift' ORDER BY id) END AS gift_n
				   FROM inbox WHERE player_id = ? AND acked_at IS NULL
				 ) i LEFT JOIN profiles pr ON pr.player_id = i.from_id
				 WHERE i.gift_n IS NULL OR i.gift_n <= ${SOCIAL.maxGiftsClaimedPerDay} - (SELECT COUNT(*) FROM inbox WHERE player_id = ? AND acked_at >= ? AND kind = 'gift')
				 ORDER BY i.id LIMIT ${SOCIAL.inboxPage}`,
			)
			.bind(playerId, playerId, dayStart)
			.all();
		return results.map((row) => ({
			id: Number(row.id),
			kind: String(row.kind),
			payload: String(row.payload),
			createdAt: Number(row.created_at),
			from: row.code ? { id: String(row.from_id), code: String(row.code), marketName: Number(row.name_hidden) ? null : str(row.market_name), avatar: str(row.avatar) } : null,
		}));
	}

	/** Acks inbox items (only the player's own, unacked ones) and drops the ones acked long ago. */
	async ackInbox(playerId: string, ids: number[]) {
		const now = this.clock();
		await this.db.batch([
			this.db.prepare("UPDATE inbox SET acked_at = ? WHERE player_id = ? AND acked_at IS NULL AND id IN (SELECT value FROM json_each(?))").bind(now, playerId, JSON.stringify(ids)),
			this.db.prepare("DELETE FROM inbox WHERE player_id = ? AND acked_at < ?").bind(playerId, now - SOCIAL.keepAckedMs),
		]);
	}

	/** The invite landing page's lookup: the market name behind a code (null when unknown, unnamed or hidden). */
	async marketNameByCode(code: string) {
		const row = await this.db.prepare("SELECT market_name, name_hidden FROM profiles WHERE code = ?").bind(code).first();
		return row && !Number(row.name_hidden) ? str(row.market_name) : null;
	}

	/** Objects nothing points at any more. A failure only leaves an orphan behind (never a missing save). */
	async deleteObjects(keys: string[]) {
		try {
			for (let i = 0; i < keys.length; i += 1000) await this.bucket.delete(keys.slice(i, i + 1000));
		} catch (error) {
			this.log(`r2 delete failed: ${(error as Error)?.message ?? error}`);
		}
	}
}

/** Keeps the newest HISTORY_KEPT restore points of a player; answers the keys of the objects it dropped. */
export function pruneHistory(db: D1Database, playerId: string) {
	return db
		.prepare(
			`DELETE FROM save_history WHERE player_id = ? AND id NOT IN
			   (SELECT id FROM save_history WHERE player_id = ? ORDER BY saved_at DESC, id DESC LIMIT ${HISTORY_KEPT})
			 RETURNING body_key`,
		)
		.bind(playerId, playerId);
}

// ── Social statements shared by several store methods ───────────────────────────────────────────────────────

/** A friend as seen by f.player_id: profile, last seen (last upload or login), gifted/liked today. Binds: day, day. */
const FRIEND_SELECT = `SELECT pr.*, MAX(COALESCE(s.updated_at, 0), COALESCE(pl.last_seen, 0)) AS last_seen,
	  EXISTS (SELECT 1 FROM daily_actions d WHERE d.player_id = f.player_id AND d.day = ? AND d.kind = 'gift' AND d.target = f.friend_id) AS gifted,
	  EXISTS (SELECT 1 FROM daily_actions d WHERE d.player_id = f.player_id AND d.day = ? AND d.kind = 'like' AND d.target = f.friend_id) AS liked
	FROM friends f JOIN profiles pr ON pr.player_id = f.friend_id LEFT JOIN players pl ON pl.id = f.friend_id LEFT JOIN cloud_saves s ON s.player_id = f.friend_id`;

/**
 * Friendship between a and b, as statements for one batch. The inbox item for `notify` and the first row are guarded
 * by "both below the friend maximum and not friends yet" (plus `extra`), evaluated before either is written; the
 * second row and the clean-up of requests follow the first row (so a pair is never half made).
 */
function befriendStatements(db: D1Database, a: string, b: string, via: "code" | "invite", notify: string, now: number, extra?: { sql: string; values: unknown[] }) {
	const guard = `(SELECT COUNT(*) FROM friends WHERE player_id = ?) < ${SOCIAL.maxFriends} AND (SELECT COUNT(*) FROM friends WHERE player_id = ?) < ${SOCIAL.maxFriends}
		AND NOT EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?)${extra ? ` AND ${extra.sql}` : ""}`;
	const values = [a, b, a, b, ...(extra?.values ?? [])];
	const paired = "EXISTS (SELECT 1 FROM friends WHERE player_id = ? AND friend_id = ?)";
	return [
		db
			.prepare(`INSERT INTO inbox (player_id, kind, from_id, payload, created_at) SELECT ?, 'friend_added', ?, ?, ? WHERE ${guard}`)
			.bind(notify, notify === a ? b : a, JSON.stringify({ via }), now, ...values),
		db.prepare(`INSERT INTO friends (player_id, friend_id, created_at) SELECT ?, ?, ? WHERE ${guard} ON CONFLICT DO NOTHING`).bind(a, b, now, ...values),
		db.prepare(`INSERT INTO friends (player_id, friend_id, created_at) SELECT ?, ?, ? WHERE ${paired} ON CONFLICT DO NOTHING`).bind(b, a, now, a, b),
		db
			.prepare(`DELETE FROM friend_requests WHERE ((from_id = ? AND to_id = ?) OR (from_id = ? AND to_id = ?)) AND ${paired}`)
			.bind(a, b, b, a, a, b),
	];
}

const INVITER_REWARD = `CASE invites_rewarded ${SOCIAL.inviteMilestones
	.map((m) => `WHEN ${m} THEN '${JSON.stringify({ diamonds: SOCIAL.inviteRewardDiamonds, role: "inviter", milestone: m })}'`)
	.join(" ")} ELSE '${JSON.stringify({ diamonds: SOCIAL.inviteRewardDiamonds, role: "inviter" })}' END`;
const INVITED_REWARD = JSON.stringify({ diamonds: SOCIAL.inviteRewardDiamonds, role: "invited" });

/**
 * The invite reward, as statements for one batch: when the invited player (playerId) has an inviter, is at the
 * reward level and was not rewarded yet, the inviter's count goes up, both get an invite_reward inbox item (the
 * inviter's carries the milestone when the new count is one) and the invited player is marked rewarded. Every
 * statement checks that same condition and the mark is written last, so all happen or none, and never twice
 * (D1 runs batches one at a time). An inviter whose account is gone ('') gets nothing; the invited player still does.
 */
export function inviteReward(db: D1Database, playerId: string, now: number) {
	const due = `invited_by IS NOT NULL AND invite_rewarded = 0 AND level >= ${SOCIAL.inviteRewardLevel}`;
	const dueMe = `EXISTS (SELECT 1 FROM profiles WHERE player_id = ? AND ${due})`;
	const inviter = "(SELECT invited_by FROM profiles WHERE player_id = ?)";
	return [
		db.prepare(`UPDATE profiles SET invites_rewarded = invites_rewarded + 1 WHERE player_id = ${inviter} AND ${dueMe}`).bind(playerId, playerId),
		db
			.prepare(`INSERT INTO inbox (player_id, kind, from_id, payload, created_at) SELECT player_id, 'invite_reward', ?, ${INVITER_REWARD}, ? FROM profiles WHERE player_id = ${inviter} AND ${dueMe}`)
			.bind(playerId, now, playerId, playerId),
		db
			.prepare(`INSERT INTO inbox (player_id, kind, from_id, payload, created_at) SELECT player_id, 'invite_reward', NULLIF(invited_by, ''), ?, ? FROM profiles WHERE player_id = ? AND ${due}`)
			.bind(INVITED_REWARD, now, playerId),
		db.prepare(`UPDATE profiles SET invite_rewarded = 1 WHERE player_id = ? AND ${due}`).bind(playerId),
	];
}

/** A deleted player's league rows (their group keeps one member less). */
function leagueDeletes(db: D1Database, id: string) {
	return [
		db.prepare("UPDATE league_groups SET members = members - 1 WHERE id IN (SELECT group_id FROM league_members WHERE player_id = ?)").bind(id),
		db.prepare("DELETE FROM league_members WHERE player_id = ?").bind(id),
	];
}

/** Every social row of a deleted player (see Store.deletePlayer). */
function socialDeletes(db: D1Database, id: string) {
	return [
		"DELETE FROM friends WHERE (player_id, friend_id) IN (SELECT friend_id, player_id FROM friends WHERE player_id = ?)",
		"DELETE FROM friends WHERE player_id = ?",
		"DELETE FROM friend_requests WHERE from_id = ?",
		"DELETE FROM friend_requests WHERE to_id = ?",
		"DELETE FROM inbox WHERE player_id = ?",
		"UPDATE inbox SET from_id = NULL WHERE from_id = ?",
		"DELETE FROM daily_actions WHERE player_id = ?",
		"DELETE FROM daily_actions WHERE target = ?",
		"DELETE FROM build_helps WHERE owner_id = ?",
		"DELETE FROM build_helps WHERE helper_id = ?",
		"DELETE FROM product_requests WHERE player_id = ?",
		"UPDATE product_requests SET fulfilled_by = NULL WHERE fulfilled_by = ?",
		"DELETE FROM name_reports WHERE target_id = ?",
		"DELETE FROM name_reports WHERE reporter_id = ?",
		"UPDATE profiles SET invited_by = '' WHERE invited_by = ?",
		"DELETE FROM profiles WHERE player_id = ?",
	].map((sql) => db.prepare(sql).bind(id));
}

/** A new, never reused R2 key for a save of that player. */
export const saveKey = (playerId: string, label: string) => `saves/${playerId}/${label}-${crypto.randomUUID().slice(0, 8)}.json`;

const str = (value: unknown) => (typeof value === "string" ? value : null);

export function toPlayer(row: Row): PlayerRecord {
	return {
		id: String(row.id),
		provider: row.apple_sub ? "apple" : "google",
		googleSub: str(row.google_sub),
		appleSub: str(row.apple_sub),
		email: str(row.email),
		name: str(row.name),
		appleRefresh: str(row.apple_refresh),
	};
}

export function toSave(row: Row): SaveMeta {
	return {
		revision: Number(row.revision),
		summary: cleanSummary(JSON.parse(String(row.summary))),
		deviceId: String(row.device_id),
		updatedAt: Number(row.updated_at),
		key: String(row.body_key),
		bytes: Number(row.bytes),
	};
}

const flag = (value: unknown) => !!Number(value);

export function toProfile(row: Row): Profile {
	return {
		id: String(row.player_id),
		code: String(row.code),
		marketName: str(row.market_name),
		avatar: str(row.avatar),
		level: Number(row.level),
		era: String(row.era ?? ""),
		likes: Number(row.likes_total ?? 0),
		publicJson: str(row.public_json),
		invitedBy: str(row.invited_by),
		inviteRewarded: flag(row.invite_rewarded),
		invitesRewarded: Number(row.invites_rewarded ?? 0),
		nameHidden: flag(row.name_hidden),
		createdAt: Number(row.created_at),
		xp: Number(row.xp ?? 0),
		levelAt: Number(row.level_at ?? 0),
		country: str(row.country),
		optOut: flag(row.ranking_opt_out),
		hidden: flag(row.ranking_hidden),
		strikes: Number(row.strikes ?? 0),
		division: typeof row.league_division === "string" ? row.league_division : "bronze",
		hasSave: flag(row.has_save),
	};
}

export function toFriend(row: Row): FriendRow {
	return { ...toProfile(row), lastSeen: Number(row.last_seen ?? 0), giftedToday: flag(row.gifted), likedToday: flag(row.liked) };
}

export function toRequest(row: Row): RequestRow {
	return {
		id: Number(row.id),
		owner: String(row.player_id),
		productId: String(row.product_id),
		qty: Number(row.qty),
		createdAt: Number(row.created_at),
		expiresAt: Number(row.expires_at),
	};
}
