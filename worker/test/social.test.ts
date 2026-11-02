import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { describe, test } from "node:test";
import { createApp } from "../src/app.ts";
import { readCode } from "../src/codes.ts";
import { pickLanguage } from "../src/landing.ts";
import { DAY_MS, dayOf, SOCIAL } from "../src/limits.ts";
import { cleanName, isNameAllowed, isProfane } from "../src/names.ts";
import { readUpload } from "../src/save.ts";
import { Store } from "../src/store.ts";
import { fakeD1, fakeR2 } from "./fakes.ts";

// Social v1 (docs/social-api.md) against the Worker's own code: real schema on node:sqlite, R2 in memory.
const SECRET = "test-secret-test-secret-test-secret-123";
const T0 = dayOf(1_800_000_000_000) * DAY_MS + 10 * 3600_000; // 10:00 UTC, far from midnight
const save = (level: number, era = "mesinha", diamonds = 10) =>
	JSON.stringify({ state: { coins: 100, era: { id: era }, market: { level }, logistics: { premiumCurrency: diamonds }, day: { dayNumber: 2 } }, version: 45 });

type User = { name: string; token: string; id: string; code: string; revision: number };

function world() {
	const clock = { now: T0 };
	const db = fakeD1();
	const bucket = fakeR2();
	const logs: string[] = [];
	const store = new Store(db, bucket, { clock: () => clock.now, log: (l) => logs.push(l) });
	const app = createApp({
		store,
		verifyGoogle: async (t) => (t.startsWith("token-") ? { sub: `g-${t.slice(6)}`, email: `${t.slice(6)}@example.com`, name: t.slice(6) } : null),
		sessionSecret: SECRET,
		rateLimit: 1_000_000,
		now: () => clock.now,
		log: (l) => logs.push(l),
	});
	const call = async (method: string, path: string, body?: unknown, token?: string, headers: Record<string, string> = {}) => {
		const response = await app(
			new Request(`https://checkout-server.example${path}`, {
				method,
				headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}), ...headers },
				body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
			}),
			"1.2.3.4",
		);
		const text = await response.text();
		let parsed: any = null;
		try {
			parsed = text ? JSON.parse(text) : null;
		} catch {}
		return { status: response.status, body: parsed, text, headers: response.headers };
	};
	const user = async (name: string): Promise<User> => {
		const login = (await call("POST", "/v1/auth/google", { idToken: `token-${name}` })).body;
		const me = (await call("GET", "/v1/social/me", undefined, login.token)).body;
		return { name, token: login.token, id: login.player.id, code: me.code, revision: login.save?.revision ?? 0 };
	};
	/** The Unity upload; `pub`: the public block as the last field (object, raw JSON text, or omitted). */
	const upload = async (u: User, level: number, pub?: unknown) => {
		const tail = pub === undefined ? "" : `,"public":${typeof pub === "string" ? pub : JSON.stringify(pub)}`;
		const body = `{"baseRevision":${u.revision},"data":${JSON.stringify(save(level))},"deviceId":"phone","force":false${tail}}`;
		const r = await call("PUT", "/v1/save", body, u.token);
		assert.equal(r.status, 200, r.text);
		u.revision = r.body.revision;
		return r;
	};
	const befriend = async (a: User, b: User) => {
		assert.deepEqual((await call("POST", "/v1/social/friends/add", { code: a === b ? a.code : b.code }, a.token)).body, { status: "requested" });
		assert.deepEqual((await call("POST", "/v1/social/friends/accept", { id: a.id }, b.token)).body, { status: "friends" });
	};
	const inbox = async (u: User) => (await call("GET", "/v1/social/inbox", undefined, u.token)).body.items as any[];
	const ack = async (u: User, items: { id: number }[]) => call("POST", "/v1/social/inbox/ack", { ids: items.map((i) => i.id) }, u.token);
	const rows = (sql: string, ...values: (string | number)[]) => db.sqlite.prepare(sql).all(...values) as Record<string, any>[];
	return { clock, db, bucket, store, app, call, user, upload, befriend, inbox, ack, rows, logs };
}

describe("schema and migration", () => {
	const migration = readFileSync(new URL("../migrations/0002_social.sql", import.meta.url), "utf8");
	const schema = readFileSync(new URL("../schema.sql", import.meta.url), "utf8");
	const statements = migration
		.split("\n")
		.filter((line) => !line.startsWith("--"))
		.join("\n")
		.split(";")
		.map((s) => s.trim())
		.filter(Boolean);

	test("only CREATE … IF NOT EXISTS, and the same statements as schema.sql", () => {
		assert.ok(statements.length >= 12);
		for (const s of statements) {
			assert.match(s, /^CREATE (TABLE|INDEX) IF NOT EXISTS /, s);
			assert.ok(schema.includes(s), `schema.sql lacks: ${s.slice(0, 60)}`);
		}
	});

	test("runs on the live database's schema (before social), twice, and keeps the data", () => {
		const sqlite = new DatabaseSync(":memory:");
		sqlite.exec(schema.slice(0, schema.indexOf("-- ── Social v1")));
		sqlite.exec("INSERT INTO players (id, created_at, last_seen) VALUES ('p1', 1, 1)");
		sqlite.exec(migration);
		sqlite.exec("INSERT INTO profiles (player_id, code, created_at, updated_at) VALUES ('p1', 'ABCDEFGH', 1, 1)");
		sqlite.exec(migration);
		assert.equal((sqlite.prepare("SELECT COUNT(*) AS n FROM profiles").get() as { n: number }).n, 1);
		const tables = (sqlite.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all() as { name: string }[]).map((t) => t.name);
		for (const t of ["profiles", "friends", "friend_requests", "inbox", "daily_actions", "build_helps", "product_requests", "name_reports"]) assert.ok(tables.includes(t), t);
	});

	test("before the migration runs, saves and account deletion keep working (social reads switch off)", async () => {
		const w = world();
		for (const t of ["profiles", "friends", "friend_requests", "inbox", "daily_actions", "build_helps", "product_requests", "name_reports"]) w.db.sqlite.exec(`DROP TABLE ${t}`);
		const login = (await w.call("POST", "/v1/auth/google", { idToken: "token-old" })).body;
		const put = await w.call("PUT", "/v1/save", { baseRevision: 0, data: save(3), deviceId: "d", public: { builds: [] } }, login.token);
		assert.equal(put.status, 200);
		assert.equal((await w.call("GET", "/v1/save", undefined, login.token)).body.data, save(3));
		assert.equal((await w.call("DELETE", "/v1/account", undefined, login.token)).status, 204);
		assert.ok(w.logs.some((l) => l.includes("0002_social.sql")));
	});
});

