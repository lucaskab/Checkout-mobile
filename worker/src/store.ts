import type { D1Database, R2Bucket, Row } from "./cf.ts";
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

	/** The player and their save's description (one round trip). Null when the player is gone. */
	async getPlayer(id: string): Promise<{ player: PlayerRecord; save: SaveMeta | null } | null> {
		const [player, save] = await this.db.batch([
			this.db.prepare("SELECT * FROM players WHERE id = ?").bind(id),
			this.db.prepare("SELECT * FROM cloud_saves WHERE player_id = ?").bind(id),
		]);
		if (!player.results[0]) return null;
		return { player: toPlayer(player.results[0]), save: save.results[0] ? toSave(save.results[0]) : null };
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
		if (!current) {
			const result = await this.db
				.prepare(
					`INSERT INTO cloud_saves (player_id, revision, summary, device_id, updated_at, body_key, bytes) VALUES (?, ?, ?, ?, ?, ?, ?)
					 ON CONFLICT(player_id) DO NOTHING`,
				)
				.bind(playerId, revision, summary, upload.deviceId, now, key, bytes)
				.run();
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

	/** The player, their save and every restore point, for good. */
	async deletePlayer(id: string) {
		const [save, history] = await this.db.batch<{ body_key: string }>([
			this.db.prepare("DELETE FROM cloud_saves WHERE player_id = ? RETURNING body_key").bind(id),
			this.db.prepare("DELETE FROM save_history WHERE player_id = ? RETURNING body_key").bind(id),
			this.db.prepare("DELETE FROM players WHERE id = ?").bind(id),
		]);
		await this.deleteObjects([...save.results, ...history.results].map((row) => row.body_key));
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
