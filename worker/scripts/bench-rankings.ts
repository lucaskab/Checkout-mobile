/**
 * Local estimate of the Worker's CPU time for the rankings routes and the weekly close (npm run bench:rankings). Like
 * bench-social.ts: the real app against the test stand-ins (D1 = node:sqlite, R2 = memory), minus the CPU spent inside
 * SQLite (on Cloudflare the SQL runs in D1, not in the Worker). The SQLite share is printed too: it says how long D1
 * itself works on each call. World: 20 000 ranked profiles (random levels, XP, 30 countries), "me" with 50 friends,
 * last week's league with 500 full groups (15 000 members) left open for the close.
 */
import { createApp } from "../src/app.ts";
import type { D1Database, D1PreparedStatement } from "../src/cf.ts";
import { DIVISIONS, weekOf, weekStartOf } from "../src/limits.ts";
import { closeWeeks } from "../src/ranking-store.ts";
import { Store } from "../src/store.ts";
import { fakeD1, fakeR2 } from "../test/fakes.ts";
import { syntheticSave } from "./bench.ts";

let sqliteUs = 0;
const timed =
	<A extends unknown[], R>(fn: (...args: A) => R) =>
	(...args: A): R => {
		const start = process.cpuUsage();
		try {
			return fn(...args);
		} finally {
			const used = process.cpuUsage(start);
			sqliteUs += used.user + used.system;
		}
	};
function wrapStatement(s: D1PreparedStatement): D1PreparedStatement {
	return { ...s, bind: (...v: unknown[]) => wrapStatement(s.bind(...v)), first: timed(s.first), all: timed(s.all), run: timed(s.run) } as D1PreparedStatement;
}
const raw = fakeD1();
const db: D1Database = { prepare: (sql) => wrapStatement(raw.prepare(sql)), batch: timed(raw.batch.bind(raw)) as D1Database["batch"] };

// Wednesday 10:00 UTC; the clock moves 11 minutes per "uncached" call so the top list is never reused.
const clock = { now: Date.UTC(2026, 10, 4, 10) };
const store = new Store(db, fakeR2(), { clock: () => clock.now });
const secret = "bench-secret-bench-secret-bench-secret-1";
const app = createApp({ store, verifyGoogle: async (t) => ({ sub: `g-${t}` }), sessionSecret: secret, rateLimit: 1e9, now: () => clock.now, cache: null, log: (l) => l.startsWith("error") && console.error(l) });
const call = async (method: string, path: string, token?: string, body?: string, country = "BR") => {
	const headers: Record<string, string> = { "content-type": "application/json" };
	if (token) headers.authorization = `Bearer ${token}`;
	const response = await app(new Request(`https://bench.example${path}`, { method, headers, body }), "1.1.1.1", country);
	const text = await response.text();
	if (response.status >= 300) throw new Error(`${method} ${path}: ${response.status} ${text.slice(0, 200)}`);
	return text;
};
const signIn = async (name: string) => {
	const login = JSON.parse(await (await app(new Request("https://bench.example/v1/auth/google", { method: "POST", body: JSON.stringify({ idToken: name }) }), "1.1.1.1")).text());
	return { token: login.token as string, id: login.player.id as string };
};

// ── The world ──
const PROFILES = 20_000;
const countries = ["BR", "US", "DE", "FR", "ES", "PT", "MX", "AR", "IT", "GB", "CA", "JP", "IN", "PL", "NL", "BE", "CH", "AT", "SE", "NO", "DK", "FI", "IE", "CL", "CO", "PE", "TR", "RU", "UA", "AU"];
let seed = 42;
const random = () => ((seed = (seed * 1_103_515_245 + 12_345) % 2 ** 31) / 2 ** 31);
raw.sqlite.exec("BEGIN");
const addPlayer = raw.sqlite.prepare("INSERT INTO players (id, google_sub, created_at, last_seen) VALUES (?, ?, 1, 1)");
const addProfile = raw.sqlite.prepare(
	`INSERT INTO profiles (player_id, code, market_name, level, era, created_at, updated_at, xp, level_at, country, has_save, public_json)
	 VALUES (?, ?, ?, ?, 'mercadinho', 1, 1, ?, ?, ?, 1, '{"marketRating":4.2}')`,
);
for (let i = 0; i < PROFILES; i++) {
	const id = `p-${String(i).padStart(6, "0")}`;
	const level = 1 + Math.floor(random() ** 2 * 60);
	addPlayer.run(id, `g-bench-${i}`);
	addProfile.run(id, `C${String(i).padStart(7, "0")}`, `Mercado ${i}`, level, level * 10_000 + Math.floor(random() * 9_999), Math.floor(random() * 1e12), countries[i % countries.length]);
}
raw.sqlite.exec("COMMIT");

// "me": a mid-table player with 50 friends and a cloud save.
const me = await signIn("me");
await call("GET", "/v1/social/me", me.token);
await call("PUT", "/v1/save", me.token, `{"baseRevision":0,"data":${JSON.stringify(syntheticSave(14_000))},"deviceId":"d","force":false}`);
raw.sqlite.prepare("UPDATE profiles SET level = 20, xp = 200000 WHERE player_id = ?").run(me.id);
const addFriend = raw.sqlite.prepare("INSERT INTO friends VALUES (?, ?, 1), (?, ?, 1)");
for (let i = 0; i < 50; i++) addFriend.run(me.id, `p-${String(i * 37).padStart(6, "0")}`, `p-${String(i * 37).padStart(6, "0")}`, me.id);

