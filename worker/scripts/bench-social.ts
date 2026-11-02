/**
 * Local estimate of the Worker's CPU time for the heaviest social routes (npm run bench:social). Runs the real app
 * (routes, store, answer building, session check) against the test stand-ins (D1 = node:sqlite, R2 = memory), and
 * subtracts the CPU spent inside SQLite: on Cloudflare the SQL runs in D1, not in the Worker, so what is left is
 * the Worker's share. Worst-case data: 50 friends with a full 4 KB public block and 2 open requests each, 100
 * unacked inbox items.
 */
import { createApp } from "../src/app.ts";
import type { D1Database, D1PreparedStatement } from "../src/cf.ts";
import { DAY_MS, dayOf, SOCIAL } from "../src/limits.ts";
import { cleanName, isNameAllowed } from "../src/names.ts";
import { readUpload } from "../src/save.ts";
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
function wrapStatement(s: D1PreparedStatement & { sql?: string; values?: unknown[] }): D1PreparedStatement {
	return { ...s, bind: (...v: unknown[]) => wrapStatement(s.bind(...v)), first: timed(s.first), all: timed(s.all), run: timed(s.run) } as D1PreparedStatement;
}
const raw = fakeD1();
const db: D1Database = { prepare: (sql) => wrapStatement(raw.prepare(sql)), batch: timed(raw.batch.bind(raw)) as D1Database["batch"] };

const now = dayOf(1_800_000_000_000) * DAY_MS + 10 * 3600_000;
const store = new Store(db, fakeR2(), { clock: () => now });
const secret = "bench-secret-bench-secret-bench-secret-1";
const app = createApp({
	store,
	verifyGoogle: async (t) => ({ sub: `g-${t}` }),
	sessionSecret: secret,
	rateLimit: 1e9,
	now: () => now,
});
const call = async (method: string, path: string, token: string, body?: string) => {
	const response = await app(
		new Request(`https://bench.example${path}`, { method, headers: { authorization: `Bearer ${token}`, "content-type": "application/json" }, body }),
		"1.1.1.1",
	);
	const text = await response.text();
	if (response.status >= 300) throw new Error(`${method} ${path}: ${response.status} ${text.slice(0, 200)}`);
	return text;
};
const signIn = async (name: string) => {
	const login = JSON.parse(await (await app(new Request("https://bench.example/v1/auth/google", { method: "POST", body: JSON.stringify({ idToken: name }) }), "1.1.1.1")).text());
	return { token: login.token as string, id: login.player.id as string };
};

// The world: "me" with 50 friends, each with a full public block (12 builds, padded to ~4 KB), a 14 KB save and
// 2 open requests; 100 inbox items for me; a request of mine to fulfil many times.
const me = await signIn("me");
await call("GET", "/v1/social/me", me.token);
const builds = Array.from({ length: SOCIAL.maxPublicBuilds }, (_, i) => ({ id: `interior:${i}:1793570000000`, kind: "interior", item: "shelf-produce", tier: 3, endsAt: now + 3600_000 }));
const pub = JSON.stringify({ builds, stage: "spati", marketRating: 4.2, pad: "" });
const padded = pub.replace('"pad":""', `"pad":"${"x".repeat(SOCIAL.maxPublicBytes - pub.length - 10)}"`);
const friends: { token: string; id: string }[] = [];
for (let i = 0; i < SOCIAL.maxFriends; i++) {
	const f = await signIn(`friend-${i}`);
	await call("GET", "/v1/social/me", f.token);
	const data = syntheticSave(14_000);
	await call("PUT", "/v1/save", f.token, `{"baseRevision":0,"data":${JSON.stringify(data)},"deviceId":"d","force":false,"public":${padded}}`);
	raw.sqlite.prepare("INSERT INTO friends VALUES (?, ?, ?), (?, ?, ?)").run(me.id, f.id, now, f.id, me.id, now);
	for (const product of ["milk", "bread"]) await call("POST", "/v1/social/requests", f.token, JSON.stringify({ productId: product, qty: 5 }));
	friends.push(f);
}
const insert = raw.sqlite.prepare("INSERT INTO inbox (player_id, kind, from_id, payload, created_at) VALUES (?, ?, ?, ?, ?)");
for (let i = 0; i < 100; i++) insert.run(me.id, i % 2 ? "help" : "delivery", friends[i % 50].id, JSON.stringify({ buildId: `interior:${i}`, minutes: 5, requestId: i, productId: "milk", qty: 3 }), now);

