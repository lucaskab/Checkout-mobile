import { type Helpers, HttpError, json } from "./app.ts";
import type { Connect, D1Database, R2Bucket } from "./cf.ts";
import { copyHistory, copyPlayers, copySaves, type MigrateDeps, plan, verifyHistory, verifySaves } from "./migrate.ts";
import type { Store } from "./store.ts";
import { fromB64url } from "./tokens.ts";

/**
 * Temporary routes for the move from Render. They exist only while the ADMIN_PUBLIC_KEY setting does (a plain, public
 * value: an ECDSA P-256 public key, base64 SPKI — no secret is stored in Cloudflare), and answer only requests with the
 * header `x-admin-token: <expiry ms>.<signature>`, the signature (ES256, base64url) of "checkout-admin:<expiry ms>"
 * made with the matching private key, valid until that time (at most 2 hours ahead; scripts/admin-token.ts makes one).
 * Delete the setting afterwards and the routes are gone:
 * - GET  /admin/migrate/plan                         counts and sizes on both sides
 * - POST /admin/migrate/players                      step 1: every player
 * - POST /admin/migrate/saves?after=&limit=          step 2: current saves, a few players per call
 * - POST /admin/migrate/history?after=&limit=        step 3: restore points
 * - GET  /admin/migrate/verify-saves?after=&limit=   proof per player (revision, summary, md5 = R2 etag)
 * - GET  /admin/migrate/verify-history?after=&limit=
 * - GET|PUT /admin/bench/save, DELETE /admin/bench   the save routes for a test player "bench-cpu" (CPU measurements)
 * Answers carry counts and player ids only, never a save or a secret.
 */
export type AdminOptions = { publicKey: string; oldDatabaseUrl?: string; connect?: Connect; db: D1Database; bucket: R2Bucket; store: Store };

export const BENCH_PLAYER = "bench-cpu";
export const ADMIN_TOKEN_MAX_MS = 2 * 60 * 60_000;

const keys = new Map<string, Promise<CryptoKey>>();

/** Checks an admin token against the public key: well signed, not expired, not valid for more than 2 hours. */
export async function checkAdminToken(publicKey: string, token: string, now = Date.now()) {
	const [expiry, signature] = token.split(".");
	const until = Number(expiry);
	if (!signature || !Number.isSafeInteger(until) || until <= now || until - now > ADMIN_TOKEN_MAX_MS) return false;
	try {
		let imported = keys.get(publicKey);
		if (!imported) {
			imported = crypto.subtle.importKey("spki", Uint8Array.from(atob(publicKey.trim()), (c) => c.charCodeAt(0)), { name: "ECDSA", namedCurve: "P-256" }, false, ["verify"]);
			keys.set(publicKey, imported);
		}
		const key = await imported;
		return await crypto.subtle.verify({ name: "ECDSA", hash: "SHA-256" }, key, fromB64url(signature), new TextEncoder().encode(`checkout-admin:${expiry}`));
	} catch {
		return false;
	}
}

export function adminRoutes(options: AdminOptions) {
	return async (request: Request, path: string, helpers: Helpers): Promise<Response | null> => {
		if (!path.startsWith("/admin/")) return null;
		if (!(await checkAdminToken(options.publicKey, request.headers.get("x-admin-token") ?? ""))) throw new HttpError(404, { error: "not-found" });
		const url = new URL(request.url);
		const after = url.searchParams.get("after") ?? "";
		const limit = Math.max(1, Math.min(50, Number(url.searchParams.get("limit") ?? "1") || 1));
		const method = request.method;

		if (path === "/admin/bench/save" && (method === "GET" || method === "PUT")) {
			const now = Date.now();
			await options.db.prepare("INSERT OR IGNORE INTO players (id, created_at, last_seen) VALUES (?, ?, ?)").bind(BENCH_PLAYER, now, now).run();
			const found = await options.store.getPlayer(BENCH_PLAYER);
			if (!found) throw new HttpError(500, { error: "bench player" });
			return method === "GET" ? helpers.getSave(found.player, found.save) : helpers.putSave(request, found.player, found.save);
		}
		if (path === "/admin/bench" && method === "DELETE") {
			await options.store.deletePlayer(BENCH_PLAYER);
			return json(200, { deleted: BENCH_PLAYER });
		}

		if (path.startsWith("/admin/migrate/")) {
			if (!options.oldDatabaseUrl || !options.connect) throw new HttpError(404, { error: "OLD_DATABASE_URL not set" });
			const deps: MigrateDeps = { url: options.oldDatabaseUrl, connect: options.connect, db: options.db, bucket: options.bucket };
			try {
				if (path === "/admin/migrate/plan" && method === "GET") return json(200, await plan(deps));
				if (path === "/admin/migrate/players" && method === "POST") return json(200, await copyPlayers(deps));
				if (path === "/admin/migrate/saves" && method === "POST") return json(200, await copySaves(deps, after, limit));
				if (path === "/admin/migrate/history" && method === "POST") return json(200, await copyHistory(deps, after || "0", limit));
				if (path === "/admin/migrate/verify-saves" && method === "GET") return json(200, await verifySaves(deps, after, limit));
				if (path === "/admin/migrate/verify-history" && method === "GET") return json(200, await verifyHistory(deps, after || "0", limit));
			} catch (error) {
				// Postgres' and D1's messages carry no secrets (never the connection string).
				return json(500, { error: (error as Error)?.message ?? String(error) });
			}
		}
		return null;
	};
}
