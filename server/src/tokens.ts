import { createHmac, createPublicKey, sign as signData, timingSafeEqual, verify as verifySignature } from "node:crypto";

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
/** Apple's identity token carries no name (the phone sends it once, on the first login). `nonce`: the SHA-256 (hex)
 * of the login's one-time nonce, when the phone asked for one (builds from 29/10 on). */
export type AppleIdentity = { sub: string; email?: string; nonce?: string };
export type AppleVerifier = (idToken: string) => Promise<AppleIdentity | null>;
type Jwk = { kid: string; kty: string; n: string; e: string; alg?: string };
type KeySet = { keys: Jwk[] };
type Claims = Record<string, unknown>;

/**
 * An OpenID Connect ID token checker: RS256, signed by one of the issuer's public keys (cached), issued by it, for one
 * of the game's audiences, not expired. Returns the claims, or null when the token is not good.
 */
function idTokenChecker(
	issuers: string[],
	audiences: string[],
	fetchKeys: () => Promise<{ keys: KeySet; maxAgeMs: number }>,
	clock: () => number,
) {
	let cache: { keys: KeySet; until: number; fetchedAt: number } | null = null;
	// Keys rotate: an unknown key id fetches them again, but at most once a minute (forged ids must not turn every
	// request into a call to Google or Apple).
	const keysFor = async (kid: string) => {
		const now = clock();
		const known = cache?.keys.keys.some((k) => k.kid === kid);
		if (!cache || cache.until < now || (!known && now - cache.fetchedAt >= 60_000)) {
			const fresh = await fetchKeys();
			cache = { keys: fresh.keys, until: now + fresh.maxAgeMs, fetchedAt: now };
		}
		return cache.keys.keys.find((k) => k.kid === kid) ?? null;
	};
	return async (idToken: string): Promise<Claims | null> => {
		const parts = idToken.split(".");
		if (parts.length !== 3) return null;
		let header: { alg?: unknown; kid?: unknown };
		try {
			header = JSON.parse(fromB64url(parts[0]).toString("utf8"));
		} catch {
			return null;
		}
		if (header.alg !== "RS256" || typeof header.kid !== "string") return null;
		// The keys out of reach: an error (503), not "refused".
		const jwk = await keysFor(header.kid);
		if (!jwk) return null;
		try {
			const key = createPublicKey({ key: jwk as any, format: "jwk" });
			if (!verifySignature("RSA-SHA256", Buffer.from(`${parts[0]}.${parts[1]}`), key, fromB64url(parts[2]))) return null;
			const claims = JSON.parse(fromB64url(parts[1]).toString("utf8"));
			const now = clock() / 1000;
			const tokenAudiences = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
			if (!issuers.includes(claims.iss)) return null;
			if (!tokenAudiences.some((aud: unknown) => typeof aud === "string" && audiences.includes(aud))) return null;
			if (typeof claims.exp !== "number" || claims.exp + 60 < now) return null;
			if (typeof claims.sub !== "string" || !claims.sub) return null;
			return claims;
		} catch {
			return null;
		}
	};
}

const text = (value: unknown) => (typeof value === "string" ? value : undefined);

/**
 * Checks a "Sign in with Google" ID token: signed by Google, issued by Google, for one of the game's OAuth clients,
 * not expired. Only Google's stable account id (`sub`) identifies the player.
 */
export function googleVerifier(
	clientIds: string[],
	fetchKeys: () => Promise<{ keys: KeySet; maxAgeMs: number }> = fetchGoogleKeys,
	clock = () => Date.now(),
): GoogleVerifier {
	const check = idTokenChecker(["accounts.google.com", "https://accounts.google.com"], clientIds, fetchKeys, clock);
	return async (idToken) => {
		const claims = await check(idToken);
		return claims ? { sub: claims.sub as string, email: text(claims.email), name: text(claims.name) } : null;
	};
}

/**
 * Checks a "Sign in with Apple" identity token (Lucas 19/10, required on the App Store next to Google): signed by
 * Apple, issued by https://appleid.apple.com, for the game's bundle id, not expired. Apple's `sub` is the account id
 * (stable for this developer team); the e-mail may be Apple's private relay address, or missing.
 */
