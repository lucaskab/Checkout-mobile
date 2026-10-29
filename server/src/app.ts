import { createHash } from "node:crypto";
import type { IncomingMessage, ServerResponse } from "node:http";
import { canReplace, MAX_SAVE_BYTES, readSave, type SaveRecord } from "./save.ts";
import type { Store } from "./store.ts";
import type { PlayerRecord } from "./store.ts";
import { type AppleTokens, type AppleVerifier, type GoogleVerifier, readSession, signSession } from "./tokens.ts";

/**
 * The game's API (all JSON):
 * - POST /v1/auth/google  {idToken}                       → {token, player, save: summary | null}
 * - POST /v1/auth/google-code {code, codeVerifier, redirectUri, client?} → the same (PC/Editor: the browser login's
 *   code is exchanged here, so the game never carries the desktop client's secret; client "ios" = the iPhone's
 *   Google login, an iOS OAuth client with its own redirect scheme and no secret)
 * - POST /v1/auth/apple   {idToken, authorizationCode?, name?, nonce?} → the same (Sign in with Apple on the iPhone; the
 *   name comes from the phone, Apple sends it only on the first login; nonce: the raw one-time value whose SHA-256 the
 *   phone gave Apple; when sent, the token's nonce claim must match it. Builds before 29/10 send none.)
 * - GET  /v1/save                                          → {revision, updatedAt, summary, data} | 404
 * - PUT  /v1/save         {baseRevision, data, deviceId, force?} → {revision, updatedAt, summary}
 *                                                           | 409 {error:"conflict", current: {revision, updatedAt, summary, deviceId}}
 * - DELETE /v1/account                                     → 204 (the player and every save, for good)
 * - GET  /health                                           → {ok:true}
 * Everything under /v1 except the login needs `Authorization: Bearer <token>`.
 */
export type AppOptions = {
	store: Store;
	verifyGoogle: GoogleVerifier;
	/** PC/Editor login: trades the browser login's code for Google's ID token (null when not configured). */
	exchangeCode?: ((code: string, codeVerifier: string, redirectUri: string) => Promise<string | null>) | null;
	/** iPhone Google login: trades the code of the iOS OAuth client (null when not configured). */
	exchangeIosCode?: ((code: string, codeVerifier: string, redirectUri: string) => Promise<string | null>) | null;
	/** Sign in with Apple (null when not configured). */
	verifyApple?: AppleVerifier | null;
	/** Apple's token API: keeps a refresh token at login and revokes it when the account is deleted (optional). */
	apple?: AppleTokens | null;
	sessionSecret: string;
	now?: () => number;
	/** Requests per minute per address (and per player). */
	rateLimit?: number;
	log?: (line: string) => void;
};

class HttpError extends Error {
	status: number;
	body: Record<string, unknown>;
	constructor(status: number, body: Record<string, unknown>) {
		super(String(body.error));
		this.status = status;
		this.body = body;
	}
}

const describe = (save: SaveRecord) => ({
	revision: save.revision,
	updatedAt: save.updatedAt.toISOString(),
	summary: save.summary,
	deviceId: save.deviceId,
});

