import type { Connect, D1Database, R2Bucket } from "./cf.ts";
import { PgClient, sqlText } from "./pg.ts";
import { cleanSummary } from "./save.ts";
import { pruneHistory, saveKey } from "./store.ts";

/**
 * The copy from the Render database (Prisma Postgres) — temporary, removed once every tester is on the new build.
 *
 * Every step is idempotent and can run again at any time (before the switch, after it, while old builds still upload
 * to Render): what is already here is skipped, and nothing here is ever overwritten by something older. The rule per
 * player, so that no progress is ever lost:
 *  - no save here yet → the Render save becomes the save (same player id, same revision: the game sees "synced");
 *  - the save here is still the copied one and Render has a newer revision → the newer one replaces it (the replaced
 *    copy becomes a restore point);
 *  - the player already uploaded here and Render got a newer revision too (an old build on another phone) → the
 *    Render save is kept as a restore point (old_id "s:…"), never dropped.
 * Restore points (save_history) are copied once each (old_id "h:<id>").
 *
 * Saves are read as Postgres' own JSON string literal (to_json(data)) and moved as bytes, so the Worker never parses
 * them; md5 of that literal (Postgres) = the R2 etag, which is how `verify` proves each copy is byte-identical.
 * Each call opens its own connection and does a small batch (the free plan's CPU limit is per request).
 */
export type MigrateDeps = { url: string; connect: Connect; db: D1Database; bucket: R2Bucket };

const ID = /^[\w-]{0,64}$/;
const decoder = new TextDecoder();
const asText = (v: unknown) => (v instanceof Uint8Array ? decoder.decode(v) : v == null ? null : String(v));

async function withOld<T>(deps: MigrateDeps, work: (pg: PgClient) => Promise<T>): Promise<T> {
	const pg = await PgClient.connect(deps.url, deps.connect);
	try {
		return await work(pg);
	} finally {
		await pg.close();
	}
}

/** The player here for a Render player: the same id, or (someone who signed in here first) the same Google/Apple account. */
async function targetOf(db: D1Database, row: Record<string, unknown>) {
	const found = await db
		.prepare("SELECT id FROM players WHERE id = ? OR (google_sub IS NOT NULL AND google_sub = ?) OR (apple_sub IS NOT NULL AND apple_sub = ?) ORDER BY id = ? DESC LIMIT 1")
		.bind(asText(row.player_id), asText(row.google_sub), asText(row.apple_sub), asText(row.player_id))
		.first<{ id: string }>();
	return found?.id ?? null;
}

const summaryText = (row: Record<string, unknown>) => JSON.stringify(cleanSummary(JSON.parse(asText(row.summary) ?? "{}")));

/** What is on each side: counts and sizes (no data). */
export async function plan(deps: MigrateDeps) {
	const old = await withOld(deps, async (pg) => {
		const [row] = await pg.objects(`SELECT
			(SELECT count(*) FROM players) AS players,
			(SELECT count(*) FROM cloud_saves) AS saves,
			(SELECT count(*) FROM save_history) AS history,
			(SELECT coalesce(max(octet_length(data)), 0) FROM cloud_saves) AS max_save_bytes,
			(SELECT coalesce(avg(octet_length(data)), 0)::bigint FROM cloud_saves) AS avg_save_bytes,
			(SELECT count(*) FROM cloud_saves WHERE octet_length(data) > 500000) AS saves_over_500kb,
			(SELECT count(*) FROM cloud_saves WHERE octet_length(data) > 1000000) AS saves_over_1mb,
			(SELECT coalesce(sum(octet_length(data)), 0) FROM cloud_saves) AS save_bytes,
			(SELECT coalesce(sum(octet_length(data)), 0) FROM save_history) AS history_bytes,
			(SELECT coalesce(max(octet_length(data)), 0) FROM save_history) AS max_history_bytes`);
		return Object.fromEntries(Object.entries(row).map(([k, v]) => [k, Number(v)]));
	});
	const [players, saves, history] = await deps.db.batch<{ n: number }>([
		deps.db.prepare("SELECT count(*) AS n FROM players"),
		deps.db.prepare("SELECT count(*) AS n FROM cloud_saves"),
		deps.db.prepare("SELECT count(*) AS n FROM save_history"),
	]);
	return { old, here: { players: players.results[0].n, saves: saves.results[0].n, history: history.results[0].n } };
}

