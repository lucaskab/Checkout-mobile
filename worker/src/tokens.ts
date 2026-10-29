/**
 * Sessions, Google and Apple sign-in — the same tokens and checks as server/src/tokens.ts (Render), written with
 * WebCrypto (crypto.subtle), which Cloudflare Workers and Node both have. The session token format and secret are
 * the Render server's, so players stay signed in when the game moves to this Worker.
 */
const encoder = new TextEncoder();
const decoder = new TextDecoder();

export function b64url(data: Uint8Array | ArrayBuffer | string) {
	const bytes = typeof data === "string" ? encoder.encode(data) : data instanceof Uint8Array ? data : new Uint8Array(data);
	let binary = "";
	for (let i = 0; i < bytes.length; i += 0x8000) binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
	return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function fromB64url(text: string): Uint8Array<ArrayBuffer> {
	const base64 = text.replace(/-/g, "+").replace(/_/g, "/");
	const binary = atob(base64 + "=".repeat((4 - (base64.length % 4)) % 4));
	const bytes = new Uint8Array(binary.length);
	for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
	return bytes;
}

const fromB64urlText = (text: string) => decoder.decode(fromB64url(text));

export async function sha256Hex(text: string) {
	const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", encoder.encode(text)));
	return Array.from(digest, (b) => b.toString(16).padStart(2, "0")).join("");
}

/** The game's own session token (HMAC-signed, like a JWT): which player, until when. */
export type Session = { sub: string; exp: number };
export const SESSION_DAYS = 180;

const hmacKeys = new Map<string, Promise<CryptoKey>>();
const hmacKey = (secret: string) => {
	let key = hmacKeys.get(secret);
	if (!key) {
		key = crypto.subtle.importKey("raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]);
		hmacKeys.set(secret, key);
	}
	return key;
};

export async function signSession(playerId: string, secret: string, now = Date.now()) {
	const header = b64url(JSON.stringify({ alg: "HS256", typ: "JWT" }));
	const payload = b64url(JSON.stringify({ sub: playerId, iat: Math.floor(now / 1000), exp: Math.floor(now / 1000) + SESSION_DAYS * 86400 }));
	const signature = await crypto.subtle.sign("HMAC", await hmacKey(secret), encoder.encode(`${header}.${payload}`));
	return `${header}.${payload}.${b64url(signature)}`;
}

export async function readSession(token: string | undefined, secret: string, now = Date.now()): Promise<Session | null> {
	if (!token) return null;
	const parts = token.split(".");
	if (parts.length !== 3) return null;
	try {
		// crypto.subtle.verify compares in constant time.
		if (!(await crypto.subtle.verify("HMAC", await hmacKey(secret), fromB64url(parts[2]), encoder.encode(`${parts[0]}.${parts[1]}`)))) return null;
		const payload = JSON.parse(fromB64urlText(parts[1]));
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
export type Jwk = { kid: string; kty: string; n: string; e: string; alg?: string };
export type KeySet = { keys: Jwk[] };
export type KeyFetcher = () => Promise<{ keys: KeySet; maxAgeMs: number }>;
type Claims = Record<string, unknown>;

/**
 * An OpenID Connect ID token checker: RS256, signed by one of the issuer's public keys (cached), issued by it, for one
 * of the game's audiences, not expired. Returns the claims, or null when the token is not good. Throws when the
 * issuer's keys are out of reach (an error, 503, not "refused").
 */
function idTokenChecker(issuers: string[], audiences: string[], fetchKeys: KeyFetcher, clock: () => number) {
	let cache: { keys: KeySet; until: number; fetchedAt: number } | null = null;
	const imported = new Map<string, Promise<CryptoKey>>();
	// Keys rotate: an unknown key id fetches them again, but at most once a minute (forged ids must not turn every
	// request into a call to Google or Apple).
	const keyFor = async (kid: string) => {
		const now = clock();
		const known = cache?.keys.keys.some((k) => k.kid === kid);
		if (!cache || cache.until < now || (!known && now - cache.fetchedAt >= 60_000)) {
			const fresh = await fetchKeys();
			cache = { keys: fresh.keys, until: now + fresh.maxAgeMs, fetchedAt: now };
			imported.clear();
		}
		const jwk = cache.keys.keys.find((k) => k.kid === kid);
		if (!jwk) return null;
		let key = imported.get(kid);
		if (!key) {
			key = crypto.subtle.importKey("jwk", { kty: jwk.kty, n: jwk.n, e: jwk.e, ext: true }, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
			imported.set(kid, key);
		}
		return { key };
	};
	return async (idToken: string): Promise<Claims | null> => {
		const parts = idToken.split(".");
		if (parts.length !== 3) return null;
		let header: { alg?: unknown; kid?: unknown };
		try {
			header = JSON.parse(fromB64urlText(parts[0]));
		} catch {
			return null;
		}
		if (header?.alg !== "RS256" || typeof header.kid !== "string") return null;
		const found = await keyFor(header.kid);
		if (!found) return null;
		try {
			const key = await found.key;
			if (!(await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, fromB64url(parts[2]), encoder.encode(`${parts[0]}.${parts[1]}`)))) return null;
			const claims = JSON.parse(fromB64urlText(parts[1]));
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

/** "Sign in with Google": signed by Google, issued by Google, for one of the game's OAuth clients, not expired. */
export function googleVerifier(clientIds: string[], fetchKeys: KeyFetcher = fetchGoogleKeys, clock = () => Date.now()): GoogleVerifier {
	const check = idTokenChecker(["accounts.google.com", "https://accounts.google.com"], clientIds, fetchKeys, clock);
	return async (idToken) => {
		const claims = await check(idToken);
		return claims ? { sub: claims.sub as string, email: text(claims.email), name: text(claims.name) } : null;
	};
}

/** "Sign in with Apple": signed by Apple, issued by https://appleid.apple.com, for the game's bundle id, not expired. */
export function appleVerifier(bundleIds: string[], fetchKeys: KeyFetcher = fetchAppleKeys, clock = () => Date.now()): AppleVerifier {
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
 * Apple's token API for the game (optional: needs a "Sign in with Apple" key from the Apple Developer account): the
 * login's one-time code becomes a refresh token, which is revoked when the player deletes the account (App Store rule
 * 5.1.1(v)). The client secret is a short JWT signed with the key (ES256).
 */
export type AppleKeyConfig = { teamId: string; keyId: string; privateKey: string; clientId: string };
export type AppleTokens = { exchange(code: string): Promise<string | null>; revoke(refreshToken: string): Promise<boolean> };

const pemKeys = new Map<string, Promise<CryptoKey>>();
function ecKey(pem: string) {
	let key = pemKeys.get(pem);
	if (!key) {
		const base64 = pem.replace(/-----(BEGIN|END) [A-Z ]+-----/g, "").replace(/\s+/g, "");
		const der = fromB64url(base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, ""));
		key = crypto.subtle.importKey("pkcs8", der, { name: "ECDSA", namedCurve: "P-256" }, false, ["sign"]);
		pemKeys.set(pem, key);
	}
	return key;
}

export async function appleClientSecret(config: AppleKeyConfig, now = Date.now()) {
	const header = b64url(JSON.stringify({ alg: "ES256", kid: config.keyId }));
	const iat = Math.floor(now / 1000);
	const payload = b64url(JSON.stringify({ iss: config.teamId, iat, exp: iat + 600, aud: "https://appleid.apple.com", sub: config.clientId }));
	// WebCrypto's ECDSA signature is r||s (IEEE P1363), which is what a JWT carries.
	const signature = await crypto.subtle.sign({ name: "ECDSA", hash: "SHA-256" }, await ecKey(config.privateKey), encoder.encode(`${header}.${payload}`));
	return `${header}.${payload}.${b64url(signature)}`;
}

export function appleTokens(config: AppleKeyConfig, post: typeof fetch = fetch, clock = () => Date.now(), log: (line: string) => void = console.log): AppleTokens {
	const form = async (endpoint: "token" | "revoke", fields: Record<string, string>) =>
		post(`https://appleid.apple.com/auth/${endpoint}`, {
			signal: AbortSignal.timeout(10_000),
			method: "POST",
			headers: { "content-type": "application/x-www-form-urlencoded" },
			body: new URLSearchParams({ client_id: config.clientId, client_secret: await appleClientSecret(config, clock()), ...fields }),
		});
	return {
		async exchange(code) {
			const response = await form("token", { code, grant_type: "authorization_code" });
			if (!response.ok) {
				log(`apple-code refused: ${response.status} ${(await response.text()).slice(0, 300)}`);
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
export function googleCodeExchange(clientId: string, clientSecret = "", log: (line: string) => void = console.log) {
	return async (code: string, codeVerifier: string, redirectUri: string) => {
		const response = await fetch("https://oauth2.googleapis.com/token", {
			signal: AbortSignal.timeout(10_000),
			method: "POST",
			headers: { "content-type": "application/x-www-form-urlencoded" },
			body: new URLSearchParams({ code, code_verifier: codeVerifier, redirect_uri: redirectUri, client_id: clientId, ...(clientSecret ? { client_secret: clientSecret } : {}), grant_type: "authorization_code" }),
		});
		if (!response.ok) {
			log(`google-code refused: ${response.status} ${(await response.text()).slice(0, 300)}`);
			return null;
		}
		const body = (await response.json()) as { id_token?: unknown };
		return typeof body.id_token === "string" ? body.id_token : null;
	};
}
