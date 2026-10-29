import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import { readdirSync, readFileSync } from "node:fs";
import { after, before, describe, test } from "node:test";
import { adminRoutes } from "../src/admin.ts";
import { createApp } from "../src/app.ts";
import { copyHistory, copyPlayers, copySaves, type MigrateDeps, plan, verifyHistory, verifySaves } from "../src/migrate.ts";
import { PgClient } from "../src/pg.ts";
import { Store } from "../src/store.ts";
import { signSession } from "../src/tokens.ts";
import { fakeD1, fakeR2, nodeConnect } from "./fakes.ts";

// The copy from the Render database, against a real Postgres with the Render server's own migrations
// (server/prisma/migrations). Needs OLD_TEST_DATABASE_URL, e.g. scripts/test-postgres.sh prints one
// (SCRAM password + TLS, like Prisma Postgres).
const url = process.env.OLD_TEST_DATABASE_URL;
const SECRET = "test-secret-test-secret-test-secret-123";
const keys = generateKeyPairSync("ec", { namedCurve: "P-256" });
const PUBLIC_KEY = keys.publicKey.export({ format: "der", type: "spki" }).toString("base64");
const adminToken = (until = Date.now() + 600_000, key = keys.privateKey) =>
	`${until}.${sign("sha256", Buffer.from(`checkout-admin:${until}`), { key, dsaEncoding: "ieee-p1363" }).toString("base64url")}`;
const ADMIN = adminToken();
const save = (diamonds: number, extra = "") =>
	JSON.stringify({ state: { coins: 10, era: { id: "banca" }, market: { level: 4 }, logistics: { premiumCurrency: diamonds }, day: { dayNumber: 9 }, extra }, version: 45 });
const unicodeBig = save(7, `${"Pão de queijo \"quente\" \\ ção\n\t€😀 ".repeat(52_000)}`);