/** Step 1: every player (small rows, all at once). Profiles here win over Render's, except where empty. */
export async function copyPlayers(deps: MigrateDeps) {
	const { db } = deps;
	const rows = await withOld(deps, (pg) =>
		pg.objects(`SELECT id, google_sub, apple_sub, apple_refresh, email, name,
			(extract(epoch from created_at) * 1000)::bigint AS created_at, (extract(epoch from last_seen) * 1000)::bigint AS last_seen
			FROM players ORDER BY id`),
	);
	const counts = { old: rows.length, inserted: 0, updated: 0, aliased: 0, failed: [] as string[] };
	for (const row of rows) {
		const id = asText(row.id) as string;
		const fields = [asText(row.google_sub), asText(row.apple_sub), asText(row.apple_refresh), asText(row.email), asText(row.name), Number(asText(row.created_at)), Number(asText(row.last_seen))];
		try {
			const target = await targetOf(db, { player_id: id, google_sub: row.google_sub, apple_sub: row.apple_sub });
			if (!target) {
				await db.prepare("INSERT INTO players (google_sub, apple_sub, apple_refresh, email, name, created_at, last_seen, id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)").bind(...fields, id).run();
				counts.inserted++;
			} else {
				await db
					.prepare(
						`UPDATE players SET google_sub = COALESCE(google_sub, ?), apple_sub = COALESCE(apple_sub, ?), apple_refresh = COALESCE(apple_refresh, ?),
						 email = COALESCE(email, ?), name = COALESCE(name, ?), created_at = MIN(created_at, ?), last_seen = MAX(last_seen, ?) WHERE id = ?`,
					)
					.bind(...fields, target)
					.run();
				if (target === id) counts.updated++;
				else counts.aliased++;
			}
		} catch (error) {
			counts.failed.push(`${id}: ${(error as Error).message}`);
		}
	}
	return counts;
}

type Outcome = "copied" | "same" | "replaced-copy" | "kept-in-history" | "already" | "older" | "no-player" | "raced";

