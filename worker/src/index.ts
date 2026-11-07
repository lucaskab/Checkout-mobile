import { createApp } from "./app.ts";
import type { Env } from "./cf.ts";
import { HEADERS } from "./http.ts";
import { fcmSender, flushPush, readServiceAccount } from "./push.ts";
import { closeWeeks } from "./ranking-store.ts";
import type { BoardCache } from "./rankings.ts";
import { Store } from "./store.ts";
import { appleTokens, appleVerifier, googleCodeExchange, googleVerifier } from "./tokens.ts";

/**
 * checkout-server on Cloudflare Workers (free plan): D1 "checkout-saves" (binding DB) + R2 "checkout-saves" (binding
 * SAVES). Settings: Workers › checkout-server › Settings › Variables and Secrets (see worker/README.md).
 * Cron triggers: "5 0 * * 1" (Monday 00:05 UTC) the weekly league close, every 10 minutes the push flush (scheduled() below).
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
	"FCM_SERVICE_ACCOUNT",
] as const;

const log = (line: string) => console.log(line);
/** The least time between two accepted uploads of one save (the game uploads every 5 minutes and on leaving). */
const MIN_UPLOAD_GAP_MS = 2_000;
const list = (value: string | undefined) => (value ?? "").split(",").map((id) => id.trim()).filter(Boolean);

type Handler = (request: Request, address: string, country?: unknown, waitUntil?: (work: Promise<unknown>) => void) => Promise<Response>;
const apps = new WeakMap<Env, Handler>();

function build(env: Env): Handler {
	// Which settings exist goes to the Worker's log (Workers › checkout-server › Logs), not to the public /health: the
	// setup is nobody else's business (OWASP API8, security misconfiguration / information exposure).
	const missing = SETTINGS.filter((name) => !env[name]);
	const clientIds = list(env.GOOGLE_CLIENT_IDS);
	const sessionSecret = env.SESSION_SECRET ?? "";
	const configured = sessionSecret.length >= 32 && !!clientIds.length && !!env.DB && !!env.SAVES;
	log(`settings: ${configured ? "configured" : "NOT configured"}; missing: ${missing.join(", ") || "none"}${sessionSecret && sessionSecret.length < 32 ? "; SESSION_SECRET shorter than 32" : ""}${env.DB ? "" : "; no DB binding"}${env.SAVES ? "" : "; no SAVES binding"}`);
	const health = () => ({ configured });
	if (!configured) {
		// Not set up yet: only /health answers; the game's routes are 503 (what is missing is in the log above).
		return async (request) => {
			const path = new URL(request.url).pathname;
			const status = path === "/health" || path === "/" ? 200 : 503;
			return new Response(JSON.stringify(status === 200 ? { ok: false, ...health() } : { error: "not-configured" }), {
				status,
				headers: HEADERS,
			});
		};
	}
	// The Rate Limiting bindings come only with `wrangler deploy` (wrangler.jsonc "ratelimits"): say so when absent.
	const noLimiters = (["RL_IP", "RL_AUTH", "RL_PLAYER", "RL_SAVE"] as const).filter((name) => !env[name]);
	if (noLimiters.length) log(`rate limiting bindings missing (deploy with wrangler 4.36+): ${noLimiters.join(", ")}`);
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
		push: pushSender(env),
		// The Workers Cache API (the top lists of the boards, 10 min). Absent outside Workers (tests, benchmarks).
		cache: ((globalThis as { caches?: { default?: BoardCache } }).caches?.default as BoardCache | undefined) ?? null,
		limiters: { ip: env.RL_IP, auth: env.RL_AUTH, player: env.RL_PLAYER, save: env.RL_SAVE },
		minUploadGapMs: MIN_UPLOAD_GAP_MS,
		// The /admin/* routes of the move from Render (src/admin.ts) are no longer wired, whatever the settings say.
	});
	return app;
}

/** The FCM sender (push.ts), one per isolate, when the FCM_SERVICE_ACCOUNT secret holds a valid key. */
const senders = new WeakMap<Env, ReturnType<typeof fcmSender> | null>();
function pushSender(env: Env) {
	if (!senders.has(env)) {
		const account = readServiceAccount(env.FCM_SERVICE_ACCOUNT);
		if (env.FCM_SERVICE_ACCOUNT && !account) log("push: FCM_SERVICE_ACCOUNT is not a service account key");
		senders.set(env, account ? fcmSender(account, fetch, Date.now, log) : null);
	}
	return senders.get(env) ?? null;
}

export default {
	async fetch(request: Request, env: Env, ctx?: { waitUntil(promise: Promise<unknown>): void }): Promise<Response> {
		let app = apps.get(env);
		if (!app) {
			app = build(env);
			apps.set(env, app);
		}
		return app(request, request.headers.get("cf-connecting-ip") ?? "", (request as { cf?: { country?: unknown } }).cf?.country, ctx ? (work) => ctx.waitUntil(work) : undefined);
	},

	/** The cron trigger (Monday 00:05 UTC): closes last week's league groups and pays the rewards (ranking-store.ts). */
	async scheduled(controller: { cron?: string; scheduledTime?: number }, env: Env, ctx: { waitUntil(promise: Promise<unknown>): void }): Promise<void> {
		if (!env.DB) return;
		// Every 10 minutes: the pushes a social call left behind (more than one flush's worth) and the league results.
		if (controller.cron === "*/10 * * * *") {
			ctx.waitUntil(flushPush(env.DB, pushSender(env), Date.now(), log).catch((error) => log(`push flush failed: ${(error as Error)?.message ?? error}`)));
			return;
		}
		const store = new Store(env.DB, env.SAVES, { log });
		ctx.waitUntil(
			closeWeeks(store, Date.now(), log)
				.catch((error) => {
					log(`league close failed: ${(error as Error)?.stack ?? error}`);
				})
				// The week's results are in the inbox now: the first "liga fechou" pushes (the 10-min cron sends the rest).
				.then(() => flushPush(env.DB, pushSender(env), Date.now(), log))
				.catch((error) => log(`league push failed: ${(error as Error)?.message ?? error}`)),
		);
	},
};