describe("codes, names, languages", () => {
	test("codes: 8 characters without look-alikes, typed with dash/spaces/lower case", () => {
		assert.equal(readCode("7kq2-m9xa"), "7KQ2M9XA");
		assert.equal(readCode(" 7KQ2 M9XA "), "7KQ2M9XA");
		for (const bad of ["7KQ2M9X", "7KQ2M9XA1", "OKQ2M9XA", "1KQ2M9XA", "LKQ2M9XA", 42, null]) assert.equal(readCode(bad), null, String(bad));
	});

	test("market names: length, characters, any script", () => {
		for (const ok of ["Mercado do Zé", "D'Ávila & Filhos", "Mini-Mercado 7", "St. Pauli Späti", "スーパー田中", "Супермаркет", "Bäckerei Müller"]) assert.ok(isNameAllowed(cleanName(ok) as string), ok);
		for (const bad of ["ab", "x".repeat(21), "...", "Mercado 😀", "Mer​cado", "a<b>c", "Mercado #1"]) assert.equal(isNameAllowed(cleanName(bad) as string), false, bad);
		assert.equal(cleanName("  Zé   Mercado  "), "Zé Mercado");
	});

	test("profanity (pt, en, es, fr, de): normalised, whole words, worst ones inside words, no false alarms", () => {
		for (const bad of ["Puta Market", "P u t a", "p.u.t.a", "Mercado F0da", "FUCKMART", "MercadoDoCaralho", "Puuuuta", "Caralh0", "Hitler Shop", "Arrombado",
			"Pute", "Coño", "Scheiße", "Arschloch", "Fdp", "Nigga", "Niiiggga", "Merda", "Connard", "Gilipollas", "Hurensohn", "Putain", "Fuuuck", "Pu Ta",
			"Cu", "Wichser", "5hit", "B1tch", "Putas", "Encule", "рuта"])
			assert.ok(isProfane(bad), bad);
		for (const ok of ["Computadores & Cia", "Barcelona", "Ícono Mart", "Scunthorpe", "Shitake", "Niger Market", "Fagott", "Député", "Arsenal", "Cucamonga",
			"Pedro's", "Café con Leche", "Sexta Feira", "Analu", "Disputa", "As Meninas", "Rolla", "Mercado Assis", "Späti 24"])
			assert.equal(isProfane(ok), false, ok);
	});

	test("Accept-Language picks pt / en / es / fr / de (q-values), en otherwise", () => {
		assert.equal(pickLanguage("pt-BR,pt;q=0.9,en;q=0.8"), "pt");
		assert.equal(pickLanguage("de-DE"), "de");
		assert.equal(pickLanguage("ja,fr;q=0.5,es;q=0.7"), "es");
		assert.equal(pickLanguage("ja"), "en");
		assert.equal(pickLanguage(null), "en");
	});
});

describe("profile", () => {
	test("GET /me creates the profile on first call (level/era from the save), then stays the same", async () => {
		const w = world();
		assert.equal((await w.call("GET", "/v1/social/me")).status, 401);
		const login = (await w.call("POST", "/v1/auth/google", { idToken: "token-ana" })).body;
		await w.call("PUT", "/v1/save", { baseRevision: 0, data: save(6, "lojinha"), deviceId: "d" }, login.token);
		const me = (await w.call("GET", "/v1/social/me", undefined, login.token)).body;
		assert.match(me.code, /^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{8}$/);
		assert.deepEqual(
			{ ...me, code: "x" },
			{ id: login.player.id, code: "x", marketName: null, avatar: null, level: 6, era: "lojinha", likes: 0, friends: 0, invitedBy: null, invites: { rewarded: 0, milestones: [1, 3, 5] }, nameHidden: false },
		);
		assert.equal((await w.call("GET", "/v1/social/me", undefined, login.token)).body.code, me.code);
	});

	test("PUT /me: name and avatar, checked", async () => {
		const w = world();
		const ana = await w.user("ana");
		const put = (body: unknown) => w.call("PUT", "/v1/social/me", body, ana.token);
		assert.deepEqual((await put({ marketName: "ab" })).body, { error: "name-not-allowed" });
		assert.deepEqual((await put({ marketName: "Mercado da Puta" })).body, { error: "name-not-allowed" });
		assert.deepEqual((await put({ marketName: 42 })).body, { error: "name-not-allowed" });
		assert.deepEqual((await put({ avatar: "bad avatar!" })).body, { error: "bad-avatar" });
		assert.deepEqual((await put({ avatar: 3 })).body, { error: "bad-avatar" });
		const ok = await put({ marketName: "  Mercado   da Ana ", avatar: "chef-2" });
		assert.equal(ok.status, 200);
		assert.equal(ok.body.marketName, "Mercado da Ana");
		assert.equal(ok.body.avatar, "chef-2");
		assert.equal((await put({ avatar: null })).body.avatar, null);
		assert.equal((await put({})).body.marketName, "Mercado da Ana");
		assert.equal((await w.call("PUT", "/v1/social/me", "x".repeat(20_000), ana.token)).status, 413);
	});
});

