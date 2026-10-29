import assert from "node:assert/strict";
import { createHash, generateKeyPairSync, sign, verify as verifySig } from "node:crypto";
import { describe, test } from "node:test";
import { createApp } from "../src/app.ts";
import { readSave, readUpload as readUploadBytes } from "../src/save.ts";
import { Store } from "../src/store.ts";
import { appleClientSecret, appleTokens, appleVerifier, googleVerifier, readSession, signSession } from "../src/tokens.ts";
import { fakeD1, fakeR2 } from "./fakes.ts";

// The Render server's tests (server/test/api.test.ts), run against the Worker's code: same routes, same answers.
const SECRET = "test-secret-test-secret-test-secret-123";
// readUpload with text in, text literal out.
const readUpload = (body: string) => {
	const upload = readUploadBytes(new TextEncoder().encode(body));
	return { ...upload, literal: new TextDecoder().decode(upload.literal) };
};
const save = (state: Record<string, unknown>, version = 45) => JSON.stringify({ state, version });
const game = (diamonds: number, coins = 200, level = 1) =>
	save({ coins, era: { id: "mesinha" }, market: { level }, logistics: { premiumCurrency: diamonds }, day: { dayNumber: 3 } });

describe("cloud save rules", () => {
	test("reads what the player sees about a save, refuses what is not one", () => {
		assert.deepEqual(readSave(game(120, 5000, 7)), { level: 7, era: "mesinha", coins: 5000, diamonds: 120, day: 3, version: 45 });
		for (const bad of ["", "{", "[]", JSON.stringify({ version: 1 }), JSON.stringify({ state: [] }), 42, null])
			assert.equal(readSave(bad), null, String(bad));
		assert.equal(readSave(save({ blob: "x".repeat(2 * 1024 * 1024) })), null);
		// 2 MB in UTF-8, not in characters: "ã" is two bytes.
		assert.equal(readSave(save({ blob: "ã".repeat(1024 * 1024) })), null);
		assert.ok(readSave(save({ blob: "ã".repeat(1000 * 1000) })));
	});

	test("the game's upload: the save's literal is cut out of the body as is; other shapes take the general path", () => {
		const data = game(5);
		// Unity's JsonUtility.ToJson(new Upload{…}): fields in order, no spaces.
		const unity = `{"baseRevision":3,"data":${JSON.stringify(data)},"deviceId":"phone-a","force":false}`;
		const fast = readUpload(unity);
		assert.equal(fast.literal, JSON.stringify(data));
		assert.deepEqual([fast.baseRevision, fast.deviceId, fast.force, fast.summary.diamonds], [3, "phone-a", false, 5]);
		// Escapes the way another encoder writes them (\u, \/) are kept as sent: still the same save once parsed.
		const odd = `{"baseRevision":0,"data":"{\\"state\\":{\\"coins\\":1,\\"name\\":\\"\\u00e3\\/x\\"},\\"version\\":45}","deviceId":"d","force":true}`;
		const kept = readUpload(odd);
		assert.equal(JSON.parse(kept.literal), '{"state":{"coins":1,"name":"ã/x"},"version":45}');
		assert.equal(kept.force, true);
		// Other key order or spaces (any other client): same result through JSON.parse.
		const other = readUpload(JSON.stringify({ deviceId: "phone-b", data, baseRevision: 2 }, null, 1));
		assert.deepEqual([other.baseRevision, other.deviceId, other.force, JSON.parse(other.literal)], [2, "phone-b", false, data]);
		// A literal that is not one single string falls back to the general parse (which sees two "data" keys).
		const tricky = `{"baseRevision":1,"data":"x","data":${JSON.stringify(data)},"deviceId":"d","force":false}`;
		assert.equal(JSON.parse(readUpload(tricky).literal), data);
		for (const [body, code] of [
			["{", "bad-json"],
			["[1]", "bad-json"],
			[`{"baseRevision":0,"data":"nope","deviceId":"d","force":false}`, "not-a-save"],
			[`{"baseRevision":0,"data":${JSON.stringify(data)},"deviceId":"","force":false}`, "bad-upload"],
			[`{"baseRevision":-1,"data":${JSON.stringify(data)},"deviceId":"d","force":false}`, "bad-upload"],
		])
			assert.throws(() => readUpload(body), { code }, body);
	});
});