// Last week's league: 500 full groups of 30 (15 000 members), still open (the cron has not run).
const lastWeek = weekOf(weekStartOf(clock.now) - 1);
raw.sqlite.exec("BEGIN");
const addGroup = raw.sqlite.prepare("INSERT INTO league_groups (week, division, level_band, members) VALUES (?, ?, ?, 30)");
const addMember = raw.sqlite.prepare("INSERT INTO league_members (week, player_id, group_id, points, points_at) VALUES (?, ?, ?, ?, ?)");
for (let g = 0; g < 500; g++) {
	const group = Number(addGroup.run(lastWeek, DIVISIONS[g % DIVISIONS.length], g % 12).lastInsertRowid);
	for (let m = 0; m < 30; m++) addMember.run(lastWeek, `p-${String(1000 + g * 30 + m).padStart(6, "0")}`, group, Math.floor(random() * 5000), Math.floor(random() * 1e9));
}
raw.sqlite.exec("COMMIT");
// This week: "me" in a full group of 30.
const thisWeek = weekOf(clock.now);
const myGroup = Number(addGroup.run(thisWeek, "bronze", 3).lastInsertRowid);
for (let m = 0; m < 29; m++) addMember.run(thisWeek, `p-${String(m * 11).padStart(6, "0")}`, myGroup, Math.floor(random() * 3000), Math.floor(random() * 1e9));
addMember.run(thisWeek, me.id, myGroup, 100, 1);

async function bench(label: string, runs: number, work: (i: number) => Promise<unknown>) {
	await work(0);
	sqliteUs = 0;
	const start = process.cpuUsage();
	for (let i = 1; i <= runs; i++) await work(i);
	const used = process.cpuUsage(start);
	const total = (used.user + used.system) / 1000 / runs;
	const sql = sqliteUs / 1000 / runs;
	console.log(`${label.padEnd(58)} Worker ≈ ${(total - sql).toFixed(2)} ms CPU  (SQLite ${sql.toFixed(2)} ms)`);
}

console.log(`Rankings, ${PROFILES} ranked profiles, me with 50 friends, a group of 30, last week 500 groups open:`);
const tick = () => {
	clock.now += 11 * 60_000;
};
await bench("GET /v1/rankings/world (uncached top 100, signed in)", 20, () => (tick(), call("GET", "/v1/rankings/world", me.token)));
await bench("GET /v1/rankings/world (uncached top 100, signed out)", 20, () => (tick(), call("GET", "/v1/rankings/world")));
await bench("GET /v1/rankings/world (top 100 from memory, signed in)", 50, () => call("GET", "/v1/rankings/world", me.token));
await bench("GET /v1/rankings/country (uncached, ~670 in BR)", 20, () => (tick(), call("GET", "/v1/rankings/country", me.token)));
await bench("GET /v1/rankings/friends (50 friends)", 50, () => call("GET", "/v1/rankings/friends", me.token));

// The close: first the cron over 500 groups (as on Monday 00:05), then the league routes of the new week.
clock.now = weekStartOf(clock.now) + 7 * 24 * 60 * 60_000 + 5 * 60_000;
// Before: the lazy close of a chunk as the first league call of the week would do it (100 groups), on a copy run.
sqliteUs = 0;
let start = process.cpuUsage();
const result = await closeWeeks(store, clock.now, () => {});
let used = process.cpuUsage(start);
const total = (used.user + used.system) / 1000;
console.log(`cron close: ${result.closed} groups (15 000 members, ${Math.ceil(result.closed / 100)} batches)`.padEnd(58), `Worker ≈ ${(total - sqliteUs / 1000).toFixed(2)} ms CPU  (SQLite ${(sqliteUs / 1000).toFixed(2)} ms)`);
const rewards = (raw.sqlite.prepare("SELECT COUNT(*) AS n FROM inbox WHERE kind = 'league_reward'").get() as { n: number }).n;
console.log(`  → ${rewards} league_reward items`);
sqliteUs = 0;
start = process.cpuUsage();
await closeWeeks(store, clock.now, () => {});
used = process.cpuUsage(start);
console.log("cron close run again (nothing left)".padEnd(58), `Worker ≈ ${((used.user + used.system) / 1000 - sqliteUs / 1000).toFixed(2)} ms CPU  (SQLite ${(sqliteUs / 1000).toFixed(2)} ms)`);

// The new week: me joins a group of 29 others.
const newWeek = weekOf(clock.now);
const group2 = Number(addGroup.run(newWeek, "bronze", 3).lastInsertRowid);
for (let m = 0; m < 29; m++) addMember.run(newWeek, `p-${String(5 + m * 13).padStart(6, "0")}`, group2, Math.floor(random() * 3000), Math.floor(random() * 1e9));
raw.sqlite.prepare("UPDATE league_groups SET members = 29 WHERE id = ?").run(group2);
raw.sqlite.prepare("UPDATE profiles SET league_division = 'bronze', level = 18 WHERE player_id = ?").run(me.id);
let pts = 10;
await bench("POST /v1/rankings/league/points (group of 30)", 50, () => call("POST", "/v1/rankings/league/points", me.token, JSON.stringify({ week: newWeek, points: (pts += 7) })));
await bench("GET /v1/rankings/league (group of 30, lastWeek)", 50, () => call("GET", "/v1/rankings/league", me.token));
let revision = 1;
const data = (xp: number) => JSON.stringify(JSON.stringify({ state: { market: { level: 18, totalExperience: xp }, era: { id: "mercadinho" }, items: JSON.parse(syntheticSave(14_000)).state.items }, version: 45 }));
await bench("PUT /v1/save (14 KB save, profile xp/level in the same batch)", 30, (i) =>
	call("PUT", "/v1/save", me.token, `{"baseRevision":${revision++},"data":${data(200_000 + i)},"deviceId":"d","force":false}`),
);