/** Step 2: the current saves, `limit` players after `after` (player id order). */
export async function copySaves(deps: MigrateDeps, after: string, limit: number) {
	if (!ID.test(after)) throw new Error("bad cursor");
	const { db, bucket } = deps;
	return withOld(deps, async (pg) => {
		const rows = await pg.objects(
			`SELECT s.player_id, p.google_sub, p.apple_sub, s.revision, s.device_id, (extract(epoch from s.updated_at) * 1000)::bigint AS updated_at,
				s.summary::text AS summary, to_json(s.data)::text AS literal
			 FROM cloud_saves s JOIN players p ON p.id = s.player_id WHERE s.player_id > ${sqlText(after)} ORDER BY s.player_id LIMIT ${limit}`,
			["literal"],
		);
		const done: { player: string; revision: number; bytes: number; outcome: Outcome }[] = [];
		for (const row of rows) {
			const oldId = asText(row.player_id) as string;
			const revision = Number(asText(row.revision));
			const literal = row.literal as Uint8Array;
			const note = (outcome: Outcome) => done.push({ player: oldId, revision, bytes: literal.length, outcome });
			const target = await targetOf(db, row);
			if (!target) {
				note("no-player");
				continue;
			}
			const current = await db.prepare("SELECT revision, body_key, render_revision, summary, device_id, updated_at, bytes FROM cloud_saves WHERE player_id = ?").bind(target).first<Record<string, unknown>>();
			const untouched = current && current.render_revision !== null && Number(current.revision) === Number(current.render_revision);
			if (current && untouched && revision === Number(current.revision)) {
				note("same");
				continue;
			}
			if (current && untouched && revision < Number(current.revision)) {
				note("older");
				continue;
			}
			if (current && !untouched && current.render_revision !== null && revision <= Number(current.render_revision)) {
				note("already");
				continue;
			}
			const fields = [summaryText(row), asText(row.device_id), Number(asText(row.updated_at))];
			if (!current || untouched) {
				const key = saveKey(target, `${revision}r`);
				const object = await bucket.put(key, literal, { httpMetadata: { contentType: "application/json" } });
				const bytes = object?.size ?? literal.length;
				let won: boolean;
				if (!current) {
					const result = await db
						.prepare(
							`INSERT INTO cloud_saves (summary, device_id, updated_at, player_id, revision, body_key, bytes, render_revision) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
							 ON CONFLICT(player_id) DO NOTHING`,
						)
						.bind(...fields, target, revision, key, bytes, revision)
						.run();
					won = result.meta.changes === 1;
				} else {
					const results = await db.batch<{ body_key: string }>([
						db
							.prepare(
								`UPDATE cloud_saves SET summary = ?, device_id = ?, updated_at = ?, revision = ?, body_key = ?, bytes = ?, render_revision = ?
								 WHERE player_id = ? AND revision = ? AND body_key = ?`,
							)
							.bind(...fields, revision, key, bytes, revision, target, Number(current.revision), current.body_key),
						db
							.prepare(
								`INSERT INTO save_history (player_id, revision, summary, device_id, saved_at, body_key, bytes)
								 SELECT ?, ?, ?, ?, ?, ?, ? WHERE EXISTS (SELECT 1 FROM cloud_saves WHERE player_id = ? AND body_key = ?)`,
							)
							.bind(target, Number(current.revision), current.summary, current.device_id, Number(current.updated_at), current.body_key, Number(current.bytes), target, key),
						pruneHistory(db, target),
					]);
					won = results[0].meta.changes === 1;
					const pruned = results[2].results.map((r) => r.body_key);
					if (pruned.length) await bucket.delete(pruned);
				}
				if (!won) await bucket.delete(key);
				note(!won ? "raced" : current ? "replaced-copy" : "copied");
				continue;
			}
			// The player moved on here, and Render has a save this side never saw: keep it as a restore point.
			const oldKey = `s:${oldId}:${revision}`;
			if (await db.prepare("SELECT 1 AS x FROM save_history WHERE old_id = ?").bind(oldKey).first()) {
				note("already");
				continue;
			}
			const key = saveKey(target, `${revision}s`);
			const object = await bucket.put(key, literal, { httpMetadata: { contentType: "application/json" } });
			const result = await db
				.prepare(
					`INSERT INTO save_history (summary, device_id, saved_at, player_id, revision, body_key, bytes, old_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
					 ON CONFLICT(old_id) DO NOTHING`,
				)
				.bind(...fields, target, revision, key, object?.size ?? literal.length, oldKey)
				.run();
			if (result.meta.changes !== 1) await bucket.delete(key);
			note(result.meta.changes === 1 ? "kept-in-history" : "already");
		}
		return { done, next: rows.length ? (asText(rows[rows.length - 1].player_id) as string) : after, finished: rows.length < limit };
	});
}

/** Step 3: the restore points, `limit` rows after `after` (Render's history id order). */
export async function copyHistory(deps: MigrateDeps, after: string, limit: number) {
	if (!/^\d{1,18}$/.test(after)) throw new Error("bad cursor");
	const { db, bucket } = deps;
	return withOld(deps, async (pg) => {
		const rows = await pg.objects(
			`SELECT h.id, h.player_id, p.google_sub, p.apple_sub, h.revision, h.device_id, (extract(epoch from h.saved_at) * 1000)::bigint AS saved_at,
				h.summary::text AS summary, to_json(h.data)::text AS literal
			 FROM save_history h JOIN players p ON p.id = h.player_id WHERE h.id > ${after} ORDER BY h.id LIMIT ${limit}`,
			["literal"],
		);
		const counts = { copied: 0, already: 0, noPlayer: 0, bytes: 0 };
		for (const row of rows) {
			const oldKey = `h:${asText(row.id)}`;
			const target = await targetOf(db, row);
			if (!target) {
				counts.noPlayer++;
				continue;
			}
			if (await db.prepare("SELECT 1 AS x FROM save_history WHERE old_id = ?").bind(oldKey).first()) {
				counts.already++;
				continue;
			}
			const literal = row.literal as Uint8Array;
			const key = saveKey(target, `h${asText(row.id)}`);
			const object = await bucket.put(key, literal, { httpMetadata: { contentType: "application/json" } });
			const result = await db
				.prepare(
					`INSERT INTO save_history (player_id, revision, summary, device_id, saved_at, body_key, bytes, old_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
					 ON CONFLICT(old_id) DO NOTHING`,
				)
				.bind(target, Number(asText(row.revision)), summaryText(row), asText(row.device_id), Number(asText(row.saved_at)), key, object?.size ?? literal.length, oldKey)
				.run();
			if (result.meta.changes === 1) {
				counts.copied++;
				counts.bytes += literal.length;
			} else {
				await bucket.delete(key);
				counts.already++;
			}
		}
		return { ...counts, next: rows.length ? asText(rows[rows.length - 1].id) : after, finished: rows.length < limit };
	});
}