describe("friends", () => {
	test("add by code → request (inbox), accept → friends both ways (inbox), decline, remove", async () => {
		const w = world();
		const [ana, bia, cris] = [await w.user("ana"), await w.user("bia"), await w.user("cris")];
		const add = (u: User, code: unknown) => w.call("POST", "/v1/social/friends/add", { code }, u.token);
		assert.deepEqual((await add(ana, ana.code)).body, { error: "self" });
		assert.equal((await add(ana, "ZZZZ-ZZZZ")).status, 404);
		assert.equal((await add(ana, "nope")).status, 404);
		const dashed = `${bia.code.slice(0, 4)}-${bia.code.slice(4)}`.toLowerCase();
		assert.deepEqual((await add(ana, dashed)).body, { status: "requested" });
		assert.deepEqual((await add(ana, bia.code)).body, { status: "requested" }, "asking again changes nothing");
		const biaInbox = await w.inbox(bia);
		assert.equal(biaInbox.length, 1);
		assert.equal(biaInbox[0].kind, "friend_request");
		assert.equal(biaInbox[0].from.id, ana.id);
		assert.deepEqual(biaInbox[0].payload, {});
		const lists = (await w.call("GET", "/v1/social/friends", undefined, bia.token)).body;
		assert.deepEqual(lists.incoming.map((p: any) => p.id), [ana.id]);
		assert.deepEqual(Object.keys(lists.incoming[0]), ["id", "code", "marketName", "avatar", "level", "era"]);
		assert.deepEqual((await w.call("GET", "/v1/social/friends", undefined, ana.token)).body.outgoing.map((p: any) => p.id), [bia.id]);
		// Accept.
		assert.equal((await w.call("POST", "/v1/social/friends/accept", { id: cris.id }, bia.token)).status, 404, "no request from cris");
		assert.deepEqual((await w.call("POST", "/v1/social/friends/accept", { id: ana.id }, bia.token)).body, { status: "friends" });
		assert.deepEqual((await w.call("POST", "/v1/social/friends/accept", { id: ana.id }, bia.token)).body, { status: "friends" });
		const added = (await w.inbox(ana)).find((i) => i.kind === "friend_added");
		assert.deepEqual(added.payload, { via: "code" });
		assert.equal(added.from.id, bia.id);
		assert.deepEqual((await add(ana, bia.code)).body, { error: "already-friends" });
		const anaLists = (await w.call("GET", "/v1/social/friends", undefined, ana.token)).body;
		assert.deepEqual([anaLists.friends.length, anaLists.incoming.length, anaLists.outgoing.length], [1, 0, 0]);
		assert.deepEqual(Object.keys(anaLists.friends[0]).sort(), ["avatar", "code", "era", "giftedToday", "id", "level", "likedToday", "likes", "lastSeen", "marketName", "openRequests", "public"].sort());
		assert.equal((await w.call("GET", "/v1/social/me", undefined, ana.token)).body.friends, 1);
		// Both adding each other's code: the second add accepts.
		assert.deepEqual((await add(cris, ana.code)).body, { status: "requested" });
		assert.deepEqual((await add(ana, cris.code)).body, { status: "friends" });
		// Decline.
		const dani = await w.user("dani");
		await add(dani, bia.code);
		assert.equal((await w.call("POST", "/v1/social/friends/decline", { id: dani.id }, bia.token)).status, 204);
		assert.equal((await w.call("GET", "/v1/social/friends", undefined, bia.token)).body.incoming.length, 0);
		// Remove: both sides, and requests between them.
		assert.equal((await w.call("DELETE", `/v1/social/friends/${bia.id}`, undefined, ana.token)).status, 204);
		assert.equal((await w.call("GET", "/v1/social/friends", undefined, bia.token)).body.friends.length, 0);
		assert.equal(w.rows("SELECT * FROM friends WHERE player_id IN (?, ?) AND friend_id IN (?, ?)", ana.id, bia.id, ana.id, bia.id).length, 0);
		assert.equal((await w.call("DELETE", `/v1/social/friends/${bia.id}`, undefined, ana.token)).status, 204, "idempotent");
	});

	test("friend cap (50, both sides, also when two accepts race) and pending outgoing cap (20)", async () => {
		const w = world();
		const [ana, bia, cris] = [await w.user("ana"), await w.user("bia"), await w.user("cris")];
		const fill = (u: User, n: number) => {
			for (let i = 0; i < n; i++) w.db.sqlite.prepare("INSERT INTO friends VALUES (?, ?, ?)").run(u.id, `filler-${u.name}-${i}`, T0);
		};
		fill(ana, SOCIAL.maxFriends);
		assert.deepEqual((await w.call("POST", "/v1/social/friends/add", { code: bia.code }, ana.token)).body, { error: "limit" });
		assert.deepEqual((await w.call("POST", "/v1/social/friends/add", { code: ana.code }, bia.token)).body, { error: "limit" }, "their list is full");
		// 49 friends and two requests: accepting both at once makes only one friend.
		w.db.sqlite.prepare("DELETE FROM friends WHERE player_id = ? AND friend_id = ?").run(ana.id, `filler-ana-0`);
		w.db.sqlite.prepare("INSERT INTO friend_requests VALUES (?, ?, ?), (?, ?, ?)").run(bia.id, ana.id, T0, cris.id, ana.id, T0);
		const both = await Promise.all([bia, cris].map((u) => w.call("POST", "/v1/social/friends/accept", { id: u.id }, ana.token)));
		assert.deepEqual(both.map((r) => r.status).sort(), [200, 429]);
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM friends WHERE player_id = ?", ana.id)[0].n, SOCIAL.maxFriends);
		const loser = both[0].status === 429 ? bia : cris;
		assert.equal(w.rows("SELECT * FROM friends WHERE player_id = ? AND friend_id = ?", loser.id, ana.id).length, 0, "no half friendship");
		// Outgoing requests.
		const dani = await w.user("dani");
		const targets: User[] = [];
		for (let i = 0; i < SOCIAL.maxOutgoingRequests + 1; i++) targets.push(await w.user(`t${i}`));
		for (const t of targets.slice(0, SOCIAL.maxOutgoingRequests)) assert.equal((await w.call("POST", "/v1/social/friends/add", { code: t.code }, dani.token)).status, 200);
		assert.deepEqual((await w.call("POST", "/v1/social/friends/add", { code: targets[SOCIAL.maxOutgoingRequests].code }, dani.token)).body, { error: "limit" });
	});

	test("not friends → 403 for visit, gift, like, help, fulfil", async () => {
		const w = world();
		const [ana, bia] = [await w.user("ana"), await w.user("bia")];
		await w.upload(bia, 3, { builds: [{ id: "b1" }] });
		const request = (await w.call("POST", "/v1/social/requests", { productId: "milk", qty: 2 }, bia.token)).body;
		const expect403 = async (method: string, path: string, body?: unknown) => assert.deepEqual((await w.call(method, path, body, ana.token)).body, { error: "not-friends" }, path);
		await expect403("GET", `/v1/social/friends/${bia.id}/market`);
		await expect403("POST", "/v1/social/gift", { to: bia.id });
		await expect403("POST", "/v1/social/like", { to: bia.id });
		await expect403("POST", "/v1/social/help", { to: bia.id, buildId: "b1" });
		await expect403("POST", `/v1/social/requests/${request.id}/fulfill`);
		await expect403("POST", "/v1/social/gift", { to: ana.id });
		assert.equal((await w.inbox(bia)).length, 0, "nothing was delivered");
	});
});

