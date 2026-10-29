import { connect } from "cloudflare:sockets";
import { adminRoutes } from "./admin.ts";
import { createApp } from "./app.ts";
import type { Connect, Env } from "./cf.ts";
import { Store } from "./store.ts";
import { appleTokens, appleVerifier, googleCodeExchange, googleVerifier } from "./tokens.ts";

/**
 * checkout-server on Cloudflare Workers (free plan): D1 "checkout-saves" (binding DB) + R2 "checkout-saves" (binding
 * SAVES). Settings: Workers › checkout-server › Settings › Variables and Secrets (see worker/README.md).
 */
const SETTINGS = [
	"SESSION_SECRET",
	"GOOGLE_CLIENT_IDS",
	"GOOGLE_DESKTOP_CLIENT_ID",
	"GOOGLE_DESKTOP_CLIENT_SECRET",
	"GOOGLE_IOS_CLIENT_ID",
	"APPLE_BUNDLE_IDS",
	"APPLE_TEAM_ID",
	"APPLE_KEY_ID",
	"APPLE_PRIVATE_KEY",
	"OLD_DATABASE_URL",
	"ADMIN_PUBLIC_KEY",
] as const;

const log = (line: string) => console.log(line);
const list = (value: string | undefined) => (value ?? "").split(",").map((id) => id.trim()).filter(Boolean);

type Handler = (request: Request, address: string) => Promise<Response>;
const apps = new WeakMap<Env, Handler>();

function build(env: Env): Handler {
	const settings = Object.fromEntries(SETTINGS.map((name) => [name, !!env[name]]));
	const health = () => ({ settings, sessionSecretLongEnough: (env.SESSION_SECRET ?? "").length >= 32, storage: { DB: !!env.DB, SAVES: !!env.SAVES } });
	const clientIds = list(env.GOOGLE_CLIENT_IDS);
	const sessionSecret = env.SESSION_SECRET ?? "";
	if (sessionSecret.length < 32 || !clientIds.length || !env.DB || !env.SAVES) {
		// Not set up yet: only /health answers (it tells what is missing, by name), plus the token-gated /admin/* routes
		// (copy from Render, CPU benchmark), which need no session secret.
		const admin =
			env.ADMIN_PUBLIC_KEY && env.DB && env.SAVES
				? appFor(env, Array.from(crypto.getRandomValues(new Uint8Array(32)), (b) => b.toString(16)).join(""), [], health)
				: null;
		return async (request, address) => {
			const path = new URL(request.url).pathname;
			if (admin && path.startsWith("/admin/")) return admin(request, address);
			const status = path === "/health" || path === "/" ? 200 : 503;
			return new Response(JSON.stringify(status === 200 ? { ok: false, ...health() } : { error: "not-configured" }), {
				status,
				headers: { "content-type": "application/json", "cache-control": "no-store" },
			});
		};
	}
	return appFor(env, sessionSecret, clientIds, health);
}

function appFor(env: Env, sessionSecret: string, clientIds: string[], health: () => Record<string, unknown>): Handler {
	const appleBundleIds = list(env.APPLE_BUNDLE_IDS);
	const appleKey =
		env.APPLE_TEAM_ID && env.APPLE_KEY_ID && env.APPLE_PRIVATE_KEY && appleBundleIds.length
			? { teamId: env.APPLE_TEAM_ID, keyId: env.APPLE_KEY_ID, privateKey: env.APPLE_PRIVATE_KEY.replace(/\\n/g, "\n"), clientId: appleBundleIds[0] }
			: null;
	const store = new Store(env.DB, env.SAVES, { log });
	const app = createApp({
		store,
		verifyGoogle: googleVerifier(clientIds),
		exchangeCode:
			env.GOOGLE_DESKTOP_CLIENT_ID && env.GOOGLE_DESKTOP_CLIENT_SECRET ? googleCodeExchange(env.GOOGLE_DESKTOP_CLIENT_ID, env.GOOGLE_DESKTOP_CLIENT_SECRET, log) : null,
		exchangeIosCode: env.GOOGLE_IOS_CLIENT_ID ? googleCodeExchange(env.GOOGLE_IOS_CLIENT_ID, "", log) : null,
		verifyApple: appleBundleIds.length ? appleVerifier(appleBundleIds) : null,
		apple: appleKey ? appleTokens(appleKey, fetch, Date.now, log) : null,
		sessionSecret,
		log,
		health,
		extra: env.ADMIN_PUBLIC_KEY
			? adminRoutes({ publicKey: env.ADMIN_PUBLIC_KEY, oldDatabaseUrl: env.OLD_DATABASE_URL, connect: connect as unknown as Connect, db: env.DB, bucket: env.SAVES, store })
			: undefined,
	});
	return app;
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		let app = apps.get(env);
		if (!app) {
			app = build(env);
			apps.set(env, app);
		}
		return app(request, request.headers.get("cf-connecting-ip") ?? "");
	},
};
