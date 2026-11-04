import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { describe, test } from "node:test";
import { createApp } from "../src/app.ts";
import { DAY_MS, dayOf } from "../src/limits.ts";
import { Store } from "../src/store.ts";
import { photoUrlOf } from "../src/tokens.ts";
import { fakeD1, fakeR2 } from "./fakes.ts";

// Friends see each other's Google profile photo (docs/social-api.md › Photos): stored from the ID token on every Google
// login, sent only to accepted friends (and the player themself), hidden by the profile switch; Apple gives none.
const SECRET = "test-secret-test-secret-test-secret-123";
const T0 = dayOf(1_800_000_000_000) * DAY_MS + 10 * 3600_000;
const PHOTO = (who: string, size = "s96-c") => `https://lh3.googleusercontent.com/a/ACg8oc-${who}=${size}`;
const save = (level: number) => JSON.stringify({ state: { coins: 100, era: { id: "tenda" }, market: { level }, logistics: { premiumCurrency: 1 }, day: { dayNumber: 2 } }, version: 45 });

function world() {
	const clock = { now: T0 };
	const db = fakeD1();
	const logs: string[] = [];
	const store = new Store(db, fakeR2(), { clock: () => clock.now, log: (l) => logs.push(l) });
	/** Google tokens: "token-<name>" (with that name's photo), "token-<name>:none" (no picture), "token-<name>:<url>". */
	const pictures = new Map<string, string | undefined>();
	const app = createApp({
		store,
		verifyGoogle: async (t) => {
			if (!t.startsWith("token-")) return null;
			const [name, picture] = t.slice(6).split("|");
			const chosen = picture === undefined ? PHOTO(name) : picture === "none" ? undefined : picture;
			pictures.set(name, chosen);
			return { sub: `g-${name}`, email: `${name}@example.com`, name, ...(chosen ? { picture: chosen } : {}) };
		},
		verifyApple: async (t) => (t.startsWith("apple-") ? { sub: `a-${t.slice(6)}`, email: `${t.slice(6)}@privaterelay.appleid.com` } : null),
		sessionSecret: SECRET,
		rateLimit: 1_000_000,
		now: () => clock.now,
		log: (l) => logs.push(l),
	});
	const call = async (method: string, path: string, body?: unknown, token?: string) => {
		const response = await app(
			new Request(`https://checkout-server.example${path}`, {
				method,
				headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
				body: body === undefined ? undefined : JSON.stringify(body),
			}),
			"1.2.3.4",
		);
		const text = await response.text();
		return { status: response.status, body: text ? JSON.parse(text) : null };
	};
	type User = { token: string; id: string; code: string };
	const login = async (idToken: string, apple = false): Promise<User> => {
		const r = await call("POST", apple ? "/v1/auth/apple" : "/v1/auth/google", { idToken });
		assert.equal(r.status, 200, JSON.stringify(r.body));
		await call("PUT", "/v1/save", { baseRevision: r.body.save?.revision ?? 0, data: save(5), deviceId: "d" }, r.body.token);
		const me = (await call("GET", "/v1/social/me", undefined, r.body.token)).body;
		return { token: r.body.token, id: r.body.player.id, code: me.code };
	};
	const befriend = async (a: User, b: User) => {
		assert.equal((await call("POST", "/v1/social/friends/add", { code: b.code }, a.token)).status, 200);
		assert.equal((await call("POST", "/v1/social/friends/accept", { id: a.id }, b.token)).status, 200);
	};
	const stored = (id: string) => db.sqlite.prepare("SELECT photo_url, photo_hidden FROM players WHERE id = ?").get(id) as { photo_url: string | null; photo_hidden: number };
	return { clock, db, store, call, login, befriend, stored, logs, pictures };
}

describe("photos: the address", () => {
	test("only https on lh3…lh6.googleusercontent.com, no user/port, at most 1024 characters", () => {
		assert.equal(photoUrlOf(PHOTO("ana")), PHOTO("ana"));
		assert.equal(photoUrlOf("https://lh5.googleusercontent.com/-abc/AAAA/s96-c/photo.jpg"), "https://lh5.googleusercontent.com/-abc/AAAA/s96-c/photo.jpg");
		for (const bad of [
			"http://lh3.googleusercontent.com/a/x=s96-c",
			"https://lh3.googleusercontent.com.evil.example/a/x",
			"https://evil.example/lh3.googleusercontent.com/a/x",
			"https://lh7.googleusercontent.com/a/x",
			"https://user@lh3.googleusercontent.com/a/x",
			"https://lh3.googleusercontent.com:8443/a/x",
			"javascript:alert(1)",
			"data:image/png;base64,AAAA",
			`https://lh3.googleusercontent.com/a/${"x".repeat(1100)}`,
			"",
			42,
			null,
		])
			assert.equal(photoUrlOf(bad), null, String(bad));
	});
});