describe("copy from the Render database (Postgres)", { skip: !url && "no OLD_TEST_DATABASE_URL" }, () => {
	const db = fakeD1();
	const bucket = fakeR2();
	const deps: MigrateDeps = { url: url as string, connect: nodeConnect, db, bucket };
	let pg: PgClient;
	const exec = (sql: string) => pg.query(sql);
	const lit = (s: string) => `'${s.replace(/'/g, "''")}'`;

	before(async () => {
		pg = await PgClient.connect(url as string, nodeConnect);
		await exec("DROP TABLE IF EXISTS save_history, cloud_saves, players CASCADE");
		const dir = new URL("../../server/prisma/migrations/", import.meta.url);
		for (const name of readdirSync(dir).filter((n) => /^\d/.test(n)).sort()) await exec(readFileSync(new URL(`${name}/migration.sql`, dir), "utf8"));
		await exec(`INSERT INTO players (id, google_sub, email, name, created_at, last_seen) VALUES
			('11111111-aaaa-4aaa-8aaa-000000000001', 'g-ana', 'ana@x.com', 'Ana', '2026-10-12 10:00:00.123', '2026-10-28 10:00:00'),
			('22222222-aaaa-4aaa-8aaa-000000000002', 'g-bia', 'bia@x.com', 'Bia d''Ávila', '2026-10-13 10:00:00', '2026-10-28 11:00:00'),
			('33333333-aaaa-4aaa-8aaa-000000000003', 'g-no-save', null, null, '2026-10-14 10:00:00', '2026-10-14 10:00:00')`);
		await exec(`INSERT INTO players (id, apple_sub, apple_refresh, email, name, created_at, last_seen) VALUES
			('44444444-aaaa-4aaa-8aaa-000000000004', '001.cris', 'refresh-cris', 'c@privaterelay.appleid.com', 'Cris', '2026-10-20 10:00:00', '2026-10-28 12:00:00')`);
		const summary = (d: number) => lit(JSON.stringify({ level: 4, era: "banca", coins: 10, diamonds: d, day: 9, version: 45 }));
		await exec(`INSERT INTO cloud_saves (player_id, revision, data, summary, device_id, updated_at) VALUES
			('11111111-aaaa-4aaa-8aaa-000000000001', 7, ${lit(save(70))}, ${summary(70)}, 'ana-phone', '2026-10-28 10:00:00.456'),
			('22222222-aaaa-4aaa-8aaa-000000000002', 3, ${lit(unicodeBig)}, ${summary(7)}, 'bia-pc', '2026-10-28 11:00:00'),
			('44444444-aaaa-4aaa-8aaa-000000000004', 1, ${lit(save(1))}, ${summary(1)}, 'cris-iphone', '2026-10-28 12:00:00')`);
		await exec(`INSERT INTO save_history (player_id, revision, data, summary, device_id, saved_at) VALUES
			('11111111-aaaa-4aaa-8aaa-000000000001', 5, ${lit(save(50))}, ${summary(50)}, 'ana-phone', '2026-10-27 08:00:00'),
			('11111111-aaaa-4aaa-8aaa-000000000001', 6, ${lit(save(60))}, ${summary(60)}, 'ana-old-phone', '2026-10-27 09:30:00'),
			('22222222-aaaa-4aaa-8aaa-000000000002', 2, ${lit(save(2, "ç"))}, ${summary(2)}, 'bia-pc', '2026-10-27 10:00:00')`);
	});
	after(async () => {
		await pg?.close();
	});

	const copyAll = async () => {
		const players = await copyPlayers(deps);
		const saves = [];
		for (let cursor = "", finished = false; !finished; ) {
			const r = await copySaves(deps, cursor, 2);
			saves.push(...r.done);
			({ next: cursor, finished } = r);
		}
		let history = { copied: 0, already: 0 };
		for (let cursor = "0", finished = false; !finished; ) {
			const r = await copyHistory(deps, cursor, 2);
			history = { copied: history.copied + r.copied, already: history.already + r.already };
			({ next: cursor, finished } = r as { next: string; finished: boolean });
		}
		return { players, saves, history };
	};
	const verifyAll = async () => {
		const saves = await verifySaves(deps, "", 50);
		const history = await verifyHistory(deps, "0", 50);
		return { saves, history };
	};

	test("the plan counts both sides (no data)", async () => {
		const p = await plan(deps);
		assert.equal(p.old.players, 4);
		assert.equal(p.old.saves, 3);
		assert.equal(p.old.history, 3);
		assert.equal(p.old.saves_over_1mb, 1);
		assert.ok(p.old.max_save_bytes > 1_900_000);
		assert.deepEqual(p.here, { players: 0, saves: 0, history: 0 });
	});

	test("every player, save and restore point comes over byte for byte, with the same ids and revisions", async () => {
		const { players, saves, history } = await copyAll();
		assert.deepEqual(players, { old: 4, inserted: 4, updated: 0, aliased: 0, failed: [] });
		assert.deepEqual(saves.map((s) => s.outcome), ["copied", "copied", "copied"]);
		assert.deepEqual(history, { copied: 3, already: 0 });
		const v = await verifyAll();
		assert.deepEqual([v.saves.identical, v.saves.problems, v.history.identical, v.history.problems], [3, [], 3, []]);
		const cris = db.sqlite.prepare("SELECT * FROM players WHERE apple_sub = '001.cris'").get() as Record<string, unknown>;
		assert.equal(cris.apple_refresh, "refresh-cris");
		assert.equal(new Date(Number(cris.created_at)).toISOString(), "2026-10-20T10:00:00.000Z");
	});

	test("the game picks up where it was: the Render session works, the save and its revision are the same", async () => {
		const store = new Store(db, bucket);
		const app = createApp({ store, verifyGoogle: async () => null, sessionSecret: SECRET, rateLimit: 1000 });
		const token = await signSession("22222222-aaaa-4aaa-8aaa-000000000002", SECRET);
		const response = await app(new Request("https://w/v1/save", { headers: { authorization: `Bearer ${token}` } }), "x");
		const body = (await response.json()) as Record<string, unknown>;
		assert.equal(body.data, unicodeBig);
		assert.equal(body.revision, 3);
		assert.equal(body.deviceId, "bia-pc");
		assert.equal(body.updatedAt, "2026-10-28T11:00:00.000Z");
		assert.deepEqual(body.summary, { level: 4, era: "banca", coins: 10, diamonds: 7, day: 9, version: 45 });
		const ana = await app(new Request("https://w/v1/save", { headers: { authorization: `Bearer ${await signSession("11111111-aaaa-4aaa-8aaa-000000000001", SECRET)}` } }), "x");
		assert.equal(((await ana.json()) as { updatedAt: string }).updatedAt, "2026-10-28T10:00:00.456Z");
	});

	test("running it again changes nothing", async () => {
		const puts = bucket.puts;
		const { players, saves, history } = await copyAll();
		assert.deepEqual([players.inserted, players.updated], [0, 4]);
		assert.deepEqual(saves.map((s) => s.outcome), ["same", "same", "same"]);
		assert.deepEqual(history, { copied: 0, already: 3 });
		assert.equal(bucket.puts, puts, "nothing uploaded twice");
	});

	test("old builds keep playing on Render: newer Render saves come over, and nothing played here is overwritten", async () => {
		const store = new Store(db, bucket);
		const app = createApp({ store, verifyGoogle: async (t) => (t === "g-dani-token" ? { sub: "g-dani" } : null), sessionSecret: SECRET, rateLimit: 1000 });
		// Bia (new build) uploads here on top of revision 3.
		const bia = await signSession("22222222-aaaa-4aaa-8aaa-000000000002", SECRET);
		const put = await app(
			new Request("https://w/v1/save", { method: "PUT", headers: { authorization: `Bearer ${bia}` }, body: JSON.stringify({ baseRevision: 3, data: save(8), deviceId: "bia-new" }) }),
			"x",
		);
		assert.equal(put.status, 200);
		// Dani signs in here first (new build), then turns out to have played on Render too.
		const dani = (await (await app(new Request("https://w/v1/auth/google", { method: "POST", body: JSON.stringify({ idToken: "g-dani-token" }) }), "x")).json()) as {
			player: { id: string };
		};
		await exec(`INSERT INTO players (id, google_sub, created_at, last_seen) VALUES ('55555555-aaaa-4aaa-8aaa-000000000005', 'g-dani', now(), now())`);
		await exec(`INSERT INTO cloud_saves (player_id, revision, data, summary, device_id) VALUES ('55555555-aaaa-4aaa-8aaa-000000000005', 4, ${lit(save(44))}, '{"diamonds":44}', 'dani-old')`);
		// Old builds upload to Render: Ana (never used the new build) and Bia (another phone, still on the old build).
		await exec(`UPDATE cloud_saves SET revision = 8, data = ${lit(save(80))}, summary = '{"diamonds":80,"level":4}' WHERE player_id = '11111111-aaaa-4aaa-8aaa-000000000001'`);
		await exec(`UPDATE cloud_saves SET revision = 4, data = ${lit(save(9))}, summary = '{"diamonds":9}' WHERE player_id = '22222222-aaaa-4aaa-8aaa-000000000002'`);
		const { players, saves } = await copyAll();
		assert.equal(players.aliased, 1, "Dani's Render account is the account Dani already has here");
		const outcome = Object.fromEntries(saves.map((s) => [s.player.slice(0, 2), s.outcome]));
		assert.deepEqual(outcome, { "11": "replaced-copy", "22": "kept-in-history", "44": "same", "55": "copied" });
		// Ana: Render's revision 8 is the save now; the copy it replaced is a restore point.
		assert.equal((await store.getSave("11111111-aaaa-4aaa-8aaa-000000000001"))?.revision, 8);
		// Bia: what she played here stays; Render's revision 4 is kept as a restore point, not lost.
		const biaSave = await store.getSave("22222222-aaaa-4aaa-8aaa-000000000002");
		assert.deepEqual([biaSave?.revision, biaSave?.deviceId], [4, "bia-new"]);
		const kept = db.sqlite.prepare("SELECT * FROM save_history WHERE old_id = 's:22222222-aaaa-4aaa-8aaa-000000000002:4'").get() as Record<string, unknown>;
		assert.equal(JSON.parse(new TextDecoder().decode(bucket.objects.get(String(kept.body_key)))), save(9));
		// Dani: the Render save is now the save of Dani's account here.
		assert.equal((await store.getSave(dani.player.id))?.revision, 4);
		const v = await verifyAll();
		assert.deepEqual([v.saves.identical, v.saves.keptInHistory, v.saves.problems, v.history.problems], [3, 1, [], []]);
		// And again: nothing more to do.
		assert.deepEqual((await copyAll()).saves.map((s) => s.outcome), ["same", "already", "same", "same"]);
	});

	test("the admin routes need the admin token, and answer counts only", async () => {
		const store = new Store(db, bucket);
		const app = createApp({
			store,
			verifyGoogle: async () => null,
			sessionSecret: SECRET,
			rateLimit: 1000,
			extra: adminRoutes({ publicKey: PUBLIC_KEY, oldDatabaseUrl: url, connect: nodeConnect, db, bucket, store }),
		});
		assert.equal((await app(new Request("https://w/admin/migrate/plan"), "x")).status, 404);
		const other = generateKeyPairSync("ec", { namedCurve: "P-256" }).privateKey;
		for (const bad of ["wrong", adminToken(Date.now() - 1000), adminToken(Date.now() + 3 * 3600_000), adminToken(undefined, other), `${Date.now() + 60_000}.${ADMIN.split(".")[1]}`])
			assert.equal((await app(new Request("https://w/admin/migrate/plan", { headers: { "x-admin-token": bad } }), "x")).status, 404, bad);
		const ok = await app(new Request("https://w/admin/migrate/plan", { headers: { "x-admin-token": ADMIN } }), "x");
		assert.equal(ok.status, 200);
		const text = await ok.text();
		assert.ok(!text.includes("checkout-pass") && !text.includes("state"), "no secret, no save");
		const verify = await app(new Request("https://w/admin/migrate/verify-saves?limit=50", { headers: { "x-admin-token": ADMIN } }), "x");
		assert.deepEqual(((await verify.json()) as { problems: string[] }).problems, []);
		// The benchmark player goes through the real save routes and leaves nothing behind.
		const bench = (method: string, body?: string) => app(new Request("https://w/admin/bench/save", { method, body, headers: { "x-admin-token": ADMIN } }), "x");
		assert.equal((await bench("PUT", `{"baseRevision":0,"data":${JSON.stringify(save(1))},"deviceId":"bench","force":false}`)).status, 200);
		assert.equal(((await (await bench("GET")).json()) as { data: string }).data, save(1));
		assert.equal((await app(new Request("https://w/admin/bench", { method: "DELETE", headers: { "x-admin-token": ADMIN } }), "x")).status, 200);
		assert.equal(db.sqlite.prepare("SELECT count(*) AS n FROM players WHERE id = 'bench-cpu'").get()?.n, 0);
	});
});
