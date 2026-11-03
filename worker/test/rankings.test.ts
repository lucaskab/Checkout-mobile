import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { describe, test } from "node:test";
import { createApp } from "../src/app.ts";
import { DAY_MS, MAX_LEVEL, maxPointsPerDay, RANKINGS, weekOf, weekStartOf } from "../src/limits.ts";
import { closeWeeks, RankingStore } from "../src/ranking-store.ts";
import type { BoardCache } from "../src/rankings.ts";
import { Store } from "../src/store.ts";
import { fakeD1, fakeR2 } from "./fakes.ts";

// Rankings v1 (docs/rankings-api.md) against the Worker's own code: real schema on node:sqlite, R2 in memory.
/** A league_reward payload without its podium (`top`, checked on its own). */
const noTop = ({ top, points, size, ...rest }: any) => (assert.equal(top.length, 3), assert.equal(typeof points, "number"), assert.equal(size, 30), rest);
const SECRET = "test-secret-test-secret-test-secret-123";
// Wednesday 2026-11-04 10:00 UTC: ISO week 2026-W45, third day of the week.
const T0 = Date.UTC(2026, 10, 4, 10);
const WEEK = "2026-W45";
const save = (level: number, xp = 0, era = "mesinha") =>
	JSON.stringify({ state: { coins: 100, era: { id: era }, market: { level, totalExperience: xp }, logistics: { premiumCurrency: 10 }, day: { dayNumber: 2 } }, version: 45 });

type User = { name: string; token: string; id: string; code: string; revision: number };

/** The Cache API as a map (what caches.default does for one data center), with what was put. */
function fakeCache(): BoardCache & { entries: Map<string, { body: string; headers: Headers }> } {
	const entries = new Map<string, { body: string; headers: Headers }>();
	return {
		entries,
		async match(key) {
			const e = entries.get(key);
			return e ? new Response(e.body, { headers: e.headers }) : undefined;
		},
		async put(key, response) {
			entries.set(key, { body: await response.text(), headers: response.headers });
		},
	};
}

function world(options: { db?: ReturnType<typeof fakeD1>; cache?: ReturnType<typeof fakeCache> } = {}) {
	const clock = { now: T0 };
	const db = options.db ?? fakeD1();
	const bucket = fakeR2();
	const logs: string[] = [];
	const cache = options.cache ?? fakeCache();
	const store = new Store(db, bucket, { clock: () => clock.now, log: (l) => logs.push(l) });
	const makeApp = () =>
		createApp({
			store,
			verifyGoogle: async (t) => (t.startsWith("token-") ? { sub: `g-${t.slice(6)}`, email: `${t.slice(6)}@example.com`, name: t.slice(6) } : null),
			sessionSecret: SECRET,
			rateLimit: 1_000_000,
			now: () => clock.now,
			log: (l) => logs.push(l),
			cache,
		});
	let app = makeApp();
	const call = async (method: string, path: string, body?: unknown, token?: string, country?: string) => {
		const response = await app(
			new Request(`https://checkout-server.example${path}`, {
				method,
				headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
				body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
			}),
			"1.2.3.4",
			country,
		);
		const text = await response.text();
		let parsed: any = null;
		try {
			parsed = text ? JSON.parse(text) : null;
		} catch {}
		return { status: response.status, body: parsed, text, headers: response.headers };
	};
	/** A signed-in player with a profile (opened the Ranking/Amigos window) and, with `level`, a cloud save. */
	const user = async (name: string, level?: number, xp = 0, country?: string): Promise<User> => {
		const login = (await call("POST", "/v1/auth/google", { idToken: `token-${name}` })).body;
		const me = (await call("GET", "/v1/social/me", undefined, login.token, country)).body;
		const u = { name, token: login.token, id: login.player.id, code: me.code, revision: login.save?.revision ?? 0 };
		if (level !== undefined) await upload(u, level, xp, country);
		return u;
	};
	const upload = async (u: User, level: number, xp = 0, country?: string) => {
		const body = `{"baseRevision":${u.revision},"data":${JSON.stringify(save(level, xp))},"deviceId":"phone","force":false}`;
		const r = await call("PUT", "/v1/save", body, u.token, country);
		assert.equal(r.status, 200, r.text);
		u.revision = r.body.revision;
		return r;
	};
	const points = (u: User, n: number, week = weekOf(clock.now)) => call("POST", "/v1/rankings/league/points", { week, points: n }, u.token);
	const league = async (u: User) => (await call("GET", "/v1/rankings/league", undefined, u.token)).body;
	const inbox = async (u: User) => ((await call("GET", "/v1/social/inbox", undefined, u.token)).body.items as any[]).filter((i) => i.kind === "league_reward");
	const rows = (sql: string, ...values: (string | number)[]) => db.sqlite.prepare(sql).all(...values) as Record<string, any>[];
	const profile = (u: User) => rows("SELECT * FROM profiles WHERE player_id = ?", u.id)[0];
	/** Spy on the SQL each batch runs. */
	const sql: string[] = [];
	const batch = db.batch.bind(db);
	db.batch = (async (statements: any[]) => {
		for (const s of statements) sql.push(s.sql);
		return batch(statements);
	}) as typeof db.batch;
	const newIsolate = () => {
		app = makeApp();
	};
	return { clock, db, store, cache, call, user, upload, points, league, inbox, rows, profile, logs, sql, newIsolate };
}