describe("visits, gifts, likes, helps", () => {
	test("visit: the friend's save exactly as GET /v1/save returns it, profile, public block; 404 without a save", async () => {
		const w = world();
		const [ana, bia] = [await w.user("ana"), await w.user("bia")];
		await w.befriend(ana, bia);
		assert.deepEqual((await w.call("GET", `/v1/social/friends/${bia.id}/market`, undefined, ana.token)).body, { error: "no-save" });
		const pub = { builds: [{ id: "interior:42:1793", kind: "interior", item: "shelf-produce", tier: 3, endsAt: 1793570000000 }], stage: "spati", marketRating: 4.2 };
		await w.upload(bia, 8, pub);
		await w.call("PUT", "/v1/social/me", { marketName: "Späti da Bia & Cia" }, bia.token);
		const visit = await w.call("GET", `/v1/social/friends/${bia.id}/market`, undefined, ana.token);
		assert.equal(visit.status, 200);
		assert.deepEqual(Object.keys(visit.body), ["profile", "public", "data"]);
		assert.equal(visit.body.data, (await w.call("GET", "/v1/save", undefined, bia.token)).body.data);
		assert.deepEqual(visit.body.public, pub);
		assert.deepEqual(visit.body.profile.public, pub);
		assert.equal(visit.body.profile.marketName, "Späti da Bia & Cia");
		assert.equal(visit.body.profile.level, 8);
		assert.equal(visit.body.profile.lastSeen, T0);
	});

	test("gift: once per friend per UTC day; the receiver is offered at most 25 a day, the rest wait", async () => {
		const w = world();
		const [ana, bia] = [await w.user("ana"), await w.user("bia")];
		await w.befriend(ana, bia);
		assert.equal((await w.call("POST", "/v1/social/gift", { to: bia.id }, ana.token)).status, 204);
		assert.deepEqual((await w.call("POST", "/v1/social/gift", { to: bia.id }, ana.token)).body, { error: "already-today" });
		assert.equal((await w.call("GET", "/v1/social/friends", undefined, ana.token)).body.friends[0].giftedToday, true);
		w.clock.now += DAY_MS;
		assert.equal((await w.call("GET", "/v1/social/friends", undefined, ana.token)).body.friends[0].giftedToday, false);
		assert.equal((await w.call("POST", "/v1/social/gift", { to: bia.id }, ana.token)).status, 204, "a new day");
		assert.equal(w.rows("SELECT * FROM daily_actions WHERE player_id = ? AND day < ?", ana.id, dayOf(w.clock.now)).length, 0, "old days are cleaned up");
		// 30 gifts waiting (as if from 30 friends) + one like.
		const cris = await w.user("cris");
		const insert = w.db.sqlite.prepare("INSERT INTO inbox (player_id, kind, from_id, payload, created_at) VALUES (?, ?, ?, '{}', ?)");
		for (let i = 0; i < 28; i++) insert.run(cris.id, "gift", ana.id, w.clock.now);
		insert.run(cris.id, "like", ana.id, w.clock.now);
		insert.run(cris.id, "gift", ana.id, w.clock.now);
		insert.run(cris.id, "gift", ana.id, w.clock.now);
		let items = await w.inbox(cris);
		assert.equal(items.filter((i) => i.kind === "gift").length, SOCIAL.maxGiftsClaimedPerDay);
		assert.equal(items.filter((i) => i.kind === "like").length, 1, "other kinds are not held back");
		await w.ack(cris, items);
		items = await w.inbox(cris);
		assert.equal(items.length, 0, "25 claimed today: the other 5 wait");
		w.clock.now += DAY_MS;
		items = await w.inbox(cris);
		assert.equal(items.filter((i) => i.kind === "gift").length, 5);
	});

	test("like: once per friend per day, counts on the owner's profile, inbox item", async () => {
		const w = world();
		const [ana, bia] = [await w.user("ana"), await w.user("bia")];
		await w.befriend(ana, bia);
		assert.deepEqual((await w.call("POST", "/v1/social/like", { to: bia.id }, ana.token)).body, { likes: 1 });
		assert.deepEqual((await w.call("POST", "/v1/social/like", { to: bia.id }, ana.token)).body, { error: "already-today" });
		assert.equal((await w.call("GET", "/v1/social/friends", undefined, ana.token)).body.friends[0].likedToday, true);
		assert.equal((await w.call("GET", "/v1/social/me", undefined, bia.token)).body.likes, 1);
		assert.deepEqual((await w.call("POST", "/v1/social/like", { to: ana.id }, bia.token)).body, { likes: 1 });
		w.clock.now += DAY_MS;
		assert.deepEqual((await w.call("POST", "/v1/social/like", { to: bia.id }, ana.token)).body, { likes: 2 });
		assert.deepEqual((await w.inbox(bia)).filter((i) => i.kind === "like").length, 2);
	});

	test("help: on a build of the friend's public block; once per build; max 10 per build (also racing); 30 a day", async () => {
		const w = world();
		const owner = await w.user("owner");
		const builds = Array.from({ length: 12 }, (_, i) => ({ id: `interior:${i}:1793`, kind: "interior", item: "shelf", tier: 1, endsAt: T0 + 3600_000 }));
		await w.upload(owner, 5, { builds, stage: "lojinha", marketRating: 3 });
		const helpers: User[] = [];
		for (let i = 0; i < 12; i++) {
			const h = await w.user(`h${i}`);
			await w.befriend(h, owner);
			helpers.push(h);
		}
		const help = (u: User, buildId: unknown, to = owner.id) => w.call("POST", "/v1/social/help", { to, buildId }, u.token);
		assert.deepEqual((await help(helpers[0], "interior:0:1793")).body, { helps: 1 });
		assert.deepEqual((await help(helpers[0], "interior:0:1793")).body, { error: "already-helped" });
		assert.deepEqual((await help(helpers[0], "no-such-build")).body, { error: "no-build" });
		assert.equal((await help(helpers[0], "no-such-build")).status, 404);
		assert.equal((await help(helpers[0], 42)).status, 404);
		const item = (await w.inbox(owner)).find((i) => i.kind === "help");
		assert.deepEqual(item.payload, { buildId: "interior:0:1793", minutes: 5 });
		assert.equal(item.from.id, helpers[0].id);
		for (let i = 1; i < 8; i++) assert.equal((await help(helpers[i], "interior:0:1793")).body.helps, i + 1);
		// 8 helps: three more at once → only 2 fit.
		const race = await Promise.all([8, 9, 10].map((i) => help(helpers[i], "interior:0:1793")));
		assert.deepEqual(race.map((r) => r.status).sort(), [200, 200, 409]);
		assert.equal(race.find((r) => r.status === 409)?.body.error, "build-full");
		assert.deepEqual((await help(helpers[11], "interior:0:1793")).body, { error: "build-full" });
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM build_helps WHERE owner_id = ? AND build_id = ?", owner.id, "interior:0:1793")[0].n, SOCIAL.maxHelpsPerBuild);
		assert.equal((await w.inbox(owner)).filter((i) => i.kind === "help").length, SOCIAL.maxHelpsPerBuild, "one inbox item per counted help");
		// Daily limit: helper 11 helps 30 builds across three friends (12 + 12 + 6), then one more is refused.
		const others = [await w.user("o2"), await w.user("o3")];
		for (const o of others) {
			await w.upload(o, 5, { builds });
			await w.befriend(helpers[11], o);
		}
		let given = 0;
		for (const target of [owner, ...others])
			for (const b of builds) {
				if (given === SOCIAL.maxHelpsGivenPerDay) break;
				if (target === owner && b.id === "interior:0:1793") continue;
				assert.equal((await help(helpers[11], b.id, target.id)).status, 200);
				given++;
			}
		const refused = await help(helpers[11], builds[11].id, others[1].id);
		assert.equal(refused.status, 429);
		assert.deepEqual(refused.body, { error: "daily-limit" });
		w.clock.now += DAY_MS;
		assert.equal((await help(helpers[11], builds[11].id, others[1].id)).status, 200, "a new day");
	});
});

