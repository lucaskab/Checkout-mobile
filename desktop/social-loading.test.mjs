import { plugin } from "bun";
import { afterAll, beforeEach, expect, mock, test } from "bun:test";

plugin({
	name: "png-as-id",
	setup(build) {
		build.onLoad({ filter: /\.png$/ }, (args) => ({
			contents: `const path = ${JSON.stringify(args.path)}; export default path; export const toString = () => path;`,
			loader: "js",
		}));
	},
});

// The Amigos window's loading state machine (desktop/social.ts socialPhase / syncSocialOnline / loadSocial), through the
// same messages Unity sends on a phone (`social` status, `social-call` → `social-reply`). TestFlight 1.0 (11), Lucas
// 05/11: after "Iniciar sessão com a Apple" the window stayed on "Carregando os amigos…" until it was closed and opened
// again — nothing started the load when the login landed while the window was open. Here: the login lands with the
// window open (or just before it opens) and the friends load by themselves; a call that never answers ends in the error
// card with "Tentar de novo"; a sign-out during the load drops its late answers; Google and Apple are the same path.
globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../src/stores/game-store.ts");
const social = await import("./social.ts");
const { pages } = await import("./pages/index.ts");

const initial = JSON.stringify(useGameStore.getState());
const game = () => useGameStore.getState();
let sent = [];
let onlineCalls = 0;
const settle = async () => {
	for (let i = 0; i < 5; i++) await Bun.sleep(1);
};
const calls = () => sent.filter((m) => m.kind === "social-call");
const pending = (path) => calls().filter((m) => m.path === path);
/** Unity's answer to one call (the body as the text Unity forwards). */
const reply = (message, code, body) => social.applySocialReply({ id: message.id, code, body: body === undefined ? "" : JSON.stringify(body), network: false });
const ME = { id: "p-1", code: "K7Q2MX4P", marketName: null, avatar: null, level: 1, era: "mesinha", likes: 0, friends: 0, invitedBy: null, invites: { rewarded: 0, milestones: [1, 3, 5] }, nameHidden: false, photo: null, showPhoto: true };
const answerAll = () => {
	for (const m of pending("/v1/social/me")) reply(m, 200, ME);
	for (const m of pending("/v1/social/friends")) reply(m, 200, { friends: [], incoming: [], outgoing: [] });
	for (const m of pending("/v1/social/requests")) reply(m, 200, { mine: [], friends: [] });
};
const firstCard = () => pages(game(), "amigos").cards[0]?.title;

function start(loadTimeoutMs = 20_000) {
	useGameStore.setState(JSON.parse(initial));
	social.resetSocial();
	sent = [];
	onlineCalls = 0;
	social.initSocial({ send: (m) => sent.push(m), refresh: () => {}, onOnline: () => onlineCalls++, unity: false, loadTimeoutMs });
	// The phone at start: Unity's first status, signed out (the Editor's fake server is not used here).
	social.applySocialStatus({ signedIn: false, mock: false, platform: "ios", canShare: true, avatars: 12 });
}
beforeEach(() => start());
afterAll(() => {
	social.resetSocial();
	useGameStore.setState(JSON.parse(initial));
});

for (const provider of ["apple", "google"]) {
	test(`${provider}: the login lands while Amigos shows the sign-in card → the friends load without reopening`, async () => {
		social.onSocialRoute("amigos");
		await settle();
		expect(social.socialPhase()).toBe("signed-out");
		expect(firstCard()).toBe("Entre para jogar com amigos");
		expect(calls()).toHaveLength(0);
		// CheckoutCloud has the session (same for Sign in with Apple and Google): CheckoutSocial sends the new status.
		social.applySocialStatus({ signedIn: true, mock: false, platform: provider === "apple" ? "ios" : "android", canShare: true, avatars: 12 });
		await settle();
		expect(social.socialPhase()).toBe("loading");
		expect(firstCard()).toBe("Carregando os amigos…");
		// The load started by itself: the first GET /me creates the profile on the server.
		expect(calls().map((m) => m.path).sort()).toEqual(["/v1/social/friends", "/v1/social/me", "/v1/social/requests"]);
		expect(onlineCalls).toBe(1);
		answerAll();
		await settle();
		expect(social.socialPhase()).toBe("ready");
		// First time: the setup (market name + the 12 faces).
		expect(firstCard()).toBe("Dê um nome ao seu mercado");
		expect(pages(game(), "amigos").board.tiles.filter((t) => t.action.action === "socialPickAvatar")).toHaveLength(12);
	});
}

test("the login lands just before Amigos opens (status first, window second): one load, no stuck card", async () => {
	social.applySocialStatus({ signedIn: true, mock: false, platform: "ios", canShare: true, avatars: 12 });
	await settle();
	// No window open: no social call in the background (the free plan's budget).
	expect(calls()).toHaveLength(0);
	social.onSocialRoute("amigos");
	await settle();
	expect(calls()).toHaveLength(3);
	answerAll();
	await settle();
	expect(social.socialPhase()).toBe("ready");
});