describe("rankings: schema and migration", () => {
	const migration = readFileSync(new URL("../migrations/0003_rankings.sql", import.meta.url), "utf8");
	const schema = readFileSync(new URL("../schema.sql", import.meta.url), "utf8");
	const statements = migration
		.split("\n")
		.filter((line) => !line.trimStart().startsWith("--"))
		.join("\n")
		.split(";")
		.map((s) => s.trim())
		.filter(Boolean);

	test("the same statements as the end of schema.sql; says to run once", () => {
		assert.ok(statements.length >= 14);
		for (const s of statements) assert.ok(schema.includes(s), `schema.sql lacks: ${s.slice(0, 60)}`);
		assert.match(migration.slice(0, 600), /RUN IT ONCE/);
	});

	test("runs on the live database (social v1), ranks the profiles that have a save, and a second run stops at the first ALTER", () => {
		const sqlite = new DatabaseSync(":memory:");
		sqlite.exec(schema.slice(0, schema.indexOf("-- ── Rankings v1")));
		sqlite.exec(`INSERT INTO players (id, created_at, last_seen) VALUES ('p1', 1, 1), ('p2', 1, 1);
			INSERT INTO cloud_saves (player_id, revision, summary, device_id, updated_at, body_key, bytes) VALUES ('p1', 1, '{"level":7,"xp":900}', 'd', 5, 'k', 1);
			INSERT INTO profiles (player_id, code, level, created_at, updated_at) VALUES ('p1', 'AAAAAAAA', 7, 1, 1234), ('p2', 'BBBBBBBB', 1, 1, 99);`);
		sqlite.exec(migration);
		const got = sqlite.prepare("SELECT player_id, has_save, xp, level_at, league_division, strikes FROM profiles ORDER BY player_id").all().map((r) => ({ ...r }));
		assert.deepEqual(got, [
			{ player_id: "p1", has_save: 1, xp: 900, level_at: 1234, league_division: "bronze", strikes: 0 },
			{ player_id: "p2", has_save: 0, xp: 0, level_at: 0, league_division: "bronze", strikes: 0 },
		]);
		assert.throws(() => sqlite.exec(migration), /duplicate column name: xp/);
	});

	test("before the migration runs, saves, social and account deletion keep working; the ranking routes answer 500", async () => {
		const w = world();
		w.db.sqlite.exec("DROP INDEX profiles_rank; DROP INDEX profiles_rank_country; DROP TABLE league_groups; DROP TABLE league_members;");
		for (const c of ["xp", "level_at", "country", "ranking_opt_out", "ranking_hidden", "strikes", "league_division", "has_save"]) w.db.sqlite.exec(`ALTER TABLE profiles DROP COLUMN ${c}`);
		const ana = await w.user("ana", 4, 100, "BR");
		await w.upload(ana, 5, 200, "BR");
		assert.equal(w.profile(ana).level, 5);
		assert.equal((await w.call("GET", "/v1/save", undefined, ana.token)).body.data, save(5, 200));
		assert.equal((await w.call("GET", "/v1/social/me", undefined, ana.token)).status, 200);
		assert.equal((await w.call("GET", "/v1/rankings/world", undefined, ana.token)).status, 500);
		assert.ok(w.logs.some((l) => l.includes("0003_rankings.sql")));
		assert.equal((await w.call("DELETE", "/v1/account", undefined, ana.token)).status, 204);
	});
});

describe("rankings: profile from the save and the connection", () => {
	test("PUT /v1/save keeps level, xp, has_save and level_at (only when the level goes up); old summaries read xp 0", async () => {
		const w = world();
		const ana = await w.user("ana");
		assert.deepEqual([w.profile(ana).has_save, w.profile(ana).level_at], [0, 0]);
		w.clock.now += 1000;
		await w.upload(ana, 3, 120);
		assert.deepEqual({ ...w.profile(ana) }, { ...w.profile(ana), level: 3, xp: 120, has_save: 1, level_at: T0 + 1000 });
		w.clock.now += 1000;
		await w.upload(ana, 3, 150);
		assert.deepEqual([w.profile(ana).xp, w.profile(ana).level_at], [150, T0 + 1000], "same level: level_at stays");
		w.clock.now += 1000;
		await w.upload(ana, 4, 200);
		assert.equal(w.profile(ana).level_at, T0 + 3000);
		w.clock.now += 1000;
		await w.upload(ana, 2, 50);
		assert.deepEqual([w.profile(ana).level, w.profile(ana).level_at], [2, T0 + 3000], "a level going down (a restored save) keeps level_at");
		// The summary in the save answers carries xp.
		assert.equal((await w.call("GET", "/v1/save", undefined, ana.token)).body.summary.xp, 50);
	});

	test("an upload that changes nothing writes nothing to the profile (the cheap path stays one batch)", async () => {
		const w = world();
		const ana = await w.user("ana", 3, 120, "BR");
		w.sql.length = 0;
		await w.upload(ana, 3, 120, "BR");
		assert.equal(w.sql.filter((s) => /UPDATE profiles/.test(s)).length, 0);
		w.sql.length = 0;
		await w.upload(ana, 3, 130, "BR");
		const batches = w.sql.filter((s) => /UPDATE profiles/.test(s));
		assert.equal(batches.length, 1, "the profile update rides in the upload's batch");
	});

	test("country from request.cf.country: on uploads and social calls, only when it changed; XX, T1 and missing keep the old one", async () => {
		const w = world();
		const ana = await w.user("ana", 3, 0);
		assert.equal(w.profile(ana).country, null);
		await w.upload(ana, 3, 1, "XX");
		await w.upload(ana, 3, 2, "T1");
		await w.upload(ana, 3, 3, "br");
		assert.equal(w.profile(ana).country, null);
		await w.upload(ana, 3, 4, "BR");
		assert.equal(w.profile(ana).country, "BR");
		await w.upload(ana, 3, 5);
		await w.upload(ana, 3, 6, "XX");
		assert.equal(w.profile(ana).country, "BR");
		await w.call("GET", "/v1/social/me", undefined, ana.token, "DE");
		assert.equal(w.profile(ana).country, "DE");
		w.sql.length = 0;
		await w.call("GET", "/v1/social/me", undefined, ana.token, "DE");
		assert.ok(w.sql.some((s) => s.includes("country IS NOT ?")), "the write is guarded by 'changed'");
		const bia = await w.user("bia", undefined, 0, "PT");
		assert.equal(w.profile(bia).country, "PT", "a new profile takes the country right away");
	});
});