describe("product requests", () => {
	test("create (checked, max 2 open), list, cancel, fulfil once (racing), expire after 24 h", async () => {
		const w = world();
		const [ana, bia, cris] = [await w.user("ana"), await w.user("bia"), await w.user("cris")];
		await w.befriend(ana, bia);
		await w.befriend(cris, bia);
		const create = (body: unknown, u = bia) => w.call("POST", "/v1/social/requests", body, u.token);
		for (const bad of [{ productId: "milk", qty: 0 }, { productId: "milk", qty: 21 }, { productId: "milk", qty: 1.5 }, { productId: "", qty: 2 }, { productId: "x y", qty: 2 }, { qty: 2 }])
			assert.deepEqual((await create(bad)).body, { error: "bad-request" }, JSON.stringify(bad));
		const first = (await create({ productId: "milk", qty: 5 })).body;
		assert.deepEqual(first, { id: first.id, productId: "milk", qty: 5, createdAt: T0, expiresAt: T0 + SOCIAL.requestTtlMs });
		const second = (await create({ productId: "bread", qty: 20 })).body;
		assert.deepEqual((await create({ productId: "eggs", qty: 1 })).body, { error: "limit" });
		// Lists.
		const seen = (await w.call("GET", "/v1/social/requests", undefined, ana.token)).body;
		assert.deepEqual(seen.mine, []);
		assert.deepEqual(seen.friends, [{ ...first, owner: bia.id }, { ...second, owner: bia.id }]);
		assert.deepEqual((await w.call("GET", "/v1/social/requests", undefined, bia.token)).body.mine, [first, second]);
		assert.deepEqual((await w.call("GET", "/v1/social/friends", undefined, ana.token)).body.friends[0].openRequests, [first, second]);
		// Cancel: only the owner, only open.
		assert.equal((await w.call("DELETE", `/v1/social/requests/${second.id}`, undefined, ana.token)).status, 404);
		assert.equal((await w.call("DELETE", `/v1/social/requests/${second.id}`, undefined, bia.token)).status, 204);
		assert.equal((await w.call("DELETE", `/v1/social/requests/${second.id}`, undefined, bia.token)).status, 404);
		assert.deepEqual((await w.call("POST", `/v1/social/requests/${second.id}/fulfill`, undefined, ana.token)).body, { error: "taken" });
		assert.equal((await w.call("POST", "/v1/social/requests/999999/fulfill", undefined, ana.token)).status, 404);
		// Two friends fulfil at once: one wins, exactly one delivery.
		const race = await Promise.all([ana, cris].map((u) => w.call("POST", `/v1/social/requests/${first.id}/fulfill`, undefined, u.token)));
		assert.deepEqual(race.map((r) => r.status).sort(), [204, 409]);
		assert.equal(race.find((r) => r.status === 409)?.body.error, "taken");
		const items = await w.inbox(bia);
		const deliveries = items.filter((i) => i.kind === "delivery");
		assert.equal(deliveries.length, 1);
		assert.deepEqual(deliveries[0].payload, { requestId: first.id, productId: "milk", qty: 5 });
		assert.deepEqual(items.filter((i) => i.kind === "request_fulfilled").map((i) => i.payload), [{ requestId: first.id }]);
		const winner = race[0].status === 204 ? ana : cris;
		assert.equal(deliveries[0].from.id, winner.id);
		assert.equal(w.rows("SELECT fulfilled_by FROM product_requests WHERE id = ?", first.id)[0].fulfilled_by, winner.id);
		assert.deepEqual((await w.call("POST", `/v1/social/requests/${first.id}/fulfill`, undefined, ana.token)).body, { error: "taken" });
		// Expiry.
		const third = (await create({ productId: "rice", qty: 3 })).body;
		w.clock.now += SOCIAL.requestTtlMs;
		assert.deepEqual((await w.call("POST", `/v1/social/requests/${third.id}/fulfill`, undefined, ana.token)).body, { error: "taken" });
		assert.deepEqual((await w.call("GET", "/v1/social/requests", undefined, ana.token)).body.friends, []);
		assert.equal((await create({ productId: "eggs", qty: 1 })).status, 200);
		assert.equal((await create({ productId: "eggs", qty: 1 })).status, 200, "expired ones stop counting");
		assert.equal(w.rows("SELECT status FROM product_requests WHERE id = ?", third.id)[0].status, "expired");
	});
});

