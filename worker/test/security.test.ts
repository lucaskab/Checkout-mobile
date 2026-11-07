import assert from "node:assert/strict";
import { describe, test } from "node:test";
import { createApp, type LimiterName, type RateLimiter } from "../src/app.ts";
import { DAY_MS, dayOf } from "../src/limits.ts";
import { Store } from "../src/store.ts";
import { fakeD1, fakeR2 } from "./fakes.ts";

// The security layer (07/11/2026): headers, body caps that also hold for chunked bodies, the Workers Rate Limiting
// bindings (and what happens when they fail), the least time between two uploads, a /health that tells nothing.
const SECRET = "test-secret-test-secret-test-secret-123";
const T0 = dayOf(1_800_000_000_000) * DAY_MS + 10 * 3600_000;
const save = (level: number) => JSON.stringify({ state: { coins: 100, era: { id: "tenda" }, market: { level }, logistics: { premiumCurrency: 1 }, day: { dayNumber: 2 } }, version: 45 });

/** A rate limiter that lets `limit` calls per key through, and records the keys it saw. */
function counter(limit: number) {
	const seen = new Map<string, number>();
	const limiter: RateLimiter & { seen: Map<string, number> } = {
		seen,
		async limit({ key }) {
			const n = (seen.get(key) ?? 0) + 1;
			seen.set(key, n);
			return { success: n <= limit };
		},
	};
	return limiter;
}

function world(options: { limiters?: Partial<Record<LimiterName, RateLimiter>>; minUploadGapMs?: number } = {}) {
	const clock = { now: T0 };
	const logs: string[] = [];
	const store = new Store(fakeD1(), fakeR2(), { clock: () => clock.now });
	const app = createApp({
		store,
		verifyGoogle: async (t) => (t.startsWith("token-") ? { sub: `g-${t.slice(6)}`, email: `${t.slice(6)}@example.com` } : null),
		sessionSecret: SECRET,
		rateLimit: 1_000_000,
		now: () => clock.now,
		log: (l) => logs.push(l),
		health: () => ({ configured: true }),
		...options,
	});
	const send = (method: string, path: string, init: { body?: BodyInit; token?: string; headers?: Record<string, string> } = {}, address = "1.2.3.4") =>
		app(
			new Request(`https://checkout-server.example${path}`, {
				method,
				headers: { "content-type": "application/json", ...(init.token ? { authorization: `Bearer ${init.token}` } : {}), ...init.headers },
				body: init.body,
				...(init.body instanceof ReadableStream ? { duplex: "half" } : {}),
			} as RequestInit),
			address,
		);
	const call = async (method: string, path: string, body?: unknown, token?: string, address?: string) => {
		const response = await send(method, path, { body: body === undefined ? undefined : typeof body === "string" ? body : JSON.stringify(body), token }, address);
		const text = await response.text();
		return { status: response.status, body: text ? JSON.parse(text) : null, headers: response.headers };
	};
	const signIn = async (name: string, address?: string) => (await call("POST", "/v1/auth/google", { idToken: `token-${name}` }, undefined, address)).body as { token: string; player: { id: string } };
	const upload = (token: string, baseRevision: number, level = 5) => call("PUT", "/v1/save", { baseRevision, data: save(level), deviceId: "phone" }, token);
	return { clock, logs, send, call, signIn, upload };
}

/** A body sent in pieces, with no Content-Length (what an attacker would use to skip the declared-size check). */
const chunked = (bytes: number, piece = 64 * 1024) => {
	let left = bytes;
	return new ReadableStream<Uint8Array>({
		pull(controller) {
			if (left <= 0) return controller.close();
			const n = Math.min(piece, left);
			left -= n;
			controller.enqueue(new Uint8Array(n).fill(0x20));
		},
	});
};

describe("security: answers", () => {
	test("every JSON answer carries nosniff, a CSP that runs nothing, no-referrer and HSTS; errors too", async () => {
		const w = world();
		for (const r of [await w.call("GET", "/health"), await w.call("GET", "/v1/save"), await w.call("GET", "/nope"), await w.call("GET", "/v1/rankings/world")]) {
			assert.equal(r.headers.get("x-content-type-options"), "nosniff");
			assert.match(r.headers.get("content-security-policy") ?? "", /default-src 'none'.*frame-ancestors 'none'/);
			assert.equal(r.headers.get("referrer-policy"), "no-referrer");
			assert.match(r.headers.get("strict-transport-security") ?? "", /max-age=\d+/);
			assert.equal(r.headers.get("access-control-allow-origin"), null, "no CORS: browsers on other sites cannot call the API");
		}
	});

	test("/health says ok and configured, nothing about which settings exist", async () => {
		const w = world();
		assert.deepEqual((await w.call("GET", "/health")).body, { ok: true, configured: true });
	});

	test("the invite page keeps its own CSP and gets HSTS", async () => {
		const w = world();
		const r = await w.send("GET", "/i/7KQ2M9XA");
		assert.match(r.headers.get("content-security-policy") ?? "", /default-src 'none'/);
		assert.match(r.headers.get("strict-transport-security") ?? "", /max-age=\d+/);
	});
});