describe("rankings: world and country boards", () => {
	test("sort: level, then xp, then who reached the level first, then player id; me = my real position", async () => {
		const w = world();
		const users: Record<string, User> = {};
		// Created in this order, a second apart: level_at follows.
		for (const [name, level, xp] of [["a", 5, 100], ["b", 7, 50], ["c", 5, 300], ["d", 5, 100], ["e", 9, 0], ["f", 5, 100]] as const) {
			users[name] = await w.user(name, level, xp);
			w.clock.now += 1000;
		}
		// f reached level 5 / 100 xp at the same time as d: the player id decides.
		w.db.sqlite.prepare("UPDATE profiles SET level_at = ? WHERE player_id = ?").run(w.profile(users.d).level_at, users.f.id);
		const [d, f] = users.d.id < users.f.id ? ["d", "f"] : ["f", "d"];
		const expected = ["e", "b", "c", "a", d, f];
		const board = (await w.call("GET", "/v1/rankings/world", undefined, users.a.token)).body;
		assert.deepEqual(board.top.map((r: any) => r.id), expected.map((n) => users[n].id));
		assert.deepEqual(board.top.map((r: any) => r.rank), [1, 2, 3, 4, 5, 6]);
		assert.deepEqual(Object.keys(board), ["top", "me", "total", "updatedAt"]);
		assert.deepEqual(Object.keys(board.top[0]), ["rank", "id", "code", "marketName", "avatar", "level", "xp", "era", "country"]);
		assert.equal(board.total, 6);
		for (const [i, name] of expected.entries()) {
			const me = (await w.call("GET", "/v1/rankings/world", undefined, users[name].token)).body.me;
			assert.deepEqual([me.id, me.rank], [users[name].id, i + 1], name);
		}
		// limit: 1–100, default 100.
		assert.equal((await w.call("GET", "/v1/rankings/world?limit=2")).body.top.length, 2);
		assert.equal((await w.call("GET", "/v1/rankings/world?limit=0")).body.top.length, 1);
		assert.equal((await w.call("GET", "/v1/rankings/world?limit=500")).body.top.length, 6);
	});

	test("me: rank null with opt-out, hidden, or no save; they leave the top and the others move up", async () => {
		const w = world();
		const [a, b, c] = [await w.user("a", 9), await w.user("b", 8), await w.user("c", 7)];
		const nosave = await w.user("nosave");
		const me = async (u: User) => (await w.call("GET", "/v1/rankings/world", undefined, u.token)).body.me;
		assert.equal((await me(nosave)).rank, null);
		assert.equal((await me(nosave)).id, nosave.id);
		assert.equal((await w.call("PUT", "/v1/rankings/settings", { optOut: true }, a.token)).status, 204);
		assert.equal((await me(a)).rank, null);
		assert.equal((await me(b)).rank, 1);
		w.db.sqlite.prepare("UPDATE profiles SET ranking_hidden = 1 WHERE player_id = ?").run(b.id);
		assert.equal((await me(b)).rank, null);
		assert.equal((await me(c)).rank, 1);
		w.clock.now += RANKINGS.topCacheMs;
		const board = (await w.call("GET", "/v1/rankings/world")).body;
		assert.deepEqual([board.top.map((r: any) => r.id), board.total, board.me], [[c.id], 1, null]);
		assert.equal((await w.call("PUT", "/v1/rankings/settings", { optOut: false }, a.token)).status, 204);
		assert.equal((await me(a)).rank, 1);
		for (const bad of [{}, { optOut: "yes" }, { optOut: 1 }]) assert.equal((await w.call("PUT", "/v1/rankings/settings", bad, a.token)).status, 400);
		assert.equal((await w.call("PUT", "/v1/rankings/settings", { optOut: true })).status, 401);
	});

	test("country board: mine by default (then the connection's), any other by ?country=, me only on my own country's board", async () => {
		const w = world();
		const ana = await w.user("ana", 5, 0, "BR");
		const bia = await w.user("bia", 9, 0, "BR");
		const cris = await w.user("cris", 20, 0, "DE");
		const nocountry = await w.user("noc", 30, 0);
		const mine = (await w.call("GET", "/v1/rankings/country", undefined, ana.token)).body;
		assert.deepEqual(Object.keys(mine), ["country", "top", "me", "total", "updatedAt"]);
		assert.deepEqual([mine.country, mine.top.map((r: any) => r.id), mine.me.rank, mine.total], ["BR", [bia.id, ana.id], 2, 2]);
		assert.equal(mine.top[0].country, "BR");
		const de = (await w.call("GET", "/v1/rankings/country?country=de", undefined, ana.token)).body;
		assert.deepEqual([de.country, de.top.map((r: any) => r.id), de.me], ["DE", [cris.id], null]);
		// Signed out: the connection's country.
		const anon = (await w.call("GET", "/v1/rankings/country", undefined, undefined, "DE")).body;
		assert.deepEqual([anon.country, anon.top.length, anon.me], ["DE", 1, null]);
		// No country anywhere: an empty board.
		const none = (await w.call("GET", "/v1/rankings/country", undefined, nocountry.token)).body;
		assert.deepEqual([none.country, none.top, none.me, none.total], [null, [], null, 0]);
		// A player without a country is on the world board but on no country board.
		assert.equal((await w.call("GET", "/v1/rankings/world", undefined, nocountry.token)).body.me.rank, 1);
		for (const bad of ["XX", "BRA", "1", ""]) assert.equal((await w.call("GET", `/v1/rankings/country?country=${bad}`, undefined, ana.token)).status, 400, bad);
	});

	test("cache: top lists for 10 min per board, country and limit (memory, then the Cache API, then D1); me is always live; headers", async () => {
		const w = world();
		const ana = await w.user("ana", 5, 0, "BR");
		const first = await w.call("GET", "/v1/rankings/world", undefined, ana.token);
		assert.equal(first.headers.get("x-board-cache"), "d1");
		assert.equal(first.headers.get("cache-control"), "private, no-store", "a signed-in answer carries my row");
		const entry = [...w.cache.entries.entries()].find(([k]) => k.endsWith("/world/100"));
		assert.ok(entry, "put in the Cache API");
		assert.equal(entry[1].headers.get("cache-control"), "public, max-age=600");
		const anon = await w.call("GET", "/v1/rankings/world");
		assert.equal(anon.headers.get("x-board-cache"), "memory");
		assert.equal(anon.headers.get("cache-control"), "public, max-age=60");
		// A new player passes ana: the cached top does not change for 10 minutes, ana's own rank does.
		w.clock.now += 60_000;
		await w.user("bia", 9, 0, "BR");
		const later = (await w.call("GET", "/v1/rankings/world", undefined, ana.token)).body;
		assert.deepEqual([later.top.length, later.total, later.updatedAt, later.me.rank], [1, 1, T0, 2]);
		// Another isolate (empty memory) reads the Cache API.
		w.newIsolate();
		assert.equal((await w.call("GET", "/v1/rankings/world")).headers.get("x-board-cache"), "cache");
		// Other keys: another limit, the country board.
		assert.equal((await w.call("GET", "/v1/rankings/world?limit=10")).headers.get("x-board-cache"), "d1");
		assert.equal((await w.call("GET", "/v1/rankings/country?country=BR")).headers.get("x-board-cache"), "d1");
		assert.equal((await w.call("GET", "/v1/rankings/country?country=BR")).headers.get("x-board-cache"), "memory");
		// 10 minutes after it was read: D1 again.
		w.clock.now = T0 + RANKINGS.topCacheMs;
		const fresh = await w.call("GET", "/v1/rankings/world");
		assert.deepEqual([fresh.headers.get("x-board-cache"), fresh.body.top.length, fresh.body.updatedAt], ["d1", 2, T0 + RANKINGS.topCacheMs]);
	});
});