describe("inbox", () => {
	test("unacked items oldest first; ack only own ids; acked ones are cleaned up after 7 days", async () => {
		const w = world();
		const [ana, bia] = [await w.user("ana"), await w.user("bia")];
		await w.befriend(ana, bia);
		await w.ack(bia, await w.inbox(bia)); // the friend request
		await w.call("POST", "/v1/social/gift", { to: bia.id }, ana.token);
		await w.call("POST", "/v1/social/like", { to: bia.id }, ana.token);
		const items = await w.inbox(bia);
		assert.deepEqual(items.map((i) => i.kind), ["gift", "like"]);
		assert.deepEqual(Object.keys(items[0]).sort(), ["createdAt", "from", "id", "kind", "payload"]);
		assert.deepEqual(Object.keys(items[0].from), ["id", "code", "marketName", "avatar"]);
		assert.equal((await w.ack(ana, items)).status, 204, "someone else's ids: nothing happens");
		assert.equal((await w.inbox(bia)).length, 2);
		for (const bad of [{ ids: "1" }, { ids: [0] }, { ids: [1.5] }, { ids: ["1"] }, { ids: Array(SOCIAL.maxAckIds + 1).fill(1) }])
			assert.deepEqual((await w.call("POST", "/v1/social/inbox/ack", bad, bia.token)).body, { error: "bad-request" });
		assert.equal((await w.ack(bia, [items[0]])).status, 204);
		assert.deepEqual((await w.inbox(bia)).map((i) => i.kind), ["like"]);
		assert.equal((await w.ack(bia, [items[0]])).status, 204, "acking twice is fine");
		w.clock.now += SOCIAL.keepAckedMs + 1;
		await w.ack(bia, [items[1]]);
		assert.deepEqual(w.rows("SELECT kind FROM inbox WHERE player_id = ?", bia.id).map((r) => r.kind), ["like"], "the old acked items are gone");
	});
});

describe("invites", () => {
	test("redeem: not your own code, unknown code, once per account, only during the first 7 days, no circular invites", async () => {
		const w = world();
		const [ana, bia] = [await w.user("ana"), await w.user("bia")];
		const redeem = (u: User, code: unknown) => w.call("POST", "/v1/social/invite/redeem", { code }, u.token);
		assert.deepEqual((await redeem(bia, bia.code)).body, { error: "self" });
		assert.equal((await redeem(bia, "ZZZZZZZZ")).status, 404);
		assert.deepEqual((await redeem(bia, ana.code)).body, { status: "friends" });
		const notice = (await w.inbox(ana)).find((i) => i.kind === "friend_added");
		assert.deepEqual(notice.payload, { via: "invite" });
		assert.equal(notice.from.id, bia.id);
		assert.equal((await w.call("GET", "/v1/social/me", undefined, bia.token)).body.invitedBy, ana.code);
		const cris = await w.user("cris");
		assert.deepEqual((await redeem(bia, cris.code)).body, { error: "already-invited" });
		assert.deepEqual((await redeem(ana, bia.code)).body, { error: "self" }, "bia was invited by ana: no invite back");
		w.clock.now += SOCIAL.inviteRedeemWindowMs;
		assert.deepEqual((await redeem(cris, ana.code)).body, { error: "too-late" });
	});

	test("redeem when the inviter's list is full: the invite counts, no friendship", async () => {
		const w = world();
		const [ana, bia] = [await w.user("ana"), await w.user("bia")];
		for (let i = 0; i < SOCIAL.maxFriends; i++) w.db.sqlite.prepare("INSERT INTO friends VALUES (?, ?, ?)").run(ana.id, `filler-${i}`, T0);
		assert.deepEqual((await w.call("POST", "/v1/social/invite/redeem", { code: ana.code }, bia.token)).body, { status: "invited" });
		assert.equal((await w.call("GET", "/v1/social/me", undefined, bia.token)).body.invitedBy, ana.code);
	});

	test("reward when the invited player reaches level 8: both get 30 💎, milestones 1/3/5, never twice", async () => {
		const w = world();
		const inviter = await w.user("inviter");
		const rewards = async (u: User) => {
			const items = (await w.inbox(u)).filter((i) => i.kind === "invite_reward");
			await w.ack(u, items);
			return items;
		};
		const milestones: unknown[] = [];
		for (let n = 1; n <= 6; n++) {
			const invited = await w.user(`invited${n}`);
			await w.call("POST", "/v1/social/invite/redeem", { code: inviter.code }, invited.token);
			await w.upload(invited, 7);
			assert.equal((await rewards(invited)).length, 0, "level 7: not yet");
			await w.upload(invited, 8);
			const mine = await rewards(invited);
			assert.deepEqual(mine.map((i) => i.payload), [{ diamonds: 30, role: "invited" }]);
			assert.equal(mine[0].from.id, inviter.id);
			const theirs = await rewards(inviter);
			assert.equal(theirs.length, 1);
			assert.equal(theirs[0].from.id, invited.id);
			assert.equal(theirs[0].payload.role, "inviter");
			assert.equal(theirs[0].payload.diamonds, 30);
			milestones.push(theirs[0].payload.milestone);
			// Never twice: more uploads, a direct refresh, two at once.
			await w.upload(invited, 9);
			await Promise.all([w.store.refreshProfile(invited.id, { level: 9, era: "x" }, undefined), w.store.refreshProfile(invited.id, { level: 9, era: "x" }, undefined)]);
			assert.equal((await rewards(invited)).length + (await rewards(inviter)).length, 0);
		}
		assert.deepEqual(milestones, [1, undefined, 3, undefined, 5, undefined]);
		assert.deepEqual((await w.call("GET", "/v1/social/me", undefined, inviter.token)).body.invites, { rewarded: 6, milestones: [1, 3, 5] });
	});

	test("redeeming when already at level 8 rewards right away; an inviter deleted since still leaves the invited player's reward", async () => {
		const w = world();
		const [ana, bia, cris] = [await w.user("ana"), await w.user("bia"), await w.user("cris")];
		await w.upload(bia, 9);
		assert.deepEqual((await w.call("POST", "/v1/social/invite/redeem", { code: ana.code }, bia.token)).body, { status: "friends" });
		assert.deepEqual((await w.inbox(bia)).filter((i) => i.kind === "invite_reward").map((i) => i.payload), [{ diamonds: 30, role: "invited" }]);
		assert.deepEqual((await w.inbox(ana)).filter((i) => i.kind === "invite_reward").map((i) => i.payload), [{ diamonds: 30, role: "inviter", milestone: 1 }]);
		// cris is invited by ana, ana deletes the account, cris reaches level 8.
		await w.call("POST", "/v1/social/invite/redeem", { code: ana.code }, cris.token);
		assert.equal((await w.call("DELETE", "/v1/account", undefined, ana.token)).status, 204);
		await w.upload(cris, 8);
		const reward = (await w.inbox(cris)).filter((i) => i.kind === "invite_reward");
		assert.deepEqual(reward.map((i) => [i.payload, i.from]), [[{ diamonds: 30, role: "invited" }, null]]);
		assert.deepEqual((await w.call("POST", "/v1/social/invite/redeem", { code: bia.code }, cris.token)).body, { error: "already-invited" });
	});
});