const sameSummary = (a: string, b: string) => JSON.stringify(cleanSummary(JSON.parse(a))) === JSON.stringify(cleanSummary(JSON.parse(b)));

/**
 * Proof, player by player: each Render save is here byte for byte (R2's etag = Postgres' md5 of the same literal)
 * with the same revision and summary — or the player moved on here and that Render save is accounted for.
 */
export async function verifySaves(deps: MigrateDeps, after: string, limit: number) {
	if (!ID.test(after)) throw new Error("bad cursor");
	const { db, bucket } = deps;
	const rows = await withOld(deps, (pg) =>
		pg.objects(
			`SELECT s.player_id, p.google_sub, p.apple_sub, s.revision, s.summary::text AS summary, md5(to_json(s.data)::text) AS md5
			 FROM cloud_saves s JOIN players p ON p.id = s.player_id WHERE s.player_id > ${sqlText(after)} ORDER BY s.player_id LIMIT ${limit}`,
		),
	);
	const result = { checked: 0, identical: 0, movedOn: 0, keptInHistory: 0, problems: [] as string[] };
	for (const row of rows) {
		result.checked++;
		const oldId = asText(row.player_id) as string;
		const revision = Number(row.revision);
		const target = await targetOf(db, row);
		const current = target ? await db.prepare("SELECT * FROM cloud_saves WHERE player_id = ?").bind(target).first<Record<string, unknown>>() : null;
		if (!target || !current) {
			result.problems.push(`${oldId}: ${target ? "no save here" : "no player here"}`);
			continue;
		}
		const renderRevision = current.render_revision === null ? null : Number(current.render_revision);
		if (renderRevision === revision && Number(current.revision) === revision) {
			const object = await bucket.head(String(current.body_key));
			if (object?.etag === row.md5 && sameSummary(String(current.summary), String(row.summary))) result.identical++;
			else result.problems.push(`${oldId}: revision ${revision} differs (${object ? "content or summary" : "object missing"})`);
		} else if (renderRevision !== null && revision <= renderRevision) result.movedOn++;
		else {
			const kept = await db.prepare("SELECT body_key FROM save_history WHERE old_id = ?").bind(`s:${oldId}:${revision}`).first<{ body_key: string }>();
			const object = kept ? await bucket.head(kept.body_key) : null;
			if (object?.etag === row.md5) result.keptInHistory++;
			else result.problems.push(`${oldId}: Render revision ${revision} not here (here: ${current.revision}, copied from ${renderRevision})`);
		}
	}
	return { ...result, next: rows.length ? (asText(rows[rows.length - 1].player_id) as string) : after, finished: rows.length < limit };
}

/** Proof for the restore points: each Render history row is here byte for byte (or was dropped by the 10-copies rule). */
export async function verifyHistory(deps: MigrateDeps, after: string, limit: number) {
	if (!/^\d{1,18}$/.test(after)) throw new Error("bad cursor");
	const { db, bucket } = deps;
	const rows = await withOld(deps, (pg) => pg.objects(`SELECT id, revision, md5(to_json(data)::text) AS md5 FROM save_history WHERE id > ${after} ORDER BY id LIMIT ${limit}`));
	const result = { checked: 0, identical: 0, problems: [] as string[] };
	for (const row of rows) {
		result.checked++;
		const kept = await db.prepare("SELECT body_key, revision FROM save_history WHERE old_id = ?").bind(`h:${asText(row.id)}`).first<{ body_key: string; revision: number }>();
		const object = kept ? await bucket.head(kept.body_key) : null;
		if (object?.etag === row.md5 && Number(kept?.revision) === Number(row.revision)) result.identical++;
		else result.problems.push(`history ${asText(row.id)}: ${kept ? "differs" : "not here"}`);
	}
	return { ...result, next: rows.length ? asText(rows[rows.length - 1].id) : after, finished: rows.length < limit };
}