describe("rankings: friends board", () => {
	test("me + friends (not hidden ones), unsorted, with week points, likes and market rating; rank null", async () => {
		const w = world();
		const [ana, bia, cris, dani] = [await w.user("ana", 5), await w.user("bia", 7), await w.user("cris", 3), await w.user("dani", 4)];
		for (const f of [bia, cris]) {
			await w.call("POST", "/v1/social/friends/add", { code: f.code }, ana.token);
			await w.call("POST", "/v1/social/friends/accept", { id: ana.id }, f.token);
		}
		await w.call("POST", "/v1/social/like", { to: bia.id }, ana.token);
		await w.call("PUT", "/v1/save", `{"baseRevision":${bia.revision},"data":${JSON.stringify(save(7))},"deviceId":"p","force":false,"public":{"marketRating":4.5}}`, bia.token);
		await w.points(bia, 120);
		const got = (await w.call("GET", "/v1/rankings/friends", undefined, ana.token)).body.rows;
		assert.deepEqual(got.map((r: any) => r.id).sort(), [ana.id, bia.id, cris.id].sort());
		assert.equal(got[0].id, ana.id);
		const b = got.find((r: any) => r.id === bia.id);
		assert.deepEqual({ ...b, code: "x" }, { rank: null, id: bia.id, code: "x", marketName: null, avatar: null, level: 7, xp: 0, era: "mesinha", country: null, weekPoints: 120, likes: 1, marketRating: 4.5 });
		assert.equal(got.find((r: any) => r.id === cris.id).marketRating, null);
		w.db.sqlite.prepare("UPDATE profiles SET ranking_hidden = 1 WHERE player_id = ?").run(cris.id);
		assert.deepEqual((await w.call("GET", "/v1/rankings/friends", undefined, ana.token)).body.rows.map((r: any) => r.id).sort(), [ana.id, bia.id].sort());
		assert.equal((await w.call("GET", "/v1/rankings/friends", undefined, dani.token)).body.rows.length, 1);
		assert.equal((await w.call("GET", "/v1/rankings/friends")).status, 401);
	});
});