describe("session tokens", () => {
	test("sign, read, expire, tamper", async () => {
		const token = await signSession("player-1", SECRET, 0);
		assert.equal((await readSession(token, SECRET, 1000))?.sub, "player-1");
		assert.equal(await readSession(token, SECRET, 181 * 86400_000), null);
		assert.equal(await readSession(token, "another-secret-another-secret-12345", 1000), null);
		const [h, p, s] = token.split(".");
		const forged = Buffer.from(JSON.stringify({ sub: "player-2", exp: 9e9 })).toString("base64url");
		assert.equal(await readSession(`${h}.${forged}.${s}`, SECRET, 1000), null);
		assert.equal(await readSession(`${h}.${p}`, SECRET, 1000), null);
		assert.equal(await readSession(`${h}.${p}.!!`, SECRET, 1000), null);
	});

	test("byte for byte the Render server's token (players stay signed in after the move)", async () => {
		const { createHmac } = await import("node:crypto");
		const now = 1_761_000_000_000;
		const header = Buffer.from(JSON.stringify({ alg: "HS256", typ: "JWT" })).toString("base64url");
		const payload = Buffer.from(JSON.stringify({ sub: "4f1c-uuid", iat: now / 1000, exp: now / 1000 + 180 * 86400 })).toString("base64url");
		const render = `${header}.${payload}.${createHmac("sha256", SECRET).update(`${header}.${payload}`).digest("base64url")}`;
		assert.equal(await signSession("4f1c-uuid", SECRET, now), render);
		assert.equal((await readSession(render, SECRET, now + 1000))?.sub, "4f1c-uuid");
	});
});