async function bench(label: string, runs: number, work: (i: number) => Promise<unknown>) {
	await work(0);
	sqliteUs = 0;
	const start = process.cpuUsage();
	for (let i = 1; i <= runs; i++) await work(i);
	const used = process.cpuUsage(start);
	const total = (used.user + used.system) / 1000 / runs;
	const sql = sqliteUs / 1000 / runs;
	console.log(`${label.padEnd(48)} Worker ≈ ${(total - sql).toFixed(2)} ms CPU  (with local SQLite ${total.toFixed(2)} ms)`);
}

console.log("Social routes, worst-case data (50 friends × 4 KB public block, 100 inbox items):");
await bench("GET /v1/social/friends (50 friends, 100 requests)", 50, () => call("GET", "/v1/social/friends", me.token));
await bench("GET /v1/social/inbox (100 items)", 50, () => call("GET", "/v1/social/inbox", me.token));
await bench("GET /v1/social/friends/{id}/market (14 KB save)", 50, (i) => call("GET", `/v1/social/friends/${friends[i % 50].id}/market`, me.token));
await bench("GET /v1/social/me", 50, () => call("GET", "/v1/social/me", me.token));
await bench("GET /v1/social/requests", 50, () => call("GET", "/v1/social/requests", me.token));
await bench("POST /v1/social/help (4 KB public block)", SOCIAL.maxHelpsGivenPerDay - 1, (i) => call("POST", "/v1/social/help", me.token, JSON.stringify({ to: friends[i].id, buildId: builds[0].id })));
await bench("POST /v1/social/like", 49, (i) => call("POST", "/v1/social/like", me.token, JSON.stringify({ to: friends[i].id })));
const open = (raw.sqlite.prepare("SELECT id FROM product_requests WHERE status = 'open' ORDER BY id").all() as { id: number }[]).map((r) => r.id);
await bench("POST /v1/social/requests/{id}/fulfill", 49, (i) => call("POST", `/v1/social/requests/${open[i]}/fulfill`, me.token));
await bench("PUT /v1/social/me (name check)", 50, (i) => call("PUT", "/v1/social/me", me.token, JSON.stringify({ marketName: `Mercado Bom ${i}` })));
const friendCode = JSON.parse(await call("GET", "/v1/social/me", friends[0].token)).code;
await bench("GET /i/<code> (landing page)", 50, () => call("GET", `/i/${friendCode}`, me.token));

// Pure functions, no storage at all.
const cpu = (work: () => void, runs: number) => {
	work();
	const start = process.cpuUsage();
	for (let i = 0; i < runs; i++) work();
	const used = process.cpuUsage(start);
	return (used.user + used.system) / 1000 / runs;
};
console.log(`isNameAllowed ≈ ${(cpu(() => isNameAllowed(cleanName("Supermercado do Zé 24h") as string), 2000) * 1000).toFixed(1)} µs`);
const encoder = new TextEncoder();
for (const size of [14_000, 50_000, 200_000]) {
	const data = syntheticSave(size);
	const plain = encoder.encode(`{"baseRevision":3,"data":${JSON.stringify(data)},"deviceId":"phone-a","force":false}`);
	const withPublic = encoder.encode(`{"baseRevision":3,"data":${JSON.stringify(data)},"deviceId":"phone-a","force":false,"public":${padded}}`);
	const a = cpu(() => readUpload(plain), 30);
	const b = cpu(() => readUpload(withPublic), 30);
	console.log(`readUpload ${(size / 1000).toFixed(0)} KB save: ${a.toFixed(2)} ms without public, ${b.toFixed(2)} ms with a 4 KB public block`);
}