describe("rankings: weekly league", () => {
	test("before sending points: no group; joining by division and level band; groups capped at 30", async () => {
		const w = world();
		const ana = await w.user("ana", 3);
		const before = await w.league(ana);
		assert.deepEqual(
			{ ...before },
			{ week: WEEK, endsAt: Date.UTC(2026, 10, 9), division: "bronze", group: [], me: null, promote: 5, demote: 5, rewards: before.rewards, lastWeek: null },
		);
		assert.deepEqual(before.rewards.slice(0, 4), [{ place: 1, diamonds: 20 }, { place: 2, diamonds: 15 }, { place: 3, diamonds: 10 }, { place: 4, diamonds: 5 }]);
		assert.equal(before.rewards.length, 10);
		// Sending 0 before joining does not join.
		assert.deepEqual((await w.points(ana, 0)).body, { points: 0, place: null, groupSize: 0 });
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM league_members")[0].n, 0);
		// 31 players of levels 1–5 in bronze: a full group of 30 and a second one.
		const players: User[] = [ana];
		for (let i = 1; i < 31; i++) players.push(await w.user(`p${i}`, 1 + (i % 5)));
		for (const [i, p] of players.entries()) assert.equal((await w.points(p, 10 + i)).status, 200);
		const groups = w.rows("SELECT id, division, level_band, members FROM league_groups ORDER BY id");
		assert.deepEqual(groups.map((g) => [g.division, g.level_band, g.members]), [["bronze", 0, 30], ["bronze", 0, 1]]);
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM league_members WHERE group_id = ?", groups[0].id)[0].n, 30);
		// A member of a full group keeps sending.
		assert.deepEqual((await w.points(players[29], 1000)).body, { points: 1000, place: 1, groupSize: 30 });
		assert.deepEqual((await w.points(players[29], 1000)).body, { points: 1000, place: 1, groupSize: 30 });
		// Level 6 is another band; another division is another group.
		const six = await w.user("six", 6);
		await w.points(six, 5);
		const silver = await w.user("silver", 2);
		w.db.sqlite.prepare("UPDATE profiles SET league_division = 'silver' WHERE player_id = ?").run(silver.id);
		await w.points(silver, 5);
		assert.deepEqual(w.rows("SELECT division, level_band, members FROM league_groups ORDER BY id").slice(2).map((g) => [g.division, g.level_band, g.members]), [["bronze", 1, 1], ["silver", 0, 1]]);
		// The league answer: my group best first, me, zones.
		const view = await w.league(ana);
		assert.equal(view.group.length, 30);
		assert.deepEqual(view.group.slice(0, 2).map((r: any) => r.points), [1000, 38]);
		assert.deepEqual(Object.keys(view.group[0]), ["place", "id", "code", "marketName", "avatar", "level", "points", "isFriend"]);
		assert.deepEqual([view.me.id, view.me.place, view.me.points], [ana.id, 30, 10]);
		assert.deepEqual([view.promote, view.demote], [5, 5]);
		const small = await w.league(six);
		assert.deepEqual([small.group.length, small.promote, small.demote], [1, 0, 0]);
	});

	test("points: the week total, never down, capped by maxPointsPerDay(level) × days, one strike per crossing; 3 strikes hide", async () => {
		const w = world();
		const ana = await w.user("ana", 10);
		const bia = await w.user("bia", 10);
		await w.points(bia, 500);
		assert.deepEqual((await w.points(ana, 100)).body, { points: 100, place: 2, groupSize: 2 });
		assert.deepEqual((await w.points(ana, 50)).body, { points: 100, place: 2, groupSize: 2 }, "never down");
		const at = w.rows("SELECT points_at FROM league_members WHERE player_id = ?", ana.id)[0].points_at;
		w.clock.now += 1000;
		await w.points(ana, 100);
		assert.equal(w.rows("SELECT points_at FROM league_members WHERE player_id = ?", ana.id)[0].points_at, at, "the same total keeps points_at");
		assert.deepEqual((await w.points(ana, 501)).body, { points: 501, place: 1, groupSize: 2 });
		// Wednesday: 3 days × (2000 + 300 × 10) = 15 000.
		const cap = maxPointsPerDay(10) * 3;
		assert.equal(cap, 15_000);
		assert.deepEqual((await w.points(ana, cap + 1)).body, { points: cap, place: 1, groupSize: 2 });
		assert.equal(w.profile(ana).strikes, 1);
		await w.points(ana, cap + 999);
		assert.equal(w.profile(ana).strikes, 1, "the same over-cap total resent: no second strike");
		// Thursday: the cap grows; crossing it again is a new strike.
		w.clock.now += DAY_MS;
		assert.equal((await w.points(ana, 999_999)).body.points, maxPointsPerDay(10) * 4);
		assert.equal(w.profile(ana).strikes, 2);
		w.clock.now += DAY_MS;
		await w.points(ana, 999_999);
		assert.deepEqual([w.profile(ana).strikes, w.profile(ana).ranking_hidden], [3, 1]);
		// Hidden: points are ignored, off the group for others.
		const stored = w.rows("SELECT points FROM league_members WHERE player_id = ?", ana.id)[0].points;
		w.clock.now += DAY_MS;
		assert.deepEqual((await w.points(ana, 999_999)).body, { points: stored, place: null, groupSize: 0 });
		assert.equal(w.rows("SELECT points FROM league_members WHERE player_id = ?", ana.id)[0].points, stored);
		assert.deepEqual((await w.league(bia)).group.map((r: any) => r.id), [bia.id]);
		assert.equal((await w.points(bia, 600)).body.groupSize, 1);
	});

	test("wrong week → 409 with the server's week; bad bodies → 400; signed out → 401", async () => {
		const w = world();
		const ana = await w.user("ana", 3);
		assert.deepEqual((await w.points(ana, 10, "2026-W44")).body, { error: "wrong-week", week: WEEK });
		assert.equal((await w.points(ana, 10, "2026-W44")).status, 409);
		assert.equal((await w.points(ana, 10, "2026-W46")).status, 409);
		for (const body of [{ week: WEEK }, { week: WEEK, points: -1 }, { week: WEEK, points: 1.5 }, { week: WEEK, points: "9" }, { week: "45", points: 1 }, { points: 1 }, { week: WEEK, points: 2e9 }])
			assert.equal((await w.call("POST", "/v1/rankings/league/points", body, ana.token)).status, 400, JSON.stringify(body));
		assert.equal((await w.call("POST", "/v1/rankings/league/points", "x".repeat(20_000), ana.token)).status, 413);
		assert.equal((await w.call("POST", "/v1/rankings/league/points", { week: WEEK, points: 1 })).status, 401);
		assert.equal((await w.call("GET", "/v1/rankings/league")).status, 401);
	});

	test("ISO weeks: Monday 00:00 UTC boundaries and week-years", () => {
		assert.equal(weekOf(T0), WEEK);
		assert.equal(weekOf(Date.UTC(2026, 10, 2)), "2026-W45");
		assert.equal(weekOf(Date.UTC(2026, 10, 2) - 1), "2026-W44");
		assert.equal(weekOf(Date.UTC(2027, 0, 3, 23)), "2026-W53");
		assert.equal(weekOf(Date.UTC(2027, 0, 4)), "2027-W01");
		assert.equal(weekOf(Date.UTC(2021, 0, 3)), "2020-W53");
		assert.equal(weekStartOf(T0), Date.UTC(2026, 10, 2));
	});
});

