import { createHmac, createPublicKey, timingSafeEqual, verify as verifySignature } from "node:crypto";

const b64url = (data: Buffer | string) => Buffer.from(data).toString("base64url");
const fromB64url = (text: string) => Buffer.from(text, "base64url");

/** The game's own session token (HMAC-signed, like a JWT): which player, until when. */
export type Session = { sub: string; exp: number };
export const SESSION_DAYS = 180;

export function signSession(playerId: string, secret: string, now = Date.now()) {
	const header = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
	const payload = b64url(JSON.stringify({ sub: playerId, iat: Math.floor(now / 1000), exp: Math.floor(now / 1000) + SESSION_DAYS * 86400 }));
	const signature = b64url(createHmac("sha256", secret).update(`${header}.${payload}`).digest());
	return `${header}.${payload}.${signature}`;
}

export function readSession(token: string | undefined, secret: string, now = Date.now()): Session | null {
	if (!token) return null;
	const parts = token.split(".");
	if (parts.length !== 3) return null;
	const expected = createHmac("sha256", secret).update(`${parts[0]}.${parts[1]}`).digest();
	const given = fromB64url(parts[2]);
	if (given.length !== expected.length || !timingSafeEqual(given, expected)) return null;
	try {
		const payload = JSON.parse(fromB64url(parts[1]).toString("utf8"));
		if (typeof payload.sub !== "string" || typeof payload.exp !== "number" || payload.exp * 1000 <= now) return null;
		return { sub: payload.sub, exp: payload.exp };
	} catch {
		return null;
	}
}

export type GoogleIdentity = { sub: string; email?: string; name?: string };
export type GoogleVerifier = (idToken: string) => Promise<GoogleIdentity | null>;
type Jwk = { kid: string; kty: string; n: string; e: string; alg?: string };
type KeySet = { keys: Jwk[] };

/**
 * Checks a "Sign in with Google" ID token: signed by Google (its public keys, cached), issued by Google, for
 * one of the game's OAuth clients, not expired. Only Google's stable account id (`sub`) identifies the player.
 */
export function googleVerifier(
	clientIds: string[],
	fetchKeys: () => Promise<{ keys: KeySet; maxAgeMs: number }> = fetchGoogleKeys,
	clock = () => Date.now(),
): GoogleVerifier {
	let cache: { keys: KeySet; until: number; fetchedAt: number } | null = null;
	// Google rotates keys: an unknown key id fetches them again, but at most once a minute (forged ids must not
	// turn every request into a call to Google).
	const keysFor = async (kid: string) => {
		const now = clock();
		const known = cache?.keys.keys.some((k) => k.kid === kid);
		if (!cache || cache.until < now || (!known && now - cache.fetchedAt >= 60_000)) {
			const fresh = await fetchKeys();
			cache = { keys: fresh.keys, until: now + fresh.maxAgeMs, fetchedAt: now };
		}
		return cache.keys.keys.find((k) => k.kid === kid) ?? null;
	};
	return async (idToken) => {
		const parts = idToken.split(".");
		if (parts.length !== 3) return null;
		let header: { alg?: unknown; kid?: unknown };
		try {
			header = JSON.parse(fromB64url(parts[0]).toString("utf8"));
		} catch {
			return null;
		}
		if (header.alg !== "RS256" || typeof header.kid !== "string") return null;
		// Google's keys out of reach: an error (503), not "Google refused".
		const jwk = await keysFor(header.kid);
		if (!jwk) return null;
		try {
			const key = createPublicKey({ key: jwk as any, format: "jwk" });
			if (!verifySignature("RSA-SHA256", Buffer.from(`${parts[0]}.${parts[1]}`), key, fromB64url(parts[2]))) return null;
			const claims = JSON.parse(fromB64url(parts[1]).toString("utf8"));
			const now = clock() / 1000;
			const audiences = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
			if (claims.iss !== "accounts.google.com" && claims.iss !== "https://accounts.google.com") return null;
			if (!audiences.some((aud: unknown) => typeof aud === "string" && clientIds.includes(aud))) return null;
			if (typeof claims.exp !== "number" || claims.exp + 60 < now) return null;
			if (typeof claims.sub !== "string" || !claims.sub) return null;
			return {
				sub: claims.sub,
				email: typeof claims.email === "string" ? claims.email : undefined,
				name: typeof claims.name === "string" ? claims.name : undefined,
			};
		} catch {
			return null;
		}
	};
}

async function fetchGoogleKeys() {
	const response = await fetch("https://www.googleapis.com/oauth2/v3/certs", { signal: AbortSignal.timeout(5000) });
	if (!response.ok) throw new Error(`Google keys: HTTP ${response.status}`);
	const maxAge = /max-age=(\d+)/.exec(response.headers.get("cache-control") ?? "")?.[1];
	return { keys: (await response.json()) as KeySet, maxAgeMs: (maxAge ? Number(maxAge) : 3600) * 1000 };
}

/** PC/Editor login (OAuth "installed app" with PKCE): Google's token endpoint trades the code for an ID token. */
export function googleCodeExchange(clientId: string, clientSecret: string) {
	return async (code: string, codeVerifier: string, redirectUri: string) => {
		const response = await fetch("https://oauth2.googleapis.com/token", {
			signal: AbortSignal.timeout(10_000),
			method: "POST",
			headers: { "content-type": "application/x-www-form-urlencoded" },
			body: new URLSearchParams({ code, code_verifier: codeVerifier, redirect_uri: redirectUri, client_id: clientId, client_secret: clientSecret, grant_type: "authorization_code" }),
		});
		if (!response.ok) return null;
		const body = (await response.json()) as { id_token?: unknown };
		return typeof body.id_token === "string" ? body.id_token : null;
	};
}