describe("Google ID tokens", () => {
	const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
	// biome-ignore lint/suspicious/noExplicitAny: a JWK as Google publishes it
	const jwk = { ...(publicKey.export({ format: "jwk" }) as object), kid: "k1", alg: "RS256", use: "sig" } as any;
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

describe("Apple identity tokens", () => {
	const { privateKey, publicKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
	// biome-ignore lint/suspicious/noExplicitAny: a JWK as Apple publishes it
	const jwk = { ...(publicKey.export({ format: "jwk" }) as object), kid: "apple-1", alg: "RS256" } as any;
	const now = 1_800_000_000_000;
	const make = (claims: Record<string, unknown>) => {
		const header = Buffer.from(JSON.stringify({ alg: "RS256", kid: "apple-1" })).toString("base64url");
		const payload = Buffer.from(JSON.stringify(claims)).toString("base64url");
		return `${header}.${payload}.${sign("RSA-SHA256", Buffer.from(`${header}.${payload}`), privateKey).toString("base64url")}`;
	};
	const good = { iss: "https://appleid.apple.com", aud: "com.lucasfurini.checkout", sub: "001234.abcd", email: "x@privaterelay.appleid.com", exp: now / 1000 + 600 };
	const verify = appleVerifier(["com.lucasfurini.checkout", "com.lucasfurini.checkout.dev"], async () => ({ keys: { keys: [jwk] }, maxAgeMs: 3600_000 }), () => now);

	test("accepts Apple's token for the game's bundle ids", async () => {
		assert.deepEqual(await verify(make(good)), { sub: "001234.abcd", email: "x@privaterelay.appleid.com" });
		assert.equal((await verify(make({ ...good, aud: "com.lucasfurini.checkout.dev", email: undefined })))?.sub, "001234.abcd");
		// The login's nonce (SHA-256 hex), when the phone asked Apple for one.
		assert.equal((await verify(make({ ...good, nonce: "ab12" })))?.nonce, "ab12");
	});

	test("refuses Google's issuer, other apps and expired tokens", async () => {
		assert.equal(await verify(make({ ...good, iss: "https://accounts.google.com" })), null);
		assert.equal(await verify(make({ ...good, aud: "com.someone.else" })), null);
		assert.equal(await verify(make({ ...good, exp: now / 1000 - 3600 })), null);
	});

	test("the client secret for Apple's token API is an ES256 JWT signed with the team's key (the .p8 text)", async () => {
		const key = generateKeyPairSync("ec", { namedCurve: "P-256" });
		const pem = key.privateKey.export({ format: "pem", type: "pkcs8" }).toString();
		const secret = await appleClientSecret({ teamId: "TEAM123", keyId: "KEY456", privateKey: pem, clientId: "com.lucasfurini.checkout" }, now);
		const [h, p, s] = secret.split(".");
		assert.deepEqual(JSON.parse(Buffer.from(h, "base64url").toString()), { alg: "ES256", kid: "KEY456" });
		const claims = JSON.parse(Buffer.from(p, "base64url").toString());
		assert.equal(claims.iss, "TEAM123");
		assert.equal(claims.sub, "com.lucasfurini.checkout");
		assert.equal(claims.aud, "https://appleid.apple.com");
		assert.ok(verifySig("sha256", Buffer.from(`${h}.${p}`), { key: key.publicKey, dsaEncoding: "ieee-p1363" }, Buffer.from(s, "base64url")));
	});

	test("Apple's token API: the code becomes a refresh token; revoking posts the token", async () => {
		const key = generateKeyPairSync("ec", { namedCurve: "P-256" });
		const pem = key.privateKey.export({ format: "pem", type: "pkcs8" }).toString();
		const calls: { url: string; body: URLSearchParams }[] = [];
		const post = (async (url: string, init: { body: URLSearchParams }) => {
			calls.push({ url, body: init.body });
			return new Response(url.endsWith("/token") ? JSON.stringify({ refresh_token: "r-1" }) : "", { status: 200 });
		}) as unknown as typeof fetch;
		const apple = appleTokens({ teamId: "T", keyId: "K", privateKey: pem, clientId: "com.lucasfurini.checkout" }, post, () => now);
		assert.equal(await apple.exchange("code-1"), "r-1");
		assert.equal(await apple.revoke("r-1"), true);
		assert.equal(calls[0].url, "https://appleid.apple.com/auth/token");
		assert.equal(calls[0].body.get("grant_type"), "authorization_code");
		assert.equal(calls[1].url, "https://appleid.apple.com/auth/revoke");
		assert.equal(calls[1].body.get("token"), "r-1");
		assert.equal(calls[1].body.get("client_id"), "com.lucasfurini.checkout");
	});
});

describe("the API", () => {
	let clock = 1_800_000_000_000;
	const db = fakeD1();
	const bucket = fakeR2();
	const store = new Store(db, bucket, { clock: () => clock });
	const revoked: string[] = [];
	const identities: Record<string, { sub: string; email: string; name: string }> = {
		"token-ana": { sub: "g-ana", email: "ana@example.com", name: "Ana" },
		"token-bia": { sub: "g-bia", email: "bia@example.com", name: "Bia" },
	};
	const app = createApp({
		store,
		verifyGoogle: async (t) => identities[t] ?? null,
		exchangeCode: async (code, verifier, uri) => (code === "code-ana" && verifier === "v" && uri.startsWith("http://127.0.0.1:") ? "token-ana" : null),
		exchangeIosCode: async (code, verifier, uri) => (code === "ios-ana" && verifier === "v" && uri.endsWith(":/oauth2redirect") ? "token-ana" : null),
		verifyApple: async (t) =>
			t === "apple-cris"
				? { sub: "001.cris", email: "cris@privaterelay.appleid.com" }
				: t === "apple-dani"
					? { sub: "001.dani" }
					: t === "apple-eva"
						? { sub: "001.eva", nonce: createHash("sha256").update("raw-nonce-1").digest("hex") }
						: null,
		apple: {
			exchange: async (code) => (code === "auth-code" ? "refresh-cris" : null),
			revoke: async (token) => (revoked.push(token), true),
		},
		sessionSecret: SECRET,
		rateLimit: 1000,
		now: () => clock,
	});

	const call = async (method: string, path: string, body?: unknown, token?: string, handler = app) => {
		const response = await handler(
			new Request(`https://checkout-server.example${path}`, {
				method,
				headers: { "content-type": "application/json", ...(token ? { authorization: `Bearer ${token}` } : {}) },
				body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body),
			}),
			"1.2.3.4",
		);
		const text = await response.text();
		return { status: response.status, body: text ? JSON.parse(text) : null, text };
	};
	const signIn = async (idToken: string) => (await call("POST", "/v1/auth/google", { idToken })).body;
	// What the Unity game sends (JsonUtility: field order, no spaces).
	const unityUpload = (baseRevision: number, data: string, deviceId: string, force = false) =>
		`{"baseRevision":${baseRevision},"data":${JSON.stringify(data)},"deviceId":${JSON.stringify(deviceId)},"force":${force}}`;

	test("health and unknown routes", async () => {
		assert.equal((await call("GET", "/health")).status, 200);
		assert.equal((await call("GET", "/nope")).status, 404);
		assert.equal((await call("GET", "/admin/migrate/plan")).status, 404, "no admin routes without ADMIN_TOKEN");
	});

	test("login: Google refuses → 401; first login creates the player with no save", async () => {
		assert.equal((await call("POST", "/v1/auth/google", { idToken: "forged" })).status, 401);
		assert.equal((await call("POST", "/v1/auth/google", {})).status, 400);
		assert.equal((await call("POST", "/v1/auth/google", "{")).status, 400);
		const first = await signIn("token-ana");
		assert.equal(first.player.email, "ana@example.com");
		assert.equal(first.player.provider, "google");
		assert.equal(first.save, null);
		assert.match(first.player.id, /^[0-9a-f-]{36}$/);
		assert.equal((await signIn("token-ana")).player.id, first.player.id, "same Google account, same player");
	});

	test("PC/Editor login trades the browser code on the server; only loopback redirects", async () => {
		const ok = await call("POST", "/v1/auth/google-code", { code: "code-ana", codeVerifier: "v", redirectUri: "http://127.0.0.1:51234/" });
		assert.equal(ok.status, 200);
		assert.equal(ok.body.player.email, "ana@example.com");
		assert.equal((await call("POST", "/v1/auth/google-code", { code: "stolen", codeVerifier: "v", redirectUri: "http://127.0.0.1:1/" })).status, 400);
		assert.equal((await call("POST", "/v1/auth/google-code", { code: "code-ana", codeVerifier: "v", redirectUri: "https://evil.example/" })).status, 400);
	});

	test("iPhone Google login trades the iOS client's code; only its own scheme as the redirect", async () => {
		const ok = await call("POST", "/v1/auth/google-code", { client: "ios", code: "ios-ana", codeVerifier: "v", redirectUri: "com.googleusercontent.apps.123-abc:/oauth2redirect" });
		assert.equal(ok.status, 200);
		assert.equal(ok.body.player.provider, "google");
		assert.equal((await call("POST", "/v1/auth/google-code", { client: "ios", code: "ios-ana", codeVerifier: "v", redirectUri: "http://127.0.0.1:1/" })).status, 400);
	});

	test("Sign in with Apple: own account, the name from the first login, refresh token kept and revoked on delete", async () => {
		assert.equal((await call("POST", "/v1/auth/apple", { idToken: "forged" })).status, 401);
		assert.equal((await call("POST", "/v1/auth/apple", {})).status, 400);
		const first = (await call("POST", "/v1/auth/apple", { idToken: "apple-cris", authorizationCode: "auth-code", name: "  Cris   Souza " })).body;
		assert.equal(first.player.provider, "apple");
		assert.equal(first.player.name, "Cris Souza");
		assert.equal(first.player.email, "cris@privaterelay.appleid.com");
		const again = (await call("POST", "/v1/auth/apple", { idToken: "apple-cris" })).body;
		assert.equal(again.player.id, first.player.id);
		assert.equal(again.player.name, "Cris Souza", "Apple sends the name only once: the server keeps it");
		assert.equal(again.player.email, "cris@privaterelay.appleid.com");
		assert.notEqual((await signIn("token-ana")).player.id, first.player.id);
		// No e-mail shared, no name: still an account.
		assert.equal((await call("POST", "/v1/auth/apple", { idToken: "apple-dani" })).status, 200);
		assert.equal((await call("DELETE", "/v1/account", undefined, again.token)).status, 204);
		assert.deepEqual(revoked, ["refresh-cris"]);
	});

	test("Sign in with Apple: the nonce sent with the login must match the token's (older builds send none)", async () => {
		assert.equal((await call("POST", "/v1/auth/apple", { idToken: "apple-eva", nonce: "raw-nonce-1" })).status, 200);
		assert.equal((await call("POST", "/v1/auth/apple", { idToken: "apple-eva", nonce: "another-nonce" })).status, 401);
		assert.equal((await call("POST", "/v1/auth/apple", { idToken: "apple-eva", nonce: "" })).status, 401);
		assert.equal((await call("POST", "/v1/auth/apple", { idToken: "apple-dani", nonce: "raw-nonce-1" })).status, 401, "a token without a nonce");
		assert.equal((await call("POST", "/v1/auth/apple", { idToken: "apple-eva" })).status, 200, "builds before 29/10 send no nonce");
	});

	test("Sign in with Apple not configured → 404", async () => {
		const plain = createApp({ store, verifyGoogle: async () => null, sessionSecret: SECRET, rateLimit: 1000 });
		assert.equal((await call("POST", "/v1/auth/apple", { idToken: "x" }, undefined, plain)).status, 404);
	});

	test("the save needs a session", async () => {
		assert.equal((await call("GET", "/v1/save")).status, 401);
		assert.equal((await call("GET", "/v1/save", undefined, "garbage")).status, 401);
		assert.equal((await call("PUT", "/v1/save", unityUpload(0, game(1), "x"), await signSession("no-such-player", SECRET, clock))).status, 401);
	});

	test("phone A uploads, phone B logs in and gets it, then both keep syncing without losing anything", async () => {
		const { token } = await signIn("token-bia");
		assert.equal((await call("GET", "/v1/save", undefined, token)).status, 404);
		// Phone A: first upload.
		const a1 = await call("PUT", "/v1/save", unityUpload(0, game(50), "phone-a"), token);
		assert.equal(a1.status, 200);
		assert.equal(a1.body.revision, 1);
		assert.equal(a1.body.summary.diamonds, 50);
		assert.equal(a1.body.deviceId, "phone-a");
		assert.equal(a1.body.updatedAt, new Date(clock).toISOString());
		// Phone B signs in: the login already tells it there is progress in the cloud.
		const b = await signIn("token-bia");
		assert.equal(b.save.revision, 1);
		assert.equal(b.save.summary.diamonds, 50);
		const download = await call("GET", "/v1/save", undefined, b.token);
		assert.equal(download.body.data, game(50));
		assert.deepEqual(Object.keys(download.body), ["revision", "updatedAt", "summary", "deviceId", "data"]);
		// Phone B plays and uploads on top of revision 1.
		assert.equal((await call("PUT", "/v1/save", { baseRevision: 1, data: game(70), deviceId: "phone-b" }, b.token)).body.revision, 2);
		// Phone A (still on revision 1) must not erase that: conflict with what the cloud has.
		const stale = await call("PUT", "/v1/save", unityUpload(1, game(55), "phone-a"), token);
		assert.equal(stale.status, 409);
		assert.equal(stale.body.error, "conflict");
		assert.equal(stale.body.current.revision, 2);
		assert.equal(stale.body.current.summary.diamonds, 70);
		assert.equal(stale.body.current.deviceId, "phone-b");
		// The player chooses phone A's progress over the revision 2 they were shown…
		// …but phone B uploaded again meanwhile: the choice must be asked again with the newer progress.
		assert.equal((await call("PUT", "/v1/save", unityUpload(2, game(90), "phone-b"), b.token)).body.revision, 3);
		const staleForce = await call("PUT", "/v1/save", unityUpload(2, game(55), "phone-a", true), token);
		assert.equal(staleForce.status, 409);
		assert.equal(staleForce.body.current.summary.diamonds, 90);
		// Shown revision 3, the player still picks phone A: it replaces it, and the replaced one is kept.
		const forced = await call("PUT", "/v1/save", unityUpload(3, game(55), "phone-a", true), token);
		assert.equal(forced.body.revision, 4);
		const player = (await signIn("token-bia")).player.id;
		const history = db.sqlite.prepare("SELECT * FROM save_history WHERE player_id = ? ORDER BY id DESC").all(player) as Record<string, unknown>[];
		assert.equal(history.length, 1);
		assert.equal(JSON.parse(String(history[0].summary)).diamonds, 90);
		assert.equal(JSON.parse(new TextDecoder().decode(bucket.objects.get(String(history[0].body_key)))), game(90), "the restore point is the replaced save itself");
		assert.equal((await call("GET", "/v1/save", undefined, token)).body.data, game(55));
		// Only the current save and the restore point are left in R2 (replaced near-copies are deleted).
		assert.equal([...bucket.objects.keys()].filter((k) => k.startsWith(`saves/${player}/`)).length, 2);
	});

	test("an hour later the replaced save becomes a restore point; only the newest 10 are kept", async () => {
		const { token, player } = await signIn("token-bia");
		let revision = (await call("GET", "/v1/save", undefined, token)).body.revision;
		for (let i = 0; i < 12; i++) {
			clock += 61 * 60_000;
			const r = await call("PUT", "/v1/save", unityUpload(revision, game(100 + i), "phone-a"), token);
			assert.equal(r.status, 200);
			revision = r.body.revision;
		}
		const rows = db.sqlite.prepare("SELECT body_key FROM save_history WHERE player_id = ?").all(player.id) as { body_key: string }[];
		assert.equal(rows.length, 10);
		const keys = [...bucket.objects.keys()].filter((k) => k.startsWith(`saves/${player.id}/`));
		assert.equal(keys.length, 11, "10 restore points + the current save, nothing orphaned");
		for (const row of rows) assert.ok(bucket.objects.has(row.body_key));
	});

	test("two phones uploading on the same revision at the same moment: one wins, the other gets the conflict", async () => {
		const { token, player } = await signIn("token-bia");
		const revision = (await call("GET", "/v1/save", undefined, token)).body.revision;
		const [x, y] = await Promise.all([
			call("PUT", "/v1/save", unityUpload(revision, game(1), "phone-x"), token),
			call("PUT", "/v1/save", unityUpload(revision, game(2), "phone-y"), token),
		]);
		assert.deepEqual([x.status, y.status].sort(), [200, 409]);
		const winner = x.status === 200 ? x : y;
		const loser = x.status === 200 ? y : x;
		assert.equal(loser.body.current.deviceId, winner.body.deviceId);
		const keys = [...bucket.objects.keys()].filter((k) => k.startsWith(`saves/${player.id}/`));
		assert.equal(keys.length, 11, "the losing upload left nothing behind");
	});

	test("a download racing an upload still gets a whole save", async () => {
		const { token } = await signIn("token-bia");
		const known = await store.getPlayer((await signIn("token-bia")).player.id);
		const revision = known?.save?.revision as number;
		await call("PUT", "/v1/save", unityUpload(revision, game(321), "phone-a"), token);
		// The description read before the upload points at an object that is gone now: readSave follows the new one.
		const found = await store.readSave(known?.player.id as string, known?.save ?? null);
		assert.equal(found?.save.revision, revision + 1);
		assert.equal(JSON.parse(new TextDecoder().decode(found?.body)), game(321));
	});

	test("bad uploads are refused", async () => {
		const { token } = await signIn("token-ana");
		assert.equal((await call("PUT", "/v1/save", { baseRevision: 0, data: "not json", deviceId: "x" }, token)).status, 400);
		assert.equal((await call("PUT", "/v1/save", { baseRevision: 0, data: game(1) }, token)).status, 400);
		assert.equal((await call("PUT", "/v1/save", { data: game(1), deviceId: "x" }, token)).status, 400);
		assert.equal((await call("PUT", "/v1/save", "x".repeat(4 * 1024 * 1024 + 70 * 1024), token)).status, 413);
	});

	test("big saves: 2 MB goes through and comes back identical; more is refused", async () => {
		const { token } = await signIn("token-ana");
		// ~1.9 MB in UTF-8 with accents, quotes, backslashes and line breaks (escaped twice on the way).
		const big = save({ blob: `${"abcdefghij".repeat(9)}çã"\\\n`.repeat(18_000) });
		assert.ok(new TextEncoder().encode(big).length > 1_800_000);
		const put = await call("PUT", "/v1/save", unityUpload(0, big, "pc"), token);
		assert.equal(put.status, 200);
		assert.equal((await call("GET", "/v1/save", undefined, token)).body.data, big);
		assert.equal((await call("PUT", "/v1/save", unityUpload(1, save({ blob: "x".repeat(2 * 1024 * 1024) }), "pc"), token)).status, 400);
	});

	test("deleting the account erases the player and the save; the old session stops working", async () => {
		const { token, player } = await signIn("token-ana");
		await call("PUT", "/v1/save", unityUpload(1, game(9), "x"), token);
		assert.equal((await call("DELETE", "/v1/account", undefined, token)).status, 204);
		assert.equal((await call("GET", "/v1/save", undefined, token)).status, 401);
		assert.equal([...bucket.objects.keys()].filter((k) => k.startsWith(`saves/${player.id}/`)).length, 0, "nothing left in R2");
		const again = await signIn("token-ana");
		assert.equal(again.save, null, "a new login starts clean");
	});

	test("Google unreachable during login → 503", async () => {
		const down = createApp({ store, verifyGoogle: async () => Promise.reject(new Error("offline")), sessionSecret: SECRET, rateLimit: 1000 });
		assert.equal((await call("POST", "/v1/auth/google", { idToken: "x" }, undefined, down)).status, 503);
	});

	test("too many requests from one address slow down", async () => {
		const limited = createApp({ store, verifyGoogle: async () => null, sessionSecret: SECRET, rateLimit: 3 });
		const codes = [];
		for (let i = 0; i < 5; i++) codes.push((await call("GET", "/health", undefined, undefined, limited)).status);
		assert.deepEqual(codes, [200, 200, 200, 429, 429]);
	});
});