describe("rankings: end of the week", () => {
	/** n players in one bronze group (or `division`) with the given points; answers them best first. */
	async function group(w: ReturnType<typeof world>, prefix: string, pts: number[], division = "bronze", level = 3) {
		const users: User[] = [];
		for (const [i, p] of pts.entries()) {
			const u = await w.user(`${prefix}${i}`, level);
			w.db.sqlite.prepare("UPDATE profiles SET league_division = ? WHERE player_id = ?").run(division, u.id);
			users.push(u);
			if (p > 0) await w.points(u, p);
			else {
				// 0 points: only possible for a member (the API never joins with 0), e.g. from older data.
				await w.points(u, 1);
				w.db.sqlite.prepare("UPDATE league_members SET points = 0 WHERE player_id = ?").run(u.id);
			}
			w.clock.now += 1000;
		}
		return users;
	}
	const nextMonday = Date.UTC(2026, 10, 9, 0, 5);
	const outcome = (w: ReturnType<typeof world>, users: User[]) =>
		users.map((u) => {
			const m = w.rows("SELECT final_place, moved_to, diamonds, chest FROM league_members WHERE player_id = ?", u.id)[0];
			return [m.final_place, m.moved_to, m.diamonds, m.chest];
		});

	test("30 players: top 5 up with a chest, bottom 5 down, places 1–10 diamonds; 0 points always down; ties: who got there first", async () => {
		const w = world();
		const pts = Array.from({ length: 30 }, (_, i) => 300 - i * 10);
		pts[6] = pts[5]; // places 6 and 7 tie on points: the earlier one is 6th
		pts[12] = 0;
		const users = await group(w, "s", pts, "silver");
		w.clock.now = nextMonday;
		const result = await closeWeeks(w.store, w.clock.now, () => {});
		assert.deepEqual(result, { closed: 1, more: false });
		const got = outcome(w, users);
		assert.deepEqual(got.slice(0, 7), [
			[1, "gold", 20, 1], [2, "gold", 15, 1], [3, "gold", 10, 1], [4, "gold", 5, 1], [5, "gold", 5, 1],
			[6, "silver", 5, 0], [7, "silver", 5, 0],
		]);
		assert.deepEqual(got[12].slice(1), ["bronze", 0, 0], "0 points: down, no diamonds");
		assert.deepEqual(got[12][0], 30, "0 points: last");
		assert.deepEqual(got.filter((g) => g[0] >= 26).map((g) => g[1]), ["bronze", "bronze", "bronze", "bronze", "bronze"], "places 26–30 down (0-point player among them)");
		assert.equal(got[25][0], 25);
		assert.equal(got[25][1], "silver", "25th stays");
		assert.equal(got.filter((g) => g[1] === "bronze").length, 5);
		assert.deepEqual(got.slice(7, 12).map((g) => [g[1], g[2]]), [["silver", 5], ["silver", 5], ["silver", 5], ["silver", 0], ["silver", 0]]);
		assert.equal(w.profile(users[0]).league_division, "gold");
		assert.equal(w.profile(users[29]).league_division, "bronze");
		// The inbox item.
		const items = await w.inbox(users[0]);
		assert.equal(items.length, 1);
		assert.deepEqual(noTop(items[0].payload), { week: WEEK, division: "silver", place: 1, diamonds: 20, chest: true, movedTo: "gold" });
		assert.equal(items[0].from, null);
		assert.deepEqual(noTop((await w.inbox(users[12]))[0].payload), { week: WEEK, division: "silver", place: 30, diamonds: 0, chest: false, movedTo: "bronze" });
		assert.deepEqual(noTop((await w.inbox(users[29]))[0].payload), { week: WEEK, division: "silver", place: 29, diamonds: 0, chest: false, movedTo: "bronze" });
	});

	test("edges: not above diamond, not below bronze; small groups: zone = min(5, n/2); multipliers", async () => {
		const w = world();
		const diamond = await group(w, "d", [50, 40, 30, 20, 10, 9, 8, 7, 6, 5, 4, 3], "diamond");
		const bronze = await group(w, "b", [50, 40, 30, 20, 10, 9, 8, 7, 6, 5, 4, 3], "bronze");
		const gold = await group(w, "g", [60, 50, 40, 30, 20, 10], "gold", 8);
		const ruby = await group(w, "r", [5, 4], "ruby", 13);
		const solo = await group(w, "e", [5], "emerald", 18);
		w.clock.now = nextMonday;
		await closeWeeks(w.store, w.clock.now, () => {});
		// diamond × 3; top 5 stay (no higher division) with the chest; bottom 5 to emerald.
		assert.deepEqual(outcome(w, diamond).map((g) => g[1]), [...Array(7).fill("diamond"), ...Array(5).fill("emerald")]);
		assert.deepEqual(outcome(w, diamond).slice(0, 5).map((g) => [g[2], g[3]]), [[60, 1], [45, 1], [30, 1], [15, 1], [15, 1]]);
		// bronze: bottom 5 stay in bronze.
		assert.deepEqual(outcome(w, bronze).map((g) => g[1]), [...Array(5).fill("silver"), ...Array(7).fill("bronze")]);
		// gold × 1.5 rounded down, 6 players: zone 3.
		assert.deepEqual(outcome(w, gold), [[1, "sapphire", 30, 1], [2, "sapphire", 22, 1], [3, "sapphire", 15, 1], [4, "silver", 7, 0], [5, "silver", 7, 0], [6, "silver", 7, 0]]);
		// ruby × 2, 2 players: one up, one down.
		assert.deepEqual(outcome(w, ruby), [[1, "emerald", 40, 1], [2, "sapphire", 30, 0]]);
		// alone in a group: no zone (stays), still 1st.
		assert.deepEqual(outcome(w, solo), [[1, "emerald", 40, 0]]);
	});

	test("rewards exactly once: a second cron run, a lazy close and the cron at once change nothing; hidden players get nothing", async () => {
		const w = world();
		const users = await group(w, "x", [30, 20, 10, 5]);
		w.db.sqlite.prepare("UPDATE profiles SET ranking_hidden = 1 WHERE player_id = ?").run(users[1].id);
		w.clock.now = nextMonday;
		const rankings = new RankingStore(w.store);
		const ids = await rankings.staleGroups(weekOf(w.clock.now), 10);
		const [a, b] = await Promise.all([rankings.closeGroups(ids), rankings.closeGroups(ids)]);
		assert.deepEqual([a + b], [1], "only one of two closes at once closes the group");
		await closeWeeks(w.store, w.clock.now, () => {});
		await closeWeeks(w.store, w.clock.now, () => {});
		await w.league(users[0]);
		const items = w.rows("SELECT player_id, payload FROM inbox WHERE kind = 'league_reward'");
		assert.equal(items.length, 3, "one per ranked member, none for the hidden one");
		assert.ok(!items.some((i) => i.player_id === users[1].id));
		assert.deepEqual(outcome(w, users).map((g) => g[0]), [1, null, 2, 3]);
		// The group's podium rides along (places 1–3, best first; the hidden player is not on it).
		for (const item of items) {
			const top = JSON.parse(item.payload).top;
			assert.deepEqual(top.map((t: any) => [t.id, t.points]), [[users[0].id, 30], [users[2].id, 10], [users[3].id, 5]]);
			assert.ok(top.every((t: any) => typeof t.code === "string" && "marketName" in t && "avatar" in t));
		}
		assert.equal(w.profile(users[1]).league_division, "bronze", "hidden: division unchanged");
		// Even if the group were reopened by mistake, the inbox guard keeps one item per (player, week).
		w.db.sqlite.exec("UPDATE league_groups SET closed = 0");
		await rankings.closeGroups(ids);
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM inbox WHERE kind = 'league_reward'")[0].n, 3);
	});

	test("no cron: the first league call of the new week closes my old group first (my new division), lastWeek, new group", async () => {
		const w = world();
		const users = await group(w, "y", [30, 20, 10, 5, 4, 3, 2, 1, 1, 1, 1]);
		const other = await group(w, "z", [9], "gold", 30);
		w.clock.now = nextMonday + DAY_MS;
		const week = weekOf(w.clock.now);
		assert.equal(week, "2026-W46");
		// The first call of the week (by someone else) closes the stale groups lazily.
		const top = users[0];
		const res = await w.points(top, 40);
		assert.equal(res.status, 200, res.text);
		assert.equal(w.profile(top).league_division, "silver");
		const g = w.rows("SELECT g.division, g.week FROM league_members m JOIN league_groups g ON g.id = m.group_id WHERE m.player_id = ? AND m.week = ?", top.id, week)[0];
		assert.deepEqual({ ...g }, { division: "silver", week });
		const view = await w.league(top);
		assert.deepEqual([view.week, view.division, view.lastWeek], [week, "silver", { division: "bronze", place: 1, movedTo: "silver" }]);
		assert.deepEqual(w.rows("SELECT closed FROM league_groups WHERE week = ?", WEEK).map((r) => r.closed), [1, 1]);
		assert.equal((await w.league(other[0])).lastWeek.place, 1);
		// A player who did not play last week: no lastWeek, division unchanged.
		const fresh = await w.user("fresh", 3);
		assert.deepEqual([(await w.league(fresh)).lastWeek, (await w.league(fresh)).division], [null, "bronze"]);
	});

	test("league_reward top: a hidden name is null for the others and kept for its owner", async () => {
		const w = world();
		const users = await group(w, "n", [30, 20, 10]);
		w.db.sqlite.prepare("UPDATE profiles SET market_name = 'Mercado Topo', name_hidden = 1 WHERE player_id = ?").run(users[0].id);
		w.clock.now = nextMonday;
		await closeWeeks(w.store, w.clock.now, () => {});
		const payload = (u: { id: string }) => JSON.parse(w.rows("SELECT payload FROM inbox WHERE kind = 'league_reward' AND player_id = ?", u.id)[0].payload);
		assert.equal(payload(users[1]).top[0].marketName, null);
		assert.equal(payload(users[0]).top[0].marketName, "Mercado Topo");
		assert.equal(payload(users[0]).top.length, 3);
		assert.deepEqual([payload(users[1]).points, payload(users[1]).size], [20, 3]);
	});

	test("chunks: the cron closes groups in batches and can stop and resume", async () => {
		const w = world();
		for (let i = 0; i < 5; i++) await group(w, `c${i}-`, [10, 5], "bronze", 1 + i * 5);
		w.clock.now = nextMonday;
		assert.deepEqual(await closeWeeks(w.store, w.clock.now, () => {}, 0), { closed: 0, more: true });
		const rankings = new RankingStore(w.store);
		const first = await rankings.staleGroups(weekOf(w.clock.now), 2);
		assert.equal(await rankings.closeGroups(first), 2);
		assert.deepEqual(await closeWeeks(w.store, w.clock.now, () => {}), { closed: 3, more: false });
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM inbox WHERE kind = 'league_reward'")[0].n, 10);
	});

	test("old weeks are cleaned up by the cron after 8 weeks", async () => {
		const w = world();
		const users = await group(w, "o", [10, 5]);
		w.clock.now = nextMonday + 9 * 7 * DAY_MS;
		await closeWeeks(w.store, w.clock.now, () => {});
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM league_members")[0].n, 0);
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM league_groups")[0].n, 0);
		assert.equal(w.profile(users[0]).league_division, "silver", "a 2-player group: zone 1 → 1st moved up, then the rows were dropped");
	});
});

