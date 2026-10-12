import assert from "node:assert/strict";
import { generateKeyPairSync, sign } from "node:crypto";
import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import { after, before, describe, test } from "node:test";
import { createApp } from "../src/app.ts";
import { readSave } from "../src/save.ts";
import { memoryStore } from "../src/store.ts";
import { googleVerifier, readSession, signSession } from "../src/tokens.ts";

const SECRET = "test-secret-test-secret-test-secret-123";
const save = (state: Record<string, unknown>, version = 45) => JSON.stringify({ state, version });
const game = (diamonds: number, coins = 200, level = 1) =>
	save({ coins, era: { id: "mesinha" }, market: { level }, logistics: { premiumCurrency: diamonds }, day: { dayNumber: 3 } });

describe("cloud save rules", () => {
	test("reads what the player sees about a save, refuses what is not one", () => {
		assert.deepEqual(readSave(game(120, 5000, 7)), { level: 7, era: "mesinha", coins: 5000, diamonds: 120, day: 3, version: 45 });
		for (const bad of ["", "{", "[]", JSON.stringify({ version: 1 }), JSON.stringify({ state: [] }), 42, null])
			assert.equal(readSave(bad), null, String(bad));
		assert.equal(readSave(save({ blob: "x".repeat(2 * 1024 * 1024) })), null);
	});
});

describe("session tokens", () => {
	test("sign, read, expire, tamper", () => {
		const token = signSession("player-1", SECRET, 0);
		assert.equal(readSession(token, SECRET, 1000)?.sub, "player-1");
		assert.equal(readSession(token, SECRET, 181 * 86400_000), null);
		assert.equal(readSession(token, "another-secret-another-secret-12345", 1000), null);
		const [h, p, s] = token.split(".");
		const forged = Buffer.from(JSON.stringify({ sub: "player-2", exp: 9e9 })).toString("base64url");
		assert.equal(readSession(`${h}.${forged}.${s}`, SECRET, 1000), null);
		assert.equal(readSession(`${h}.${p}`, SECRET, 1000), null);
	});
});

describe("Google ID tokens", () => {
	const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
	const jwk = { ...(publicKey.export({ format: "jwk" }) as object), kid: "k1", alg: "RS256" } as any;
	const now = 1_800_000_000_000;
	const make = (claims: Record<string, unknown>, kid = "k1") => {
		const header = Buffer.from(JSON.stringify({ alg: "RS256", kid })).toString("base64url");
		const payload = Buffer.from(JSON.stringify(claims)).toString("base64url");
		const signature = sign("RSA-SHA256", Buffer.from(`${header}.${payload}`), privateKey).toString("base64url");
		return `${header}.${payload}.${signature}`;
	};
	const good = { iss: "https://accounts.google.com", aud: "web-client", sub: "g-123", email: "a@b.c", exp: now / 1000 + 600 };
	let fetches = 0;
	const verify = googleVerifier(["web-client", "desktop-client"], async () => (fetches++, { keys: { keys: [jwk] }, maxAgeMs: 3600_000 }), () => now);

	test("accepts Google's token for the game's client", async () => {
		assert.deepEqual(await verify(make(good)), { sub: "g-123", email: "a@b.c", name: undefined });
		assert.equal((await verify(make({ ...good, aud: "desktop-client" })))?.sub, "g-123");
		assert.equal(fetches, 1, "keys are cached");
	});

	test("refuses other apps, other issuers, expired, unknown keys and forged signatures", async () => {
		assert.equal(await verify(make({ ...good, aud: "someone-else" })), null);
		assert.equal(await verify(make({ ...good, iss: "https://evil.example" })), null);
		assert.equal(await verify(make({ ...good, exp: now / 1000 - 3600 })), null);
		assert.equal(await verify(make(good, "unknown")), null);
		const [h, , s] = make(good).split(".");
		const other = Buffer.from(JSON.stringify({ ...good, sub: "g-999" })).toString("base64url");
		assert.equal(await verify(`${h}.${other}.${s}`), null);
		assert.equal(await verify("not.a.token"), null);
	});

	test("an unknown key id refetches Google's keys at most once a minute", async () => {
		const before = fetches;
		for (let i = 0; i < 5; i++) await verify(make(good, `forged-${i}`));
		assert.ok(fetches - before <= 1);
	});

	test("Google's keys out of reach is an error, not a refusal", async () => {
		const down = googleVerifier(["web-client"], async () => {
			throw new Error("offline");
		});
		await assert.rejects(down(make(good)));
	});
});