describe("market names: reports", () => {
	test("3 distinct reporters hide the name until it is changed (not respelled)", async () => {
		const w = world();
		const [ana, bia, cris, dani, eva] = [await w.user("ana"), await w.user("bia"), await w.user("cris"), await w.user("dani"), await w.user("eva")];
		await w.call("PUT", "/v1/social/me", { marketName: "Mercado Zé" }, ana.token);
		await w.befriend(eva, ana);
		const nameSeenByEva = async () => (await w.call("GET", "/v1/social/friends", undefined, eva.token)).body.friends[0].marketName;
		const report = (u: User, id = ana.id) => w.call("POST", "/v1/social/report", { id }, u.token);
		assert.equal((await report(bia, "no-such-player")).status, 404);
		assert.equal((await report(ana)).status, 204, "reporting yourself does nothing");
		assert.equal((await report(bia)).status, 204);
		assert.equal((await report(bia)).status, 204);
		assert.equal((await report(cris)).status, 204);
		assert.equal(await nameSeenByEva(), "Mercado Zé", "two distinct reporters so far");
		await report(dani);
		assert.equal(await nameSeenByEva(), null);
		const own = (await w.call("GET", "/v1/social/me", undefined, ana.token)).body;
		assert.deepEqual([own.marketName, own.nameHidden], ["Mercado Zé", true]);
		assert.equal((await w.call("GET", `/i/${ana.code}`)).text.includes("Mercado Zé"), false, "not on the invite page either");
		assert.deepEqual((await w.call("PUT", "/v1/social/me", { marketName: "mercado ze" }, ana.token)).body, { error: "name-not-allowed" });
		const renamed = (await w.call("PUT", "/v1/social/me", { marketName: "Mercado Novo" }, ana.token)).body;
		assert.deepEqual([renamed.marketName, renamed.nameHidden], ["Mercado Novo", false]);
		assert.equal(await nameSeenByEva(), "Mercado Novo");
		await report(bia);
		await report(cris);
		assert.equal(await nameSeenByEva(), "Mercado Novo", "the old reports were cleared");
	});
});

describe("the save upload and the public block", () => {
	test("an old client (no public) behaves exactly as before; the profile's level/era follow the save", async () => {
		const w = world();
		const login = (await w.call("POST", "/v1/auth/google", { idToken: "token-old" })).body;
		const body = `{"baseRevision":0,"data":${JSON.stringify(save(4))},"deviceId":"phone","force":false}`;
		const put = await w.call("PUT", "/v1/save", body, login.token);
		assert.equal(put.status, 200);
		assert.deepEqual(Object.keys(put.body), ["revision", "updatedAt", "summary", "deviceId"]);
		assert.equal(w.rows("SELECT COUNT(*) AS n FROM profiles")[0].n, 0, "no profile is created by an upload");
		const me = (await w.call("GET", "/v1/social/me", undefined, login.token)).body;
		assert.equal(me.level, 4);
		const u: User = { name: "old", token: login.token, id: login.player.id, code: me.code, revision: 1 };
		u.revision = (await w.call("PUT", "/v1/save", `{"baseRevision":1,"data":${JSON.stringify(save(5, "lojinha"))},"deviceId":"phone","force":false}`, u.token)).body.revision;
		const row = w.rows("SELECT level, era, public_json FROM profiles WHERE player_id = ?", u.id)[0];
		assert.deepEqual({ ...row }, { level: 5, era: "lojinha", public_json: null });
		await w.upload(u, 5, { builds: [{ id: "a" }] });
		u.revision = (await w.call("PUT", "/v1/save", `{"baseRevision":${u.revision},"data":${JSON.stringify(save(5))},"deviceId":"phone","force":false}`, u.token)).body.revision;
		assert.equal(w.rows("SELECT public_json FROM profiles WHERE player_id = ?", u.id)[0].public_json, '{"builds":[{"id":"a"}]}', "no public block: the last one is kept");
	});

	test("the public block: stored as sent (fast path), checked (object, ≤ 4 KB, ≤ 12 builds), refused ones never refuse the save", async () => {
		const w = world();
		const u = await w.user("ana");
		const stored = () => w.rows("SELECT public_json FROM profiles WHERE player_id = ?", u.id)[0].public_json;
		await w.upload(u, 3, '{"builds":[{"id":"x","endsAt":1793570000000}],"stage":"mesinha","marketRating":4.199999809265137}');
		assert.equal(stored(), '{"builds":[{"id":"x","endsAt":1793570000000}],"stage":"mesinha","marketRating":4.199999809265137}');
		for (const bad of [[1, 2], { builds: Array(13).fill({ id: "b" }) }, { builds: "x" }, { pad: "x".repeat(4100) }, 42]) {
			await w.upload(u, 3, bad);
			assert.match(stored(), /"id":"x"/, JSON.stringify(bad).slice(0, 40));
		}
		assert.ok(w.logs.some((l) => l.startsWith("public block refused")));
		await w.upload(u, 3, null);
		assert.equal(stored(), null, "null clears it");
		// Any other key order works too (the general path).
		const other = await w.call("PUT", "/v1/save", { public: { builds: [] }, deviceId: "pc", data: save(3), baseRevision: u.revision }, u.token);
		assert.equal(other.status, 200);
		assert.equal(stored(), '{"builds":[]}');
		// The fast path: the save's literal is cut out of the body, the public block taken as sent.
		const data = save(3);
		const fast = readUpload(new TextEncoder().encode(`{"baseRevision":2,"data":${JSON.stringify(data)},"deviceId":"d","force":true,"public":{"a":"ã"}}`));
		assert.equal(new TextDecoder().decode(fast.literal), JSON.stringify(data));
		assert.deepEqual([fast.public, fast.force, fast.deviceId], ['{"a":"ã"}', true, "d"]);
		assert.equal(readUpload(new TextEncoder().encode(`{"baseRevision":2,"data":${JSON.stringify(data)},"deviceId":"d","force":false}`)).public, undefined);
	});
});