async function readJson(req: IncomingMessage): Promise<Record<string, unknown>> {
	const chunks: Buffer[] = [];
	let size = 0;
	for await (const chunk of req) {
		size += (chunk as Buffer).length;
		// The save travels as a JSON string (quotes escaped): room for twice its size; readSave enforces the real limit.
		if (size > MAX_SAVE_BYTES * 2 + 64 * 1024) throw new HttpError(413, { error: "too-large" });
		chunks.push(chunk as Buffer);
	}
	try {
		const body = JSON.parse(Buffer.concat(chunks).toString("utf8") || "{}");
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

	const playerOf = async (req: IncomingMessage) => {
		const header = req.headers.authorization ?? "";
		const session = readSession(header.startsWith("Bearer ") ? header.slice(7) : undefined, sessionSecret, now());
		if (!session) throw new HttpError(401, { error: "signed-out" });
		if (!allow(`player:${session.sub}`)) throw new HttpError(429, { error: "slow-down" });
		const player = await store.getPlayer(session.sub);
		if (!player) throw new HttpError(401, { error: "signed-out" });
		return player;
	};

	// The answer to a login: the game's session, who the player is, and the summary of the cloud save.
	const welcome = async (player: PlayerRecord) => {
		const save = await store.getSave(player.id);
		log(`sign-in ${player.id} (${player.provider})`);
		return {
			token: signSession(player.id, sessionSecret, now()),
			player: { id: player.id, email: player.email, name: player.name, provider: player.provider },
			save: save ? describe(save) : null,
		};
	};

	async function route(req: IncomingMessage) {
		const path = (req.url ?? "/").split("?")[0];
		const method = req.method ?? "GET";
		if (path === "/health" || path === "/") return { status: 200, body: { ok: true } };

		if ((path === "/v1/auth/google" || path === "/v1/auth/google-code") && method === "POST") {
			const body = await readJson(req);
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
			let identity;
			try {
				identity = await verifyGoogle(idToken);
			} catch {
				throw new HttpError(503, { error: "google-unavailable" });
			}
			if (!identity) {
				log(`login refused (${path})`);
				throw new HttpError(401, { error: "google-refused" });
			}
			return { status: 200, body: await welcome(await store.signIn("google", identity.sub, identity.email ?? null, identity.name ?? null)) };
		}

		if (path === "/v1/auth/apple" && method === "POST") {
			if (!options.verifyApple) throw new HttpError(404, { error: "not-configured" });
			const body = await readJson(req);
			const { idToken, authorizationCode } = body;
			if (typeof idToken !== "string" || idToken.length > 8192) throw new HttpError(400, { error: "missing-token" });
			let identity;
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
				const expected = typeof nonce === "string" && nonce && nonce.length <= 256 ? createHash("sha256").update(nonce).digest("hex") : null;
				if (!expected || identity.nonce !== expected) {
					log("apple login refused (nonce)");
					throw new HttpError(401, { error: "apple-refused" });
				}
			}
			// The phone sends the name the player shared (only on the very first login).
			const name = typeof body.name === "string" ? body.name.replace(/\s+/g, " ").trim().slice(0, 80) : "";
			const player = await store.signIn("apple", identity.sub, identity.email ?? null, name || null);
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
			return { status: 200, body: await welcome(player) };
		}

		if (path === "/v1/save" && method === "GET") {
			const player = await playerOf(req);
			const save = await store.getSave(player.id);
			if (!save) throw new HttpError(404, { error: "no-save" });
			return { status: 200, body: { ...describe(save), data: save.data } };
		}

		if (path === "/v1/save" && method === "PUT") {
			const player = await playerOf(req);
			const body = await readJson(req);
			const summary = readSave(body.data);
			if (!summary) throw new HttpError(400, { error: "not-a-save" });
			const baseRevision = typeof body.baseRevision === "number" && Number.isInteger(body.baseRevision) ? body.baseRevision : -1;
			const deviceId = typeof body.deviceId === "string" ? body.deviceId.slice(0, 100) : "";
			if (baseRevision < 0 || !deviceId) throw new HttpError(400, { error: "bad-upload" });
			const upload = { baseRevision, data: body.data as string, deviceId, force: body.force === true };
			const result = await store.replaceSave(player.id, { data: upload.data, summary, deviceId, keepReplaced: upload.force }, (current) =>
				canReplace(current, upload),
			);
			if (!result.ok)
				throw new HttpError(409, { error: "conflict", current: result.current ? describe(result.current) : null });
			return { status: 200, body: describe(result.save) };
		}

		if (path === "/v1/account" && method === "DELETE") {
			const player = await playerOf(req);
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
			return { status: 204, body: null };
		}

		throw new HttpError(404, { error: "not-found" });
	}

	return async (req: IncomingMessage, res: ServerResponse) => {
		let status = 500;
		let body: unknown = { error: "server" };
		try {
			// Render's proxy appends the real address last (anything before it was sent by the client).
			const address = (req.headers["x-forwarded-for"] as string | undefined)?.split(",").at(-1)?.trim() || req.socket.remoteAddress || "";
			if (!allow(`ip:${address}`)) throw new HttpError(429, { error: "slow-down" });
			({ status, body } = await route(req));
		} catch (error) {
			if (error instanceof HttpError) ({ status, body } = error);
			else log(`error ${(error as Error)?.stack ?? error}`);
		}
		res.writeHead(status, { "content-type": "application/json", "cache-control": "no-store" });
		res.end(body === null ? undefined : JSON.stringify(body));
	};
}
