import { BadRequest, canReplace, MAX_SAVE_BYTES, readUpload, type SaveMeta } from "./save.ts";
import type { PlayerRecord, Store } from "./store.ts";
import { type AppleTokens, type AppleVerifier, type GoogleVerifier, readSession, sha256Hex, signSession } from "./tokens.ts";

/**
 * The game's API — the same routes, bodies and status codes as the Render server (server/src/app.ts), so the game
 * only needs the new address:
 * - POST /v1/auth/google  {idToken}                       → {token, player, save: summary | null}
 * - POST /v1/auth/google-code {code, codeVerifier, redirectUri, client?} → the same (PC/Editor; client "ios" = iPhone)
 * - POST /v1/auth/apple   {idToken, authorizationCode?, name?, nonce?} → the same (Sign in with Apple; nonce: the raw
 *   one-time value whose SHA-256 the phone gave Apple; when sent, the token's nonce claim must match it)
 * - GET  /v1/save                                          → {revision, updatedAt, summary, deviceId, data} | 404
 * - PUT  /v1/save         {baseRevision, data, deviceId, force?} → {revision, updatedAt, summary, deviceId}
 *                                                           | 409 {error:"conflict", current: {…} | null}
 * - DELETE /v1/account                                     → 204 (the player and every save, for good)
 * - GET  /health                                           → {ok, settings: which settings are present (names only)}
 * Everything under /v1 except the login needs `Authorization: Bearer <token>`.
 */
export type AppOptions = {
	store: Store;
	verifyGoogle: GoogleVerifier;
	exchangeCode?: ((code: string, codeVerifier: string, redirectUri: string) => Promise<string | null>) | null;
	exchangeIosCode?: ((code: string, codeVerifier: string, redirectUri: string) => Promise<string | null>) | null;
	verifyApple?: AppleVerifier | null;
	apple?: AppleTokens | null;
	sessionSecret: string;
	now?: () => number;
	/** Requests per minute per address (and per player), per Worker instance. */
	rateLimit?: number;
	log?: (line: string) => void;
	/** What GET /health tells besides ok. */
	health?: () => Record<string, unknown>;
	/** Extra routes (the temporary /admin/* ones). Answers null when the path is not theirs. */
	extra?: (request: Request, path: string, helpers: Helpers) => Promise<Response | null>;
};

/** What the extra routes reuse: the save routes for any player (the CPU benchmark). */
export type Helpers = {
	getSave(player: PlayerRecord, save: SaveMeta | null): Promise<Response>;
	putSave(request: Request, player: PlayerRecord, current: SaveMeta | null): Promise<Response>;
};

export class HttpError extends Error {
	status: number;
	body: Record<string, unknown>;
	constructor(status: number, body: Record<string, unknown>) {
		super(String(body.error));
		this.status = status;
		this.body = body;
	}
}

const HEADERS = { "content-type": "application/json", "cache-control": "no-store" };
export const json = (status: number, body: unknown) => new Response(body === null ? null : JSON.stringify(body), { status, headers: HEADERS });

export const describe = (save: SaveMeta) => ({
	revision: save.revision,
	updatedAt: new Date(save.updatedAt).toISOString(),
	summary: save.summary,
	deviceId: save.deviceId,
});

// The save travels as a JSON string (quotes escaped): room for twice its size; readUpload enforces the real limit.
const MAX_BODY = MAX_SAVE_BYTES * 2 + 64 * 1024;

async function readBytes(request: Request) {
	const declared = Number(request.headers.get("content-length") ?? "0");
	if (declared > MAX_BODY) throw new HttpError(413, { error: "too-large" });
	const bytes = await request.arrayBuffer();
	if (bytes.byteLength > MAX_BODY) throw new HttpError(413, { error: "too-large" });
	return new Uint8Array(bytes);
}

async function readJson(request: Request): Promise<Record<string, unknown>> {
	const text = new TextDecoder().decode(await readBytes(request));
	try {
		const body = JSON.parse(text || "{}");
		if (!body || typeof body !== "object" || Array.isArray(body)) throw new Error();
		return body;
	} catch {
		throw new HttpError(400, { error: "bad-json" });
	}
}