describe("the API", () => {
	const store = memoryStore(undefined, 60 * 60_000);
	const identities: Record<string, { sub: string; email: string; name: string }> = {
		"token-ana": { sub: "g-ana", email: "ana@example.com", name: "Ana" },
		"token-bia": { sub: "g-bia", email: "bia@example.com", name: "Bia" },
	};
	const server = createServer(
		createApp({
			store,
			verifyGoogle: async (t) => identities[t] ?? null,
			exchangeCode: async (code, verifier, uri) => (code === "code-ana" && verifier === "v" && uri.startsWith("http://127.0.0.1:") ? "token-ana" : null),
			sessionSecret: SECRET,
			rateLimit: 1000,
		}),
	);
	let base = "";
	before(() => new Promise<void>((done) => server.listen(0, () => ((base = `http://127.0.0.1:${(server.address() as AddressInfo).port}`), done()))));
	after(() => new Promise<void>((done) => server.close(() => done())));

	const call = async (method: string, path: string, body?: unknown, token?: string) => {
		const response = await fetch(base + path, {
			method,
			headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
			body: body === undefined ? undefined : JSON.stringify(body),
		});
		const text = await response.text();
		return { status: response.status, body: text ? JSON.parse(text) : null };
	};
	const signIn = async (idToken: string) => (await call("POST", "/v1/auth/google", { idToken })).body;

	test("health and unknown routes", async () => {
		assert.equal((await call("GET", "/health")).status, 200);
		assert.equal((await call("GET", "/nope")).status, 404);
	});

	test("login: Google refuses → 401; first login creates the player with no save", async () => {
		assert.equal((await call("POST", "/v1/auth/google", { idToken: "forged" })).status, 401);
		assert.equal((await call("POST", "/v1/auth/google", {})).status, 400);
		const first = await signIn("token-ana");
		assert.equal(first.player.email, "ana@example.com");
		assert.equal(first.save, null);
		assert.equal((await signIn("token-ana")).player.id, first.player.id, "same Google account, same player");
	});

	test("PC/Editor login trades the browser code on the server; only loopback redirects", async () => {
		const ok = await call("POST", "/v1/auth/google-code", { code: "code-ana", codeVerifier: "v", redirectUri: "http://127.0.0.1:51234/" });
		assert.equal(ok.status, 200);
		assert.equal(ok.body.player.email, "ana@example.com");
		assert.equal((await call("POST", "/v1/auth/google-code", { code: "stolen", codeVerifier: "v", redirectUri: "http://127.0.0.1:1/" })).status, 400);
		assert.equal((await call("POST", "/v1/auth/google-code", { code: "code-ana", codeVerifier: "v", redirectUri: "https://evil.example/" })).status, 400);
	});

	test("the save needs a session", async () => {
		assert.equal((await call("GET", "/v1/save")).status, 401);
		assert.equal((await call("GET", "/v1/save", undefined, "garbage")).status, 401);
	});

	test("phone A uploads, phone B logs in and gets it, then both keep syncing without losing anything", async () => {
		const { token } = await signIn("token-bia");
		assert.equal((await call("GET", "/v1/save", undefined, token)).status, 404);
		// Phone A: first upload.
		const a1 = await call("PUT", "/v1/save", { baseRevision: 0, data: game(50), deviceId: "phone-a" }, token);
		assert.equal(a1.status, 200);
		assert.equal(a1.body.revision, 1);
		assert.equal(a1.body.summary.diamonds, 50);
		// Phone B signs in: the login already tells it there is progress in the cloud.
		const b = await signIn("token-bia");
		assert.equal(b.save.revision, 1);
		assert.equal(b.save.summary.diamonds, 50);
		const download = await call("GET", "/v1/save", undefined, b.token);
		assert.equal(download.body.data, game(50));
		// Phone B plays and uploads on top of revision 1.
		assert.equal((await call("PUT", "/v1/save", { baseRevision: 1, data: game(70), deviceId: "phone-b" }, b.token)).body.revision, 2);
		// Phone A (still on revision 1) must not erase that: conflict with what the cloud has.
		const stale = await call("PUT", "/v1/save", { baseRevision: 1, data: game(55), deviceId: "phone-a" }, token);
		assert.equal(stale.status, 409);
		assert.equal(stale.body.current.revision, 2);
		assert.equal(stale.body.current.summary.diamonds, 70);
		assert.equal(stale.body.current.deviceId, "phone-b");
		// The player chooses phone A's progress over the revision 2 they were shown…
		// …but phone B uploaded again meanwhile: the choice must be asked again with the newer progress.
		assert.equal((await call("PUT", "/v1/save", { baseRevision: 2, data: game(90), deviceId: "phone-b" }, b.token)).body.revision, 3);
		const staleForce = await call("PUT", "/v1/save", { baseRevision: 2, data: game(55), deviceId: "phone-a", force: true }, token);
		assert.equal(staleForce.status, 409);
		assert.equal(staleForce.body.current.summary.diamonds, 90);
		// Shown revision 3, the player still picks phone A: it replaces it, and the replaced one is kept.
		const forced = await call("PUT", "/v1/save", { baseRevision: 3, data: game(55), deviceId: "phone-a", force: true }, token);
		assert.equal(forced.body.revision, 4);
		const player = (await signIn("token-bia")).player.id;
		assert.equal(store.history.get(player)?.[0].summary.diamonds, 90);
	});

	test("bad uploads are refused", async () => {
		const { token } = await signIn("token-ana");
		assert.equal((await call("PUT", "/v1/save", { baseRevision: 0, data: "not json", deviceId: "x" }, token)).status, 400);
		assert.equal((await call("PUT", "/v1/save", { baseRevision: 0, data: game(1) }, token)).status, 400);
		assert.equal((await call("PUT", "/v1/save", { data: game(1), deviceId: "x" }, token)).status, 400);
	});

	test("deleting the account erases the player and the save; the old session stops working", async () => {
		const { token } = await signIn("token-ana");
		await call("PUT", "/v1/save", { baseRevision: 0, data: game(9), deviceId: "x" }, token);
		assert.equal((await call("DELETE", "/v1/account", undefined, token)).status, 204);
		assert.equal((await call("GET", "/v1/save", undefined, token)).status, 401);
		const again = await signIn("token-ana");
		assert.equal(again.save, null, "a new login starts clean");
	});

	test("Google unreachable during login → 503", async () => {
		const down = createServer(createApp({ store, verifyGoogle: async () => { throw new Error("offline"); }, sessionSecret: SECRET, rateLimit: 1000 }));
		await new Promise<void>((done) => down.listen(0, () => done()));
		const response = await fetch(`http://127.0.0.1:${(down.address() as AddressInfo).port}/v1/auth/google`, { method: "POST", body: JSON.stringify({ idToken: "x" }) });
		await new Promise<void>((done) => down.close(() => done()));
		assert.equal(response.status, 503);
	});

	test("too many requests from one address slow down", async () => {
		const limited = createServer(createApp({ store, verifyGoogle: async () => null, sessionSecret: SECRET, rateLimit: 3 }));
		await new Promise<void>((done) => limited.listen(0, () => done()));
		const url = `http://127.0.0.1:${(limited.address() as AddressInfo).port}/health`;
		const codes = [];
		for (let i = 0; i < 5; i++) codes.push((await fetch(url)).status);
		await new Promise<void>((done) => limited.close(() => done()));
		assert.deepEqual(codes, [200, 200, 200, 429, 429]);
	});
});
