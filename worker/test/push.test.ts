import assert from "node:assert/strict";
import { generateKeyPairSync } from "node:crypto";
import { describe, test } from "node:test";
import { createApp } from "../src/app.ts";
import { DAY_MS, dayOf } from "../src/limits.ts";
import { fcmSender, flushPush, type PushMessage, pushText, readServiceAccount } from "../src/push.ts";
import { Store } from "../src/store.ts";
import { fakeD1, fakeR2 } from "./fakes.ts";

// Push notifications (worker/src/push.ts): the device route, one push per player per flush from the new inbox rows
// (friend request, gift...), the categories of Opções › Avisos, tokens FCM forgot, account deletion, and the FCM call.
const SECRET = "test-secret-test-secret-test-secret-123";
const T0 = dayOf(1_800_000_000_000) * DAY_MS + 10 * 3600_000;
const save = (level: number) => JSON.stringify({ state: { coins: 100, era: { id: "tenda" }, market: { level }, logistics: { premiumCurrency: 1 }, day: { dayNumber: 2 } }, version: 45 });

function world(answer: (token: string) => "ok" | "gone" | "error" = () => "ok") {
	const clock = { now: T0 };
	const db = fakeD1();
	const sent: { token: string; message: PushMessage }[] = [];
	const store = new Store(db, fakeR2(), { clock: () => clock.now });
	const app = createApp({
		store,
		verifyGoogle: async (t) => (t.startsWith("token-") ? { sub: `g-${t.slice(6)}`, email: `${t.slice(6)}@example.com`, name: t.slice(6) } : null),
		sessionSecret: SECRET,
		rateLimit: 1_000_000,
		now: () => clock.now,
		push: async (token, message) => {
			sent.push({ token, message });
			return answer(token);
		},
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
	const login = async (name: string): Promise<User> => {
		const r = await call("POST", "/v1/auth/google", { idToken: `token-${name}` });
		assert.equal(r.status, 200);
		await call("PUT", "/v1/save", { baseRevision: 0, data: save(5), deviceId: "d" }, r.body.token);
		await call("PUT", "/v1/social/me", { marketName: `Mercado ${name}` }, r.body.token);
		const me = (await call("GET", "/v1/social/me", undefined, r.body.token)).body;
		return { token: r.body.token, id: r.body.player.id, code: me.code };
	};
	const device = (user: User, token: string, categories = ["amigos", "eventos"], lang = "pt", platform = "android") =>
		call("PUT", "/v1/push", { token, platform, lang, categories }, user.token);
	return { clock, db, store, call, login, device, sent };
}

describe("push: devices", () => {
	test("PUT /v1/push saves the device; bad bodies and no session are refused", async () => {
		const w = world();
		const ana = await w.login("ana");
		assert.equal((await w.call("PUT", "/v1/push", { token: "t1", platform: "android" })).status, 401);
		assert.equal((await w.call("PUT", "/v1/push", { token: "", platform: "android" }, ana.token)).status, 400);
		assert.equal((await w.call("PUT", "/v1/push", { token: "t1", platform: "web" }, ana.token)).status, 400);
		const ok = await w.device(ana, "t1", ["amigos", "nope"], "xx");
		assert.deepEqual(ok, { status: 200, body: { ok: true, categories: ["amigos"] } });
		const row = w.db.sqlite.prepare("SELECT player_id, platform, lang, categories FROM push_devices WHERE token = 't1'").get();
		assert.deepEqual({ ...row }, { player_id: ana.id, platform: "android", lang: "en", categories: "amigos" });
		assert.equal((await w.call("DELETE", "/v1/push", { token: "t1" }, ana.token)).status, 204);
		assert.equal(w.db.sqlite.prepare("SELECT COUNT(*) AS n FROM push_devices").get()?.n, 0);
	});

	test("a token that signs in on another account moves to it; a player keeps the 5 newest devices", async () => {
		const w = world();
		const ana = await w.login("ana");
		const bia = await w.login("bia");
		await w.device(ana, "shared");
		await w.device(bia, "shared");
		assert.equal(w.db.sqlite.prepare("SELECT player_id FROM push_devices WHERE token = 'shared'").get()?.player_id, bia.id);
		for (let i = 0; i < 7; i++) {
			w.clock.now += 1000;
			await w.device(ana, `ana-${i}`);
		}
		const tokens = w.db.sqlite.prepare("SELECT token FROM push_devices WHERE player_id = ? ORDER BY token").all(ana.id).map((r) => r.token);
		assert.deepEqual(tokens, ["ana-2", "ana-3", "ana-4", "ana-5", "ana-6"]);
	});

	test("deleting the account deletes its devices", async () => {
		const w = world();
		const ana = await w.login("ana");
		await w.device(ana, "t1");
		assert.equal((await w.call("DELETE", "/v1/account", undefined, ana.token)).status, 204);
		assert.equal(w.db.sqlite.prepare("SELECT COUNT(*) AS n FROM push_devices").get()?.n, 0);
	});
});

describe("push: from the inbox", () => {
	test("a friend request and a gift each push once, in the device's language, with the friend's market name", async () => {
		const w = world();
		const ana = await w.login("ana");
		const bia = await w.login("bia");
		await w.device(bia, "bia-phone", ["amigos"], "en");
		assert.equal((await w.call("POST", "/v1/social/friends/add", { code: bia.code }, ana.token)).status, 200);
		assert.deepEqual(w.sent, [{ token: "bia-phone", message: { title: "Friend request", body: "Mercado ana wants to be your friend on Checkout.", data: { kind: "friend_request" } } }]);
		assert.equal((await w.call("POST", "/v1/social/friends/accept", { id: ana.id }, bia.token)).status, 200);
		assert.equal(w.sent.length, 1, "ana has no device: accepting pushes nothing");
		assert.equal((await w.call("POST", "/v1/social/gift", { to: bia.id }, ana.token)).status, 204);
		assert.equal(w.sent.length, 2);
		assert.equal(w.sent[1].message.body, "Mercado ana sent you a gift. Come open it!");
		// Nothing new: a later social call pushes nothing again.
		await w.call("POST", "/v1/social/like", { to: ana.id }, bia.token);
		assert.equal(w.sent.length, 2);
	});

	test("the friends category off: no push; several new items: one push with the count", async () => {
		const w = world();
		const ana = await w.login("ana");
		const bia = await w.login("bia");
		const caio = await w.login("caio");
		await w.device(bia, "bia-phone", ["eventos"]);
		await w.call("POST", "/v1/social/friends/add", { code: bia.code }, ana.token);
		assert.equal(w.sent.length, 0);
		await w.device(bia, "bia-phone", ["amigos", "eventos"], "pt");
		// The earlier request was claimed already; two new ones land before the next flush.
		w.db.sqlite.prepare("INSERT INTO inbox (player_id, kind, from_id, payload, created_at) VALUES (?, 'gift', ?, '{}', ?), (?, 'like', ?, '{}', ?)").run(bia.id, caio.id, w.clock.now, bia.id, caio.id, w.clock.now);
		await flushPush(w.db, async (token, message) => (w.sent.push({ token, message }), "ok"), w.clock.now);
		assert.deepEqual(w.sent.map((s) => s.message.body), ["Você tem 2 novidades dos seus amigos no Checkout."]);
	});

	test("old or already read items are never pushed; a token FCM forgot is deleted", async () => {
		const w = world((token) => (token === "old-phone" ? "gone" : "ok"));
		const ana = await w.login("ana");
		const bia = await w.login("bia");
		await w.device(bia, "old-phone");
		w.db.sqlite.prepare("INSERT INTO inbox (player_id, kind, from_id, payload, created_at) VALUES (?, 'gift', ?, '{}', ?)").run(bia.id, ana.id, w.clock.now - 2 * 3600_000);
		w.db.sqlite.prepare("INSERT INTO inbox (player_id, kind, from_id, payload, created_at, acked_at) VALUES (?, 'gift', ?, '{}', ?, ?)").run(bia.id, ana.id, w.clock.now, w.clock.now);
		assert.equal(await flushPush(w.db, async () => "ok", w.clock.now), 0);
		await w.call("POST", "/v1/social/friends/add", { code: bia.code }, ana.token);
		assert.equal(w.sent.length, 1);
		assert.equal(w.db.sqlite.prepare("SELECT COUNT(*) AS n FROM push_devices").get()?.n, 0);
	});

	test("no FCM key: the social calls work as before", async () => {
		const w = world();
		const app = createApp({ store: w.store, verifyGoogle: async () => null, sessionSecret: SECRET, now: () => w.clock.now, push: null });
		assert.equal((await app(new Request("https://x/health"), "1.2.3.4")).status, 200);
		assert.equal(await flushPush(w.db, null, w.clock.now), 0);
	});
});

describe("push: texts", () => {
	test("one item names the friend (or not, when hidden); the league result has its own words", () => {
		assert.equal(pushText([{ kind: "help", name: "Mercado Bia" }], "es")?.body, "¡Mercado Bia ayudó a acelerar tu obra!");
		assert.equal(pushText([{ kind: "help", name: null }], "de")?.body, "Ein Freund hat deinen Bau beschleunigt!");
		assert.equal(pushText([{ kind: "league_reward", name: null }], "fr")?.title, "La ligue de la semaine est terminée");
		assert.equal(pushText([{ kind: "gift", name: "X" }, { kind: "gift", name: "Y" }], "pt")?.body, "Seus amigos te mandaram 2 presentes.");
		assert.equal(pushText([], "pt"), null);
	});
});

describe("push: FCM HTTP v1", () => {
	test("signs a JWT with the service account, keeps the access token, sends the message, reports gone tokens", async () => {
		const { privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
		const pem = privateKey.export({ type: "pkcs8", format: "pem" }).toString();
		const account = readServiceAccount(JSON.stringify({ type: "service_account", project_id: "checkout-game", client_email: "push@checkout-game.iam.gserviceaccount.com", private_key: pem }));
		assert.ok(account);
		assert.equal(readServiceAccount("{}"), null);
		assert.equal(readServiceAccount("not json"), null);
		const calls: { url: string; body: string; auth?: string }[] = [];
		const fetcher = (async (url: string, init: { body: string; headers: Record<string, string> }) => {
			calls.push({ url, body: init.body, auth: init.headers.authorization });
			if (url.includes("oauth2")) return new Response(JSON.stringify({ access_token: "ya29.test", expires_in: 3600 }));
			if (JSON.parse(init.body).message.token === "dead") return new Response('{"error":{"status":"NOT_FOUND","details":[{"errorCode":"UNREGISTERED"}]}}', { status: 404 });
			return new Response('{"name":"projects/checkout-game/messages/1"}');
		}) as unknown as typeof fetch;
		const send = fcmSender(account, fetcher, () => T0);
		assert.equal(await send("alive", { title: "Oi", body: "Tudo bem?", data: { kind: "gift" } }), "ok");
		assert.equal(await send("dead", { title: "Oi", body: "Tudo bem?" }), "gone");
		assert.equal(calls.filter((c) => c.url.includes("oauth2")).length, 1, "the access token is reused");
		const assertion = new URLSearchParams(calls[0].body).get("assertion") ?? "";
		const claims = JSON.parse(Buffer.from(assertion.split(".")[1], "base64url").toString());
		assert.equal(claims.iss, "push@checkout-game.iam.gserviceaccount.com");
		assert.equal(claims.scope, "https://www.googleapis.com/auth/firebase.messaging");
		const message = JSON.parse(calls[1].body).message;
		assert.equal(calls[1].url, "https://fcm.googleapis.com/v1/projects/checkout-game/messages:send");
		assert.equal(calls[1].auth, "Bearer ya29.test");
		assert.deepEqual(message.notification, { title: "Oi", body: "Tudo bem?" });
		assert.equal(message.android.notification.channel_id, "checkout");
	});
});