describe("photos: stored on sign-in", () => {
	test("the token's photo is stored, replaced on every Google login, kept by a login without one; a bad one is never stored", async () => {
		const w = world();
		const ana = await w.login("token-ana");
		assert.equal(w.stored(ana.id).photo_url, PHOTO("ana"));
		assert.equal(w.stored(ana.id).photo_hidden, 0);
		await w.login(`token-ana|${PHOTO("ana-new")}`);
		assert.equal(w.stored(ana.id).photo_url, PHOTO("ana-new"));
		await w.login("token-ana|none");
		assert.equal(w.stored(ana.id).photo_url, PHOTO("ana-new"), "a login without a photo keeps the last one");
		await w.login("token-ana|https://evil.example/x.png");
		assert.equal(w.stored(ana.id).photo_url, PHOTO("ana-new"), "an address off Google's hosts is dropped");
		const me = (await w.call("GET", "/v1/social/me", undefined, ana.token)).body;
		assert.equal(me.photo, PHOTO("ana-new"));
		assert.equal(me.showPhoto, true);
	});

	test("Apple accounts have none (Apple's token carries no photo)", async () => {
		const w = world();
		const eva = await w.login("apple-eva", true);
		assert.equal(w.stored(eva.id).photo_url, null);
		const me = (await w.call("GET", "/v1/social/me", undefined, eva.token)).body;
		assert.equal(me.photo, null);
		const ana = await w.login("token-ana");
		await w.befriend(ana, eva);
		const friends = (await w.call("GET", "/v1/social/friends", undefined, ana.token)).body.friends;
		assert.equal(friends[0].id, eva.id);
		assert.equal(friends[0].photo, null);
		assert.equal(friends[0].avatar, null, "the game shows the chosen avatar (default when null)");
	});
});

describe("photos: who sees them", () => {
	test("accepted friends and the player themself only: friends list, visit, friends board — never requests, inbox, Mundo, Liga", async () => {
		const w = world();
		const ana = await w.login("token-ana");
		const bia = await w.login("token-bia");
		const cris = await w.login("token-cris");
		await w.befriend(ana, bia);
		// A stranger's pending request (both ways) shows no photo.
		assert.equal((await w.call("POST", "/v1/social/friends/add", { code: ana.code }, cris.token)).status, 200);
		const anaLists = (await w.call("GET", "/v1/social/friends", undefined, ana.token)).body;
		assert.equal(anaLists.friends[0].photo, PHOTO("bia"));
		assert.equal(anaLists.incoming[0].id, cris.id);
		assert.equal("photo" in anaLists.incoming[0], false);
		const crisLists = (await w.call("GET", "/v1/social/friends", undefined, cris.token)).body;
		assert.equal("photo" in crisLists.outgoing[0], false);
		assert.ok(!JSON.stringify(crisLists).includes("googleusercontent"));
		const inbox = (await w.call("GET", "/v1/social/inbox", undefined, ana.token)).body.items;
		assert.ok(inbox.length > 0);
		assert.ok(!JSON.stringify(inbox).includes("googleusercontent"), "inbox senders carry the avatar only");
		// The visit's profile.
		const visit = await w.call("GET", `/v1/social/friends/${ana.id}/market`, undefined, bia.token);
		assert.equal(visit.status, 200);
		assert.equal(visit.body.profile.photo, PHOTO("ana"));
		assert.equal((await w.call("GET", `/v1/social/friends/${ana.id}/market`, undefined, cris.token)).status, 403);
		// Friends board: me and my friends with their photos.
		const board = (await w.call("GET", "/v1/rankings/friends", undefined, bia.token)).body.rows;
		assert.deepEqual(Object.fromEntries(board.map((r: any) => [r.id, r.photo])), { [bia.id]: PHOTO("bia"), [ana.id]: PHOTO("ana") });
		const crisBoard = (await w.call("GET", "/v1/rankings/friends", undefined, cris.token)).body.rows;
		assert.deepEqual(crisBoard.map((r: any) => r.id), [cris.id]);
		// Mundo / País / Liga: no photos for anyone, signed in or not.
		for (const path of ["/v1/rankings/world", "/v1/rankings/country?country=BR"]) {
			assert.ok(!JSON.stringify((await w.call("GET", path, undefined, cris.token)).body).includes("googleusercontent"), path);
			assert.ok(!JSON.stringify((await w.call("GET", path)).body).includes("googleusercontent"), path);
		}
		const week = (await w.call("GET", "/v1/rankings/league", undefined, bia.token)).body.week;
		await w.call("POST", "/v1/rankings/league/points", { week, points: 50 }, ana.token);
		await w.call("POST", "/v1/rankings/league/points", { week, points: 40 }, bia.token);
		const league = (await w.call("GET", "/v1/rankings/league", undefined, bia.token)).body;
		assert.ok(league.group.length >= 1);
		assert.ok(!JSON.stringify(league).includes("googleusercontent"));
	});

	test("the switch off: friends see the avatar (list, visit, board); I still get my own photo and showPhoto false; on again", async () => {
		const w = world();
		const ana = await w.login("token-ana");
		const bia = await w.login("token-bia");
		await w.befriend(ana, bia);
		assert.equal((await w.call("PUT", "/v1/social/me", { showPhoto: "no" }, ana.token)).status, 400);
		const off = await w.call("PUT", "/v1/social/me", { showPhoto: false, avatar: "shopper-4" }, ana.token);
		assert.equal(off.status, 200);
		assert.equal(off.body.showPhoto, false);
		assert.equal(off.body.photo, PHOTO("ana"));
		assert.equal(w.stored(ana.id).photo_hidden, 1);
		const seen = (await w.call("GET", "/v1/social/friends", undefined, bia.token)).body.friends[0];
		assert.equal(seen.photo, null);
		assert.equal(seen.avatar, "shopper-4");
		assert.equal((await w.call("GET", `/v1/social/friends/${ana.id}/market`, undefined, bia.token)).body.profile.photo, null);
		const board = (await w.call("GET", "/v1/rankings/friends", undefined, bia.token)).body.rows;
		assert.equal(board.find((r: any) => r.id === ana.id).photo, null);
		assert.equal((await w.call("GET", "/v1/rankings/friends", undefined, ana.token)).body.rows.find((r: any) => r.id === ana.id).photo, null, "my own row as friends see it");
		// A new Google login refreshes the address but keeps the switch.
		await w.login(`token-ana|${PHOTO("ana-2")}`);
		assert.equal(w.stored(ana.id).photo_hidden, 1);
		assert.equal((await w.call("PUT", "/v1/social/me", { showPhoto: true }, ana.token)).body.showPhoto, true);
		assert.equal((await w.call("GET", "/v1/social/friends", undefined, bia.token)).body.friends[0].photo, PHOTO("ana-2"));
	});

	test("deleting the account removes the photo with the player", async () => {
		const w = world();
		const ana = await w.login("token-ana");
		assert.equal((await w.call("DELETE", "/v1/account", undefined, ana.token)).status, 204);
		assert.equal(w.db.sqlite.prepare("SELECT COUNT(*) AS n FROM players WHERE photo_url IS NOT NULL").get()?.n, 0);
	});
});