describe("account deletion", () => {
	test("removes every social row of the player, both sides of friendships, requests and inbox", async () => {
		const w = world();
		const [ana, bia, cris] = [await w.user("ana"), await w.user("bia"), await w.user("cris")];
		await w.call("PUT", "/v1/social/me", { marketName: "Mercado da Ana" }, ana.token);
		await w.upload(ana, 8, { builds: [{ id: "b1" }] });
		await w.upload(bia, 3, { builds: [{ id: "b2" }] });
		await w.befriend(ana, bia);
		await w.call("POST", "/v1/social/friends/add", { code: cris.code }, ana.token);
		await w.call("POST", "/v1/social/gift", { to: bia.id }, ana.token);
		await w.call("POST", "/v1/social/like", { to: ana.id }, bia.token);
		await w.call("POST", "/v1/social/help", { to: bia.id, buildId: "b2" }, ana.token);
		await w.call("POST", "/v1/social/help", { to: ana.id, buildId: "b1" }, bia.token);
		const req = (await w.call("POST", "/v1/social/requests", { productId: "milk", qty: 1 }, ana.token)).body;
		const biaReq = (await w.call("POST", "/v1/social/requests", { productId: "egg", qty: 1 }, bia.token)).body;
		await w.call("POST", `/v1/social/requests/${biaReq.id}/fulfill`, undefined, ana.token);
		await w.call("POST", "/v1/social/report", { id: bia.id }, ana.token);
		await w.call("PUT", "/v1/social/me", { marketName: "Mercado da Bia" }, bia.token);
		await w.call("POST", "/v1/social/report", { id: ana.id }, bia.token);
		await w.call("POST", "/v1/social/invite/redeem", { code: ana.code }, cris.token);
		assert.ok(req.id);

		assert.equal((await w.call("DELETE", "/v1/account", undefined, ana.token)).status, 204);
		const tables = ["profiles", "friends", "friend_requests", "inbox", "daily_actions", "build_helps", "product_requests", "name_reports"];
		for (const table of tables) {
			const columns = (w.db.sqlite.prepare(`PRAGMA table_info(${table})`).all() as { name: string }[]).map((c) => c.name);
			const hits = w.rows(`SELECT * FROM ${table} WHERE ${columns.map((c) => `${c} = ?`).join(" OR ")}`, ...columns.map(() => ana.id));
			assert.deepEqual(hits, [], `${table} still mentions the deleted player`);
		}
		const biaView = (await w.call("GET", "/v1/social/friends", undefined, bia.token)).body;
		assert.equal(biaView.friends.length, 0);
		// What ana sent stays with its receiver, anonymous: bia's gift and the delivery.
		const biaInbox = await w.inbox(bia);
		assert.ok(biaInbox.some((i) => i.kind === "delivery" && i.from === null));
		assert.ok(biaInbox.some((i) => i.kind === "gift" && i.from === null));
		assert.equal((await w.call("GET", "/v1/social/friends", undefined, cris.token)).body.incoming.length, 0);
		assert.equal((await w.call("GET", "/v1/social/me", undefined, cris.token)).body.invitedBy, null);
	});
});

describe("the invite page GET /i/<code>", () => {
	test("in the visitor's language, with the inviter's name (escaped), copy, open in the game, both stores, nothing external", async () => {
		const w = world();
		const ana = await w.user("ana");
		await w.call("PUT", "/v1/social/me", { marketName: "Zé & D'Ávila" }, ana.token);
		const page = await w.call("GET", `/i/${ana.code}`, undefined, undefined, { "accept-language": "pt-BR,pt;q=0.9,en;q=0.8" });
		assert.equal(page.status, 200);
		assert.match(page.headers.get("content-type") ?? "", /^text\/html/);
		assert.match(page.headers.get("content-security-policy") ?? "", /default-src 'none'/);
		const html = page.text;
		assert.match(html, /<html lang="pt-BR">/);
		assert.ok(html.includes("Zé &amp; D&#39;Ávila"));
		assert.ok(!html.includes("Zé & D'Ávila"));
		assert.ok(html.includes("Copiar código"));
		assert.ok(html.includes(`href="checkout://add/${ana.code}"`));
		assert.ok(html.includes("Abrir no jogo"));
		assert.ok(html.includes(`https://play.google.com/store/apps/details?id=com.lucasfurini.checkout&amp;referrer=invite%3D${ana.code}`));
		assert.ok(html.includes("https://apps.apple.com/app/id6826304188"));
		assert.ok(html.includes(`${ana.code.slice(0, 4)}-${ana.code.slice(4)}`));
		assert.doesNotMatch(html, /<script[^>]+src=|<link[^>]+href=|<img|https?:\/\/(?!play\.google\.com|apps\.apple\.com)/);
		for (const [lang, word] of [["en-US", "Copy code"], ["es-MX", "Copiar código"], ["fr-FR", "Copier le code"], ["de-DE", "Code kopieren"], ["ja", "Copy code"]]) {
			const other = await w.call("GET", `/i/${ana.code}`, undefined, undefined, { "accept-language": lang });
			assert.ok(other.text.includes(word), lang);
		}
	});

	test("unknown code: the same page without the name; a malformed one: no code at all", async () => {
		const w = world();
		const unknown = (await w.call("GET", "/i/zzzz-zzzz", undefined, undefined, { "accept-language": "pt-BR" })).text;
		assert.ok(unknown.includes("Você foi convidado"));
		assert.ok(unknown.includes("checkout://add/ZZZZZZZZ"));
		assert.ok(unknown.includes("referrer=invite%3DZZZZZZZZ"));
		const malformed = (await w.call("GET", "/i/%3Cscript%3E", undefined, undefined, { "accept-language": "pt-BR" })).text;
		assert.ok(!malformed.includes("checkout://"));
		assert.ok(!malformed.includes("referrer="));
		assert.ok(!malformed.toLowerCase().includes("<script>alert"));
		assert.ok(malformed.includes("https://apps.apple.com/app/id6826304188"));
	});
});