describe("rankings: anti-cheat on uploads", () => {
	test("a jump of more than +5 levels (past the early levels) or a level above MAX_LEVEL is a strike; the level is stored; 3 strikes hide", async () => {
		const w = world();
		const ana = await w.user("ana", 1);
		await w.upload(ana, 12);
		assert.equal(w.profile(ana).strikes, 0, "the early levels can go fast");
		await w.upload(ana, 17);
		assert.equal(w.profile(ana).strikes, 0, "+5 is fine");
		await w.upload(ana, 23);
		assert.deepEqual([w.profile(ana).strikes, w.profile(ana).level], [1, 23]);
		await w.upload(ana, MAX_LEVEL + 1);
		assert.equal(w.profile(ana).strikes, 2);
		await w.upload(ana, MAX_LEVEL + 1);
		assert.deepEqual([w.profile(ana).strikes, w.profile(ana).ranking_hidden], [3, 1]);
		assert.equal((await w.call("GET", "/v1/rankings/world", undefined, ana.token)).body.me.rank, null);
		// Social keeps the level, and the save is untouched.
		assert.equal((await w.call("GET", "/v1/social/me", undefined, ana.token)).body.level, MAX_LEVEL + 1);
		// A profile made from an existing save: the first upload is not a jump.
		const bia = await w.user("bia");
		const login = (await w.call("POST", "/v1/auth/google", { idToken: "token-cris" })).body;
		await w.call("PUT", "/v1/save", { baseRevision: 0, data: save(30), deviceId: "d" }, login.token);
		await w.call("GET", "/v1/social/me", undefined, login.token);
		await w.call("PUT", "/v1/save", { baseRevision: 1, data: save(31), deviceId: "d" }, login.token);
		assert.equal(w.rows("SELECT strikes FROM profiles WHERE player_id = ?", login.player.id)[0].strikes, 0);
		await w.upload(bia, 40);
		assert.equal(w.profile(bia).strikes, 0, "the first save of a profile is not a jump");
	});
});

describe("rankings: account deletion", () => {
	test("removes the player's league rows; the group keeps one member less", async () => {
		const w = world();
		const [ana, bia] = [await w.user("ana", 3), await w.user("bia", 3)];
		await w.points(ana, 10);
		await w.points(bia, 20);
		assert.equal(w.rows("SELECT members FROM league_groups")[0].members, 2);
		assert.equal((await w.call("DELETE", "/v1/account", undefined, ana.token)).status, 204);
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM league_members WHERE player_id = ?", ana.id)[0].n, 0);
		assert.equal(w.rows("SELECT members FROM league_groups")[0].members, 1);
		assert.deepEqual((await w.league(bia)).group.map((r: any) => r.id), [bia.id]);
		const fresh = await w.user("cris", 3);
		await w.points(fresh, 5);
		assert.equal(w.rows("SELECT members FROM league_groups")[0].members, 2, "the free seat is taken again");
	});
});