describe("photos: schema and migration", () => {
	const migration = readFileSync(new URL("../migrations/0004_photos.sql", import.meta.url), "utf8");
	const schema = readFileSync(new URL("../schema.sql", import.meta.url), "utf8");
	const statements = migration
		.split("\n")
		.filter((line) => !line.trimStart().startsWith("--"))
		.join("\n")
		.split(";")
		.map((s) => s.trim())
		.filter(Boolean);

	test("the same statements as the end of schema.sql; says to run once", () => {
		assert.equal(statements.length, 2);
		for (const s of statements) assert.ok(schema.includes(s), `schema.sql lacks: ${s.slice(0, 60)}`);
		assert.ok(schema.indexOf("-- ── Photos") > schema.indexOf("-- ── Rankings v1"));
		assert.match(migration.slice(0, 600), /RUN IT ONCE/);
	});

	test("runs on the live database (rankings v1), keeps the players, defaults to shown; a second run stops at the first ALTER", () => {
		const sqlite = new DatabaseSync(":memory:");
		sqlite.exec(schema.slice(0, schema.indexOf("-- ── Photos")));
		sqlite.exec("INSERT INTO players (id, google_sub, created_at, last_seen) VALUES ('p1', 'g1', 1, 1)");
		sqlite.exec(migration);
		assert.deepEqual({ ...(sqlite.prepare("SELECT id, photo_url, photo_hidden FROM players").get() as object) }, { id: "p1", photo_url: null, photo_hidden: 0 });
		assert.throws(() => sqlite.exec(migration), /duplicate column name: photo_url/);
	});

	test("before the migration runs, logins, friends, the board and the switch keep working without photos", async () => {
		const w = world();
		w.db.sqlite.exec("ALTER TABLE players DROP COLUMN photo_url; ALTER TABLE players DROP COLUMN photo_hidden;");
		const ana = await w.login("token-ana");
		const bia = await w.login("token-bia");
		await w.befriend(ana, bia);
		assert.equal((await w.call("GET", "/v1/social/friends", undefined, bia.token)).body.friends[0].photo, null);
		const me = await w.call("PUT", "/v1/social/me", { showPhoto: false }, ana.token);
		assert.equal(me.status, 200);
		assert.equal(me.body.photo, null);
		const board = await w.call("GET", "/v1/rankings/friends", undefined, bia.token);
		assert.equal(board.status, 200);
		assert.equal(board.body.rows.length, 2);
		assert.ok(w.logs.some((l) => l.includes("0004_photos.sql")));
		// After the minute, the columns are tried again (here still missing: the same answers).
		w.clock.now += 61_000;
		assert.equal((await w.call("POST", "/v1/auth/google", { idToken: "token-ana" })).status, 200);
		assert.equal((await w.call("GET", `/v1/social/friends/${ana.id}/market`, undefined, bia.token)).body.profile.photo, null);
	});
});