describe("security: body caps", () => {
	test("logins and social calls refuse more than 16 KB, declared or chunked, without reading it all", async () => {
		const w = world();
		const big = JSON.stringify({ idToken: "x".repeat(20_000) });
		assert.equal((await w.call("POST", "/v1/auth/google", big)).status, 413);
		assert.equal((await w.send("POST", "/v1/auth/google", { body: chunked(20_000) })).status, 413);
		const { token } = await w.signIn("ana");
		assert.equal((await w.send("POST", "/v1/social/friends/add", { body: chunked(20_000), token })).status, 413);
		assert.equal((await w.send("PUT", "/v1/push", { body: chunked(20_000), token })).status, 413);
		// Small chunked bodies still work.
		const small = new TextEncoder().encode(JSON.stringify({ idToken: "token-bia" }));
		const ok = await w.send("POST", "/v1/auth/google", { body: new ReadableStream({ start: (c) => (c.enqueue(small), c.close()) }) });
		assert.equal(ok.status, 200);
	});

	test("a save upload refuses a chunked body past the save limit", async () => {
		const w = world();
		const { token } = await w.signIn("ana");
		assert.equal((await w.send("PUT", "/v1/save", { body: chunked(5 * 1024 * 1024), token })).status, 413);
	});
});

describe("security: Workers Rate Limiting bindings", () => {
	test("logins: per address; every request: per address; signed-in calls: per player; uploads: per player", async () => {
		const auth = counter(2);
		const w = world({ limiters: { auth } });
		assert.equal((await w.call("POST", "/v1/auth/google", { idToken: "token-ana" }, undefined, "9.9.9.9")).status, 200);
		assert.equal((await w.call("POST", "/v1/auth/google", { idToken: "token-ana" }, undefined, "9.9.9.9")).status, 200);
		assert.equal((await w.call("POST", "/v1/auth/google", { idToken: "token-ana" }, undefined, "9.9.9.9")).status, 429);
		assert.equal((await w.call("POST", "/v1/auth/google", { idToken: "token-ana" }, undefined, "8.8.8.8")).status, 200, "another address");

		const ip = counter(3);
		const w2 = world({ limiters: { ip } });
		for (let i = 0; i < 3; i++) assert.equal((await w2.call("GET", "/health", undefined, undefined, "5.5.5.5")).status, 200);
		assert.equal((await w2.call("GET", "/health", undefined, undefined, "5.5.5.5")).status, 429);

		const player = counter(2);
		const w3 = world({ limiters: { player } });
		const ana = await w3.signIn("ana");
		const bia = await w3.signIn("bia");
		assert.equal((await w3.call("GET", "/v1/social/me", undefined, ana.token)).status, 200);
		assert.equal((await w3.call("GET", "/v1/social/me", undefined, ana.token)).status, 200);
		assert.equal((await w3.call("GET", "/v1/social/me", undefined, ana.token)).status, 429);
		assert.equal((await w3.call("GET", "/v1/social/me", undefined, bia.token)).status, 200, "another player");
		assert.deepEqual([...player.seen.keys()].sort(), [ana.player.id, bia.player.id].sort(), "keyed by player id, not by the token");

		const savesLimit = counter(1);
		const w4 = world({ limiters: { save: savesLimit } });
		const cris = await w4.signIn("cris");
		assert.equal((await w4.upload(cris.token, 0)).status, 200);
		assert.equal((await w4.upload(cris.token, 1)).status, 429);
	});

	test("a limiter that fails lets the call through (players are never locked out by an outage) and says so in the log", async () => {
		const broken: RateLimiter = { limit: async () => Promise.reject(new Error("counters down")) };
		const w = world({ limiters: { ip: broken, auth: broken, player: broken, save: broken } });
		const { token } = await w.signIn("ana");
		assert.ok(token);
		assert.equal((await w.upload(token, 0)).status, 200);
		assert.ok(w.logs.some((l) => /rate limiter (ip|auth|player|save) failed: counters down/.test(l)));
	});
});

describe("security: least time between two uploads", () => {
	test("a second upload within 5 s is 429 (the game retries a minute later); after that it goes through; conflicts still win", async () => {
		const w = world({ minUploadGapMs: 5_000 });
		const { token } = await w.signIn("ana");
		assert.equal((await w.upload(token, 0)).status, 200, "the first upload has nothing to wait for");
		w.clock.now += 2_000;
		assert.equal((await w.upload(token, 1)).status, 429);
		assert.equal((await w.upload(token, 0)).status, 409, "a device that is behind gets its conflict right away");
		w.clock.now += 3_000;
		assert.equal((await w.upload(token, 1)).status, 200);
	});
});