test("the window opens while Unity's status is still on its way (the old stuck case) and the status lands after", async () => {
	// The route is opened right after the login: Unity's `social` status comes a moment later.
	social.onSocialRoute("amigos");
	await settle();
	expect(calls()).toHaveLength(0);
	social.applySocialStatus({ signedIn: true, mock: false, platform: "ios", canShare: true, avatars: 12 });
	await settle();
	expect(calls()).toHaveLength(3);
	answerAll();
	await settle();
	expect(firstCard()).toBe("Dê um nome ao seu mercado");
});

test("a call that never answers ends in the error card with Tentar de novo, which loads again", async () => {
	start(60);
	social.onSocialRoute("amigos");
	social.applySocialStatus({ signedIn: true, mock: false, platform: "ios", canShare: true, avatars: 12 });
	await settle();
	expect(social.socialPhase()).toBe("loading");
	await Bun.sleep(90);
	expect(social.socialPhase()).toBe("error");
	const card = pages(game(), "amigos").cards[0];
	expect(card.title).toBe("Não deu para carregar os amigos");
	expect(card.buttons.map((b) => b.label)).toEqual(["Tentar de novo"]);
	expect(card.buttons[0].action).toBe("socialRefresh");
	// The late answers of the timed-out load change nothing; "Tentar de novo" starts a new one.
	answerAll();
	await settle();
	expect(social.socialPhase()).toBe("error");
	sent = [];
	expect(social.requestSocialAction("socialRefresh", []).ok).toBe(true);
	await settle();
	expect(social.socialPhase()).toBe("loading");
	expect(calls()).toHaveLength(3);
	answerAll();
	await settle();
	expect(social.socialPhase()).toBe("ready");
});

test("a failed profile call (server error, an empty answer, 401) shows the error card, never the loading card", async () => {
	social.onSocialRoute("amigos");
	social.applySocialStatus({ signedIn: true, mock: false, platform: "android", canShare: true, avatars: 12 });
	await settle();
	for (const m of pending("/v1/social/me")) reply(m, 200, undefined);
	for (const m of pending("/v1/social/friends")) reply(m, 200, { friends: [], incoming: [], outgoing: [] });
	for (const m of pending("/v1/social/requests")) reply(m, 200, { mine: [], friends: [] });
	await settle();
	expect(social.socialPhase()).toBe("error");
	sent = [];
	social.requestSocialAction("socialRefresh", []);
	await settle();
	for (const m of calls()) reply(m, 401, { error: "signed-out" });
	await settle();
	expect(social.socialPhase()).toBe("error");
	expect(social.socialStore.error).toBe("Entre de novo na sua conta para jogar com amigos.");
});

test("signing out during the load drops its late answers; signing in again loads afresh", async () => {
	social.onSocialRoute("amigos");
	social.applySocialStatus({ signedIn: true, mock: false, platform: "ios", canShare: true, avatars: 12 });
	await settle();
	const first = calls();
	social.applySocialStatus({ signedIn: false, mock: false, platform: "ios", canShare: true, avatars: 12 });
	for (const m of first.filter((m) => m.path === "/v1/social/me")) reply(m, 200, ME);
	for (const m of first.filter((m) => m.path !== "/v1/social/me")) reply(m, 200, {});
	await settle();
	expect(social.socialPhase()).toBe("signed-out");
	expect(social.socialStore.me).toBe(null);
	expect(social.socialStore.loading).toBe(false);
	sent = [];
	social.applySocialStatus({ signedIn: true, mock: false, platform: "ios", canShare: true, avatars: 12 });
	await settle();
	expect(calls()).toHaveLength(3);
	answerAll();
	await settle();
	expect(social.socialPhase()).toBe("ready");
});

test("closing Amigos before the login: the login loads nothing until the window opens again", async () => {
	social.onSocialRoute("amigos");
	social.onSocialRoute("");
	social.applySocialStatus({ signedIn: true, mock: false, platform: "ios", canShare: true, avatars: 12 });
	await settle();
	expect(calls()).toHaveLength(0);
	expect(social.socialStore.viewing).toBe(false);
});

test("Editor QA: the fake server signed out, then signed in with a slow answer, loads by itself", async () => {
	social.applySocialStatus({ signedIn: false, mock: true, platform: "editor", canShare: true, avatars: 12 });
	social.requestSocialAction("socialMock", ["signed-out"]);
	social.requestSocialAction("socialMock", ["latency", "40"]);
	social.onSocialRoute("amigos");
	await settle();
	expect(social.socialPhase()).toBe("signed-out");
	expect(firstCard()).toBe("Entre para jogar com amigos");
	social.requestSocialAction("socialMock", ["signed-out", "off"]);
	await settle();
	expect(social.socialPhase()).toBe("loading");
	await Bun.sleep(70);
	expect(social.socialPhase()).toBe("ready");
	expect(firstCard()).toBe("Dê um nome ao seu mercado");
});
