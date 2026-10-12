import type { IncomingMessage, ServerResponse } from "node:http";
import { canReplace, MAX_SAVE_BYTES, readSave, type SaveRecord } from "./save.ts";
import type { Store } from "./store.ts";
import { type GoogleVerifier, readSession, signSession } from "./tokens.ts";

/**
 * The game's API (all JSON):
 * - POST /v1/auth/google  {idToken}                       → {token, player, save: summary | null}
 * - POST /v1/auth/google-code {code, codeVerifier, redirectUri} → the same (PC/Editor: the browser login's code
 *   is exchanged here, so the game never carries the desktop client's secret)
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
		if (size > MAX_SAVE_BYTES + 64 * 1024) throw new HttpError(413, { error: "too-large" });
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

	async function route(req: IncomingMessage) {
		const path = (req.url ?? "/").split("?")[0];
		const method = req.method ?? "GET";
		if (path === "/health" || path === "/") return { status: 200, body: { ok: true } };

		if ((path === "/v1/auth/google" || path === "/v1/auth/google-code") && method === "POST") {
			const body = await readJson(req);
			let idToken = body.idToken;
			if (path === "/v1/auth/google-code") {
				const { code, codeVerifier, redirectUri } = body;
				if (!options.exchangeCode) throw new HttpError(404, { error: "not-configured" });
				if (typeof code !== "string" || typeof codeVerifier !== "string" || typeof redirectUri !== "string" || !/^http:\/\/127\.0\.0\.1:\d+\/?$/.test(redirectUri))
					throw new HttpError(400, { error: "bad-code" });
				idToken = await options.exchangeCode(code, codeVerifier, redirectUri);
			}
			if (typeof idToken !== "string" || idToken.length > 8192) throw new HttpError(400, { error: "missing-token" });
			const identity = await verifyGoogle(idToken);
			if (!identity) throw new HttpError(401, { error: "google-refused" });
			const player = await store.signIn(identity.sub, identity.email ?? null, identity.name ?? null);
			const save = await store.getSave(player.id);
			log(`sign-in ${player.id}`);
			return {
				status: 200,
				body: {
					token: signSession(player.id, sessionSecret, now()),
					player: { id: player.id, email: player.email, name: player.name },
					save: save ? describe(save) : null,
				},
			};
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
			const result = await store.replaceSave(player.id, { data: upload.data, summary, deviceId }, (current) => canReplace(current, upload));
			if (!result.ok)
				throw new HttpError(409, { error: "conflict", current: result.current ? describe(result.current) : null });
			return { status: 200, body: describe(result.save) };
		}

		if (path === "/v1/account" && method === "DELETE") {
			const player = await playerOf(req);
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
			const address = (req.headers["x-forwarded-for"] as string | undefined)?.split(",")[0].trim() || req.socket.remoteAddress || "";
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