export function createApp(options: AppOptions) {
	const { store, verifyGoogle, sessionSecret } = options;
	const now = options.now ?? Date.now;
	const limit = options.rateLimit ?? 120;
	const log = options.log ?? (() => {});
	const hits = new Map<string, { windowStart: number; count: number }>();

	const allow = (key: string) => {
		const t = now();
		const entry = hits.get(key);
		if (!entry || t - entry.windowStart >= 60_000) {
			hits.set(key, { windowStart: t, count: 1 });
			if (hits.size > 50_000) for (const [k, v] of hits) if (t - v.windowStart >= 60_000) hits.delete(k);
			return true;
		}
		return ++entry.count <= limit;
	};

	/** The signed-in player and their save's description (one D1 round trip). */
	const playerOf = async (request: Request) => {
		const header = request.headers.get("authorization") ?? "";
		const session = await readSession(header.startsWith("Bearer ") ? header.slice(7) : undefined, sessionSecret, now());
		if (!session) throw new HttpError(401, { error: "signed-out" });
		if (!allow(`player:${session.sub}`)) throw new HttpError(429, { error: "slow-down" });
		const found = await store.getPlayer(session.sub);
		if (!found) throw new HttpError(401, { error: "signed-out" });
		return found;
	};

	// The answer to a login: the game's session, who the player is, and the summary of the cloud save.
	const welcome = async (player: PlayerRecord, save: SaveMeta | null) => {
		log(`sign-in ${player.id} (${player.provider})`);
		return {
			token: await signSession(player.id, sessionSecret, now()),
			player: { id: player.id, email: player.email, name: player.name, provider: player.provider },
			save: save ? describe(save) : null,
		};
	};

	const helpers: Helpers = {
		async getSave(player, known) {
			const found = known ? await store.readSave(player.id, known) : null;
			if (!found) throw new HttpError(404, { error: "no-save" });
			// {"revision":…,"deviceId":"…","data":<the stored string literal>} — the 2 MB literal is not re-encoded.
			const head = `${JSON.stringify(describe(found.save)).slice(0, -1)},"data":`;
			return new Response(new Blob([head, found.body, "}"]), { status: 200, headers: HEADERS });
		},
		async putSave(request, player, current) {
			let upload: ReturnType<typeof readUpload>;
			try {
				upload = readUpload(await readBytes(request));
			} catch (error) {
				if (error instanceof BadRequest) throw new HttpError(400, { error: error.code });
				throw error;
			}
			if (!canReplace(current, upload.baseRevision)) throw new HttpError(409, { error: "conflict", current: current ? describe(current) : null });
			const result = await store.replaceSave(player.id, current, { literal: upload.literal, summary: upload.summary, deviceId: upload.deviceId, keepReplaced: upload.force });
			if (!result.ok) throw new HttpError(409, { error: "conflict", current: result.current ? describe(result.current) : null });
			return json(200, describe(result.save));
		},
	};

	async function route(request: Request): Promise<Response> {
		const path = new URL(request.url).pathname;
		const method = request.method;
		if (path === "/health" || path === "/") return json(200, { ok: true, ...options.health?.() });

		if ((path === "/v1/auth/google" || path === "/v1/auth/google-code") && method === "POST") {
			const body = await readJson(request);
			let idToken = body.idToken;
			if (path === "/v1/auth/google-code") {
				const { code, codeVerifier, redirectUri } = body;
				const ios = body.client === "ios";
				const exchange = ios ? options.exchangeIosCode : options.exchangeCode;
				if (!exchange) throw new HttpError(404, { error: "not-configured" });
				// PC/Editor: a loopback address; iPhone: the iOS client's own scheme (com.googleusercontent.apps.<id>).
				const redirectOk = ios
					? /^com\.googleusercontent\.apps\.[\w-]+:\/oauth2redirect\/?$/.test(String(redirectUri))
					: /^http:\/\/127\.0\.0\.1:\d+\/?$/.test(String(redirectUri));
				if (typeof code !== "string" || typeof codeVerifier !== "string" || typeof redirectUri !== "string" || !redirectOk)
					throw new HttpError(400, { error: "bad-code" });
				idToken = await exchange(code, codeVerifier, redirectUri);
			}
			if (typeof idToken !== "string" || idToken.length > 8192) throw new HttpError(400, { error: "missing-token" });
			let identity: Awaited<ReturnType<GoogleVerifier>>;
			try {
				identity = await verifyGoogle(idToken);
			} catch {
				throw new HttpError(503, { error: "google-unavailable" });
			}
			if (!identity) {
				log(`login refused (${path})`);
				throw new HttpError(401, { error: "google-refused" });
			}
			const { player, save } = await store.signIn("google", identity.sub, identity.email ?? null, identity.name ?? null);
			return json(200, await welcome(player, save));
		}

		if (path === "/v1/auth/apple" && method === "POST") {
			if (!options.verifyApple) throw new HttpError(404, { error: "not-configured" });
			const body = await readJson(request);
			const { idToken, authorizationCode } = body;
			if (typeof idToken !== "string" || idToken.length > 8192) throw new HttpError(400, { error: "missing-token" });
			let identity: Awaited<ReturnType<AppleVerifier>>;
			try {
				identity = await options.verifyApple(idToken);
			} catch {
				throw new HttpError(503, { error: "apple-unavailable" });
			}
			if (!identity) {
				log("apple login refused");
				throw new HttpError(401, { error: "apple-refused" });
			}
			// The login's one-time nonce (newer builds): the token must carry its SHA-256, so a token caught on its way
			// cannot be replayed by another login. Older builds send none and still sign in.
			if (body.nonce !== undefined) {
				const nonce = body.nonce;
				const expected = typeof nonce === "string" && nonce && nonce.length <= 256 ? await sha256Hex(nonce) : null;
				if (!expected || identity.nonce !== expected) {
					log("apple login refused (nonce)");
					throw new HttpError(401, { error: "apple-refused" });
				}
			}
			// The phone sends the name the player shared (only on the very first login).
			const name = typeof body.name === "string" ? body.name.replace(/\s+/g, " ").trim().slice(0, 80) : "";
			const { player, save } = await store.signIn("apple", identity.sub, identity.email ?? null, name || null);
			// Keep Apple's refresh token, so deleting the account can revoke it. A failure here never blocks the login.
			if (options.apple && typeof authorizationCode === "string" && authorizationCode.length < 2048) {
				try {
					const refresh = await options.apple.exchange(authorizationCode);
					if (refresh) {
						await store.setAppleRefresh(player.id, refresh);
						player.appleRefresh = refresh;
					}
				} catch (error) {
					log(`apple code exchange failed: ${(error as Error)?.message ?? error}`);
				}
			}
			return json(200, await welcome(player, save));
		}

		if (path === "/v1/save" && method === "GET") {
			const { player, save } = await playerOf(request);
			return helpers.getSave(player, save);
		}

		if (path === "/v1/save" && method === "PUT") {
			const { player, save } = await playerOf(request);
			return helpers.putSave(request, player, save);
		}

		if (path === "/v1/account" && method === "DELETE") {
			const { player } = await playerOf(request);
			// Apple accounts: the game's access to the Apple ID ends too (App Store rule 5.1.1(v)). Best effort.
			if (player.appleRefresh && options.apple) {
				try {
					if (!(await options.apple.revoke(player.appleRefresh))) log(`apple revoke refused for ${player.id}`);
				} catch (error) {
					log(`apple revoke failed: ${(error as Error)?.message ?? error}`);
				}
			}
			await store.deletePlayer(player.id);
			log(`deleted ${player.id}`);
			return json(204, null);
		}

		const extra = options.extra ? await options.extra(request, path, helpers) : null;
		if (extra) return extra;
		throw new HttpError(404, { error: "not-found" });
	}

	/** `address`: the caller's IP (Cloudflare's CF-Connecting-IP). */
	return async (request: Request, address: string): Promise<Response> => {
		try {
			if (!allow(`ip:${address}`)) throw new HttpError(429, { error: "slow-down" });
			return await route(request);
		} catch (error) {
			if (error instanceof HttpError) return json(error.status, error.body);
			log(`error ${(error as Error)?.stack ?? error}`);
			return json(500, { error: "server" });
		}
	};
}