export function appleVerifier(
	bundleIds: string[],
	fetchKeys: () => Promise<{ keys: KeySet; maxAgeMs: number }> = fetchAppleKeys,
	clock = () => Date.now(),
): AppleVerifier {
	const check = idTokenChecker(["https://appleid.apple.com"], bundleIds, fetchKeys, clock);
	return async (idToken) => {
		const claims = await check(idToken);
		if (!claims) return null;
		const nonce = text(claims.nonce);
		return { sub: claims.sub as string, email: text(claims.email), ...(nonce ? { nonce } : {}) };
	};
}

async function fetchKeySet(url: string, defaultMaxAge: number) {
	const response = await fetch(url, { signal: AbortSignal.timeout(5000) });
	if (!response.ok) throw new Error(`${url}: HTTP ${response.status}`);
	const maxAge = /max-age=(\d+)/.exec(response.headers.get("cache-control") ?? "")?.[1];
	return { keys: (await response.json()) as KeySet, maxAgeMs: (maxAge ? Number(maxAge) : defaultMaxAge) * 1000 };
}
const fetchGoogleKeys = () => fetchKeySet("https://www.googleapis.com/oauth2/v3/certs", 3600);
const fetchAppleKeys = () => fetchKeySet("https://appleid.apple.com/auth/keys", 86400);

/**
 * Apple's token API for the game (optional: needs a "Sign in with Apple" key from the Apple Developer account):
 * the login's one-time code becomes a refresh token, which is revoked when the player deletes the account (App
 * Store rule 5.1.1(v)). The client secret is a short JWT signed with the key (ES256).
 */
export type AppleKeyConfig = { teamId: string; keyId: string; privateKey: string; clientId: string };
export type AppleTokens = { exchange(code: string): Promise<string | null>; revoke(refreshToken: string): Promise<boolean> };

export function appleClientSecret(config: AppleKeyConfig, now = Date.now()) {
	const header = b64url(JSON.stringify({ alg: "ES256", kid: config.keyId }));
	const iat = Math.floor(now / 1000);
	const payload = b64url(JSON.stringify({ iss: config.teamId, iat, exp: iat + 600, aud: "https://appleid.apple.com", sub: config.clientId }));
	const signature = signData("sha256", Buffer.from(`${header}.${payload}`), { key: config.privateKey, dsaEncoding: "ieee-p1363" });
	return `${header}.${payload}.${b64url(signature)}`;
}

export function appleTokens(config: AppleKeyConfig, post: typeof fetch = fetch, clock = () => Date.now()): AppleTokens {
	const form = (endpoint: "token" | "revoke", fields: Record<string, string>) =>
		post(`https://appleid.apple.com/auth/${endpoint}`, {
			signal: AbortSignal.timeout(10_000),
			method: "POST",
			headers: { "content-type": "application/x-www-form-urlencoded" },
			body: new URLSearchParams({ client_id: config.clientId, client_secret: appleClientSecret(config, clock()), ...fields }),
		});
	return {
		async exchange(code) {
			const response = await form("token", { code, grant_type: "authorization_code" });
			if (!response.ok) {
				console.log(new Date().toISOString(), `apple-code refused: ${response.status} ${(await response.text()).slice(0, 300)}`);
				return null;
			}
			const body = (await response.json()) as { refresh_token?: unknown };
			return typeof body.refresh_token === "string" ? body.refresh_token : null;
		},
		async revoke(refreshToken) {
			const response = await form("revoke", { token: refreshToken, token_type_hint: "refresh_token" });
			return response.ok;
		},
	};
}

/**
 * PC/Editor login (OAuth "installed app" with PKCE): Google's token endpoint trades the code for an ID token.
 * iPhone (iOS OAuth client, PKCE, no secret): the same with an empty secret.
 */
export function googleCodeExchange(clientId: string, clientSecret = "") {
	return async (code: string, codeVerifier: string, redirectUri: string) => {
		const response = await fetch("https://oauth2.googleapis.com/token", {
			signal: AbortSignal.timeout(10_000),
			method: "POST",
			headers: { "content-type": "application/x-www-form-urlencoded" },
			body: new URLSearchParams({ code, code_verifier: codeVerifier, redirect_uri: redirectUri, client_id: clientId, ...(clientSecret ? { client_secret: clientSecret } : {}), grant_type: "authorization_code" }),
		});
		if (!response.ok) {
			console.log(new Date().toISOString(), `google-code refused: ${response.status} ${(await response.text()).slice(0, 300)}`);
			return null;
		}
		const body = (await response.json()) as { id_token?: unknown };
		return typeof body.id_token === "string" ? body.id_token : null;
	};
}
