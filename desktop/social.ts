import type { GameState } from "@/@types/game";
import type { SocialInboxOutcome, SocialPublicBlock } from "@/@types/social";
import type { SimulatorSnapshot } from "@/@types/simulator";
import { getMarketEra } from "@/data/economy";
import { type GameIconId, gameIconAssets } from "@/data/game-icon-assets";
import { itemCatalog } from "@/data/market-products";
import { getSocialRewards, SOCIAL_REQUEST_MAX, SOCIAL_REQUEST_MIN } from "@/data/social";
import { t } from "@/i18n";
import { canSendProduct, helpsToday, normalizeSocialState, productIdOf } from "@/services/social";
import { createSimulatorSnapshot } from "@/services/simulator-snapshot";
import { useGameStore } from "@/stores/game-store";
import { createMockSocialServer, type MockSocialServer } from "./social-mock";
import { act, type Button, button, fmt, gameIcon } from "./view-kit";

// Social v1 on the host (docs/social-api.md): the friends' data, the inbox cycle, the visit and the actions of the
// Amigos pages. Unity owns the network and the session (CheckoutSocial.cs): the host asks it for each call
// (`social-call` → `social-reply`) and never sees the token. In the Editor Unity says "mock" and the calls are answered
// by desktop/social-mock.ts in this process.
//
// The visit never touches the player's store: the friend's save is migrated into a separate object, snapshots of it go
// to Unity under their own session (so every command Unity sends from the friend's market is refused), the player's
// timers stop and nothing is written. What the player earns there (like / help coins, items sent) is booked when they
// come back home.

export type SocialPerson = { id: string; code: string; marketName: string | null; avatar: string | null; level: number; era: string };
export type SocialRequestView = { id: number; productId: number; qty: number; createdAt: number; expiresAt: number; owner?: string };
export type SocialFriend = SocialPerson & {
	/** The friend's Google profile photo (docs/social-api.md › Photos), checked by photoOf; null = their avatar. */
	photo: string | null;
	likes: number;
	lastSeen: number;
	giftedToday: boolean;
	likedToday: boolean;
	public: SocialPublicBlock | null;
	openRequests: SocialRequestView[];
};
export type SocialMe = {
	id: string;
	/** The market name was reported and is hidden from the others ("Mercado #code") until the owner picks another. */
	nameHidden: boolean;
	code: string;
	marketName: string | null;
	avatar: string | null;
	level: number;
	era: string;
	likes: number;
	friends: number;
	invitedBy: string | null;
	invites: { rewarded: number; milestones: number[] };
	/** My Google profile photo (null: none, Apple, or an older server) and the switch "Mostrar minha foto do Google para
	 * amigos" (absent = on). */
	photo?: string | null;
	showPhoto?: boolean;
};
type Reply = { code: number; body: any; network: boolean };
type Visit = {
	friend: SocialFriend;
	public: SocialPublicBlock | null;
	state: GameState;
	session: string;
	revision: number;
	/** Builds helped during this visit (the world buttons turn into "Ajudado"). */
	helped: Set<string>;
	liked: boolean;
	gifted: boolean;
	/** Booked when the player comes back home. */
	earned: { likes: number; helps: number; sends: { productId: number; qty: number }[] };
	/** A player of the Mundo / País boards who is not a friend (Lucas 10/11): only to look — no like, gift, help or
	 * delivery (the server refuses them too: those routes need a friendship). */
	viewOnly: boolean;
};
export type SocialNews = { text: string; icon: string; at: number };

const INVITE_HOST = "https://checkout-server.lucaslfurini.workers.dev";
const CODE_LETTERS = /^[23456789ABCDEFGHJKMNPQRSTUVWXYZ]{8}$/;

export const socialStore = {
	/** Unity's status: signed in with Google / Apple (social needs an account), the mock (Editor), the share sheet. */
	signedIn: false,
	mock: false,
	platform: "",
	canShare: false,
	/** Avatars Unity can draw (portraits of the game's own shoppers). */
	avatars: 12,
	me: null as SocialMe | null,
	friends: [] as SocialFriend[],
	incoming: [] as SocialPerson[],
	outgoing: [] as SocialPerson[],
	requests: { mine: [] as SocialRequestView[], friends: [] as SocialRequestView[] },
	loadedAt: 0,
	loading: false,
	error: "",
	/** An Amigos window is open now (a sign-in that lands meanwhile loads it at once). */
	viewing: false,
	/** Results of the inbox and friend requests not seen yet (the badge on Amigos) and the latest ones. */
	unseen: 0,
	news: [] as SocialNews[],
	/** The profile page's choices before "Salvar" (avatar picked, the name field). */
	draft: { avatar: "", name: "" },
	/** An invite code from a link (checkout://add/…) or the Play Install Referrer, offered on the Amigos page. */
	offeredCode: "",
	/** Actions on their way to the server (their buttons wait). */
	busy: new Set<string>(),
	/** "Remover" asks once more (friend id), the QR code is open. */
	confirmRemove: "",
	showQr: false,
	/** Builds the player helped this session (friend|build): the Amigos badges skip them. */
	helped: new Set<string>(),
	visit: null as Visit | null,
	/** An inbox fetch that came while visiting: done when the player is back. */
	tickWaiting: false,
	inboxRunning: false,
	lastInboxAt: 0,
};

let send: (message: unknown) => void = () => {};
let refresh: () => void = () => {};
let onVisit: (active: boolean) => void = () => {};
let onOnline: () => void = () => {};
let mock: MockSocialServer | null = null;
/**
 * The Amigos load never shows "Carregando os amigos…" for longer than this: past it the window shows the error card
 * with "Tentar de novo" (Lucas 05/11, TestFlight 1.0 (11): the friends stayed loading forever after an Apple login).
 */
export const SOCIAL_LOAD_TIMEOUT_MS = 20_000;
let loadTimeout = SOCIAL_LOAD_TIMEOUT_MS;
/** Each load has a number; an answer of an older load (the account changed meanwhile) is dropped. */
let loadGeneration = 0;
/** Online (signed in, or the Editor's fake server) as last seen: a change signs the Amigos data in or out. */
let lastOnline = false;
let sequence = 0;
const waiting = new Map<string, (reply: Reply) => void>();
const flushes = new Map<string, () => void>();
/** Tests run without Unity: no flush to wait for. */
let unity = true;

export function initSocial(options: {
	send: (message: unknown) => void;
	refresh: () => void;
	onVisit?: (active: boolean) => void;
	/** The player just signed in (Google / Apple): the host reloads whatever window is open (Ranking). */
	onOnline?: () => void;
	unity?: boolean;
	/** Tests: a shorter limit for the Amigos load. */
	loadTimeoutMs?: number;
}) {
	send = options.send;
	refresh = options.refresh;
	onVisit = options.onVisit ?? (() => {});
	onOnline = options.onOnline ?? (() => {});
	unity = options.unity ?? true;
	loadTimeout = options.loadTimeoutMs ?? SOCIAL_LOAD_TIMEOUT_MS;
}

/** The mock server of this session (QA controls, tests). */
export function socialMock() {
	if (!mock) mock = createMockSocialServer();
	return mock;
}
export function resetSocial() {
	Object.assign(socialStore, {
		signedIn: false, mock: false, platform: "", canShare: false, avatars: 12, me: null, friends: [], incoming: [], outgoing: [],
		requests: { mine: [], friends: [] }, loadedAt: 0, loading: false, error: "", viewing: false, unseen: 0, news: [], draft: { avatar: "", name: "" },
		offeredCode: "", busy: new Set(), confirmRemove: "", showQr: false, helped: new Set(), visit: null, tickWaiting: false,
		inboxRunning: false, lastInboxAt: 0,
	});
	mock = null;
	waiting.clear();
	flushes.clear();
	loadGeneration++;
	lastOnline = false;
}

// ------------------------------------------------------------------------------------------------------------ transport

function call(method: string, path: string, body?: unknown, open = false): Promise<Reply> {
	if (socialStore.mock) {
		const server = socialMock();
		// (QA "signed-out": the fake account is signed out, like Unity answering without a session)
		if (!open && !path.startsWith("/v1/rankings") && server.rankings.signedOut) return Promise.resolve({ code: 401, body: { error: "signed-out" }, network: false });
		const answer = server.call(method, path, body === undefined ? undefined : JSON.stringify(body));
		// (QA "hang": a call that never comes back; whoever waits on it has its own time limit)
		if (!answer) return new Promise(() => {});
		if (server.latency > 0) return new Promise((resolve) => setTimeout(() => resolve(answer as Reply), server.latency));
		return Promise.resolve(answer as Reply);
	}
	// (`open`: a public route — the rankings' Mundo / País — that Unity calls without the session when signed out)
	if (!socialStore.signedIn && !open) return Promise.resolve({ code: 401, body: null, network: false });
	const id = `social-${++sequence}`;
	return new Promise((resolve) => {
		const timer = setTimeout(() => {
			waiting.delete(id);
			resolve({ code: 0, body: null, network: true });
		}, 45_000);
		waiting.set(id, (reply) => {
			clearTimeout(timer);
			resolve(reply);
		});
		send({ kind: "social-call", id, method, path, body: body === undefined ? "" : JSON.stringify(body), open });
	});
}

/** Rankings v1 (desktop/rankings.ts) talks to the same server through the same pipe (Unity holds the session). */
export const socialCall = (method: string, path: string, body?: unknown, open = false) => call(method, path, body, open);
export type SocialReply = Reply;
/** Makes sure the player has a social profile (the first /v1/social call creates it): opening Ranking counts. */
export const ensureSocialProfile = () => (socialStore.me ? Promise.resolve(true) : loadProfile());

/** Writes the save to the phone's disk now (Unity: CheckoutDesktopHost.Flush) before the server may forget items. */
function flush(): Promise<void> {
	if (!unity) return Promise.resolve();
	const id = `flush-${++sequence}`;
	return new Promise((resolve) => {
		const timer = setTimeout(() => {
			flushes.delete(id);
			resolve();
		}, 10_000);
		flushes.set(id, () => {
			clearTimeout(timer);
			resolve();
		});
		send({ kind: "social-flush", id });
	});
}

// ------------------------------------------------------------------------------------------------------------ helpers

export const formatCode = (code: string) => (code.length === 8 ? `${code.slice(0, 4)}-${code.slice(4)}` : code);
export const normalizeCode = (value: unknown) => String(value ?? "").toUpperCase().replace(/[^0-9A-Z]/g, "");
export const isCode = (value: string) => CODE_LETTERS.test(value);
export const inviteUrl = (code: string) => `${INVITE_HOST}/i/${code}`;
/** The friend's market name, or "Mercado #CODE" when the server hides it (reports) or none was chosen yet. */
export const marketName = (person: { marketName: string | null; code: string }) => person.marketName?.trim() || `Mercado #${formatCode(person.code)}`;
export const stageName = (era: string) => {
	try {
		return getMarketEra(era as never).name;
	} catch {
		return "";
	}
};
/**
 * A Google profile photo the game may draw (docs/social-api.md › Photos): https on lh3…lh6.googleusercontent.com, at
 * most 1024 characters, no "|" (the icon's separator). Anything else = no photo (the avatar shows).
 */
export function photoOf(value: unknown): string | null {
	if (typeof value !== "string" || value.length > 1024 || value.includes("|") || /\s/.test(value)) return null;
	return /^https:\/\/lh[3-6]\.googleusercontent\.com\/[^?#]*/.test(value) ? value : null;
}
/**
 * A player's face for Unity: "avatar:shopper-3" (a portrait of one of the game's shoppers) or, with a photo,
 * "avatar:shopper-3|https://lh3…" — Unity draws the photo round in the gold ring once it is downloaded and the avatar
 * meanwhile (or when it fails). Photos only for friends and myself in the friend screens (the server sends them only
 * there).
 */
export const avatarIcon = (avatar: string | null | undefined, photo?: string | null) => {
	const face = avatar ? `avatar:${avatar}` : "avatar:shopper-1";
	const shown = photoOf(photo);
	return shown ? `${face}|${shown}` : face;
};
/** My own photo as my friends see it: the Google photo when I have one and the switch is on (else null = avatar). */
export const myPhoto = () => (socialStore.me && socialStore.me.showPhoto !== false ? photoOf(socialStore.me.photo) : null);
/** The badge of a stage on a friend's portrait (the game's own 2D icons). */
const stageIcons: Record<string, GameIconId> = {
	mesinha: "priceTag",
	tenda: "festival",
	banca: "basket",
	conteiner: "package",
	spati: "shelf",
	quitanda: "plant",
	minimercado: "cart",
	mercadinho: "market",
	supermercado: "market",
	hipermercado: "distributionCenter",
	rede: "crown",
};
export const stageIcon = (era: string) => gameIcon(stageIcons[era] ?? "market");
/**
 * Social icons (2D, the game's painted style). friends / like / share / invite are coming as new files: until they are
 * in src/data/game-icon-assets.ts these fall back to icons already in the set, so adding the files is a drop-in.
 */
export type SocialIconId = GameIconId | "friends" | "like" | "share" | "invite";
const iconFallbacks: Record<string, GameIconId> = { friends: "customers", like: "success", share: "smartphone", invite: "ticket" };
export const socialIcon = (id: SocialIconId) => gameIcon((id in gameIconAssets ? id : (iconFallbacks[id] ?? "handshake")) as GameIconId);
/** What each inbox result shows: gift, like, help (a hand), a delivery (the box of a product request), diamonds, friends. */
const iconOf: Record<string, SocialIconId> = { gift: "gift", heart: "like", construction: "handshake", truck: "package", diamond: "diamond", customers: "friends", trophy: "trophy" };
export const outcomeIcon = (icon: string): SocialIconId => iconOf[icon] ?? "friends";
const parse = (body: unknown) => {
	if (typeof body !== "string") return body;
	try {
		return JSON.parse(body);
	} catch {
		return null;
	}
};
/** A request as the server sends it (product id as text) in the game's shape (catalog id as a number). */
const requestOf = (raw: any): SocialRequestView => ({
	id: Number(raw?.id),
	productId: productIdOf(raw?.productId),
	qty: Number(raw?.qty) || 0,
	createdAt: Number(raw?.createdAt) || 0,
	expiresAt: Number(raw?.expiresAt) || 0,
	...(raw?.owner ? { owner: String(raw.owner) } : {}),
});
const requestsOf = (list: unknown) => (Array.isArray(list) ? list.map(requestOf).filter((item) => Number.isFinite(item.productId)) : []);
const friendOf = (raw: any): SocialFriend => ({ ...raw, photo: photoOf(raw?.photo), openRequests: requestsOf(raw?.openRequests) });
const errorOf = (reply: Reply) => (reply.body && typeof reply.body === "object" ? String((reply.body as { error?: unknown }).error ?? "") : "");

/** What went wrong, in words for the player. */
function trouble(reply: Reply, words: Record<string, string> = {}) {
	if (reply.network || reply.code === 0) return "Sem conexão. Tente de novo daqui a pouco.";
	if (reply.code === 401) return "Entre de novo na sua conta para jogar com amigos.";
	const error = errorOf(reply);
	if (error === "slow-down") return "Calma! Tente de novo daqui a pouco.";
	return words[error] ?? words[String(reply.code)] ?? (reply.code === 429 ? "Limite de hoje atingido. Volte amanhã!" : "Não foi possível agora.");
}

/** A toast in the player's language: the Portuguese template with {0} name, {1} coins, {2} minutes, {3} qty, {4} product, {5} diamonds. */
export function toastText(template: string, values: { name?: string; coins?: number; minutes?: number; qty?: number; product?: string; diamonds?: number } = {}) {
	return t(template)
		.replaceAll("{0}", values.name ?? "")
		.replaceAll("{1}", String(values.coins ?? 0))
		.replaceAll("{2}", String(values.minutes ?? 0))
		.replaceAll("{3}", String(values.qty ?? 0))
		.replaceAll("{4}", values.product ? t(values.product) : "")
		.replaceAll("{5}", String(values.diamonds ?? 0));
}
function toast(text: string, icon: SocialIconId = "friends", ok = true) {
	send({ kind: "social-toast", text, icon: socialIcon(icon), ok });
}
const productName = (id: number) => itemCatalog.find((item) => item.id === id)?.name ?? "";

// ------------------------------------------------------------------------------------------------------------ messages

/** Signed in with Google / Apple (social needs an account), or the Editor's fake server unless QA plays "signed out". */
export function socialOnline() {
	if (socialStore.mock) return !socialMock().rankings.signedOut;
	return socialStore.signedIn;
}

/** Unity's status (`social`): account, mock (Editor), platform, share sheet, avatars. */
export function applySocialStatus(message: { signedIn?: unknown; mock?: unknown; platform?: unknown; canShare?: unknown; avatars?: unknown }) {
	socialStore.signedIn = message.signedIn === true;
	socialStore.mock = message.mock === true;
	socialStore.platform = typeof message.platform === "string" ? message.platform : "";
	socialStore.canShare = message.canShare === true;
	if (typeof message.avatars === "number" && message.avatars > 0) socialStore.avatars = Math.min(12, Math.floor(message.avatars));
	return syncSocialOnline();
}

/**
 * The account changed (Unity's status after a Google / Apple login or a sign-out; QA's "signed-out" on the fake server).
 * Signed out: what belonged to the account goes away (the save keeps its own mirror) and a load on its way is dropped.
 * Signed in: an Amigos window that is open (it was showing "Entre para jogar com amigos", or the login finished just
 * before it opened) loads now, without being closed and opened again — the TestFlight 1.0 (11) bug, where nothing
 * started the load and the window stayed on "Carregando os amigos…" until it was reopened.
 */
export function syncSocialOnline() {
	const now = socialOnline();
	if (now === lastOnline) return false;
	lastOnline = now;
	loadGeneration++;
	if (!now) {
		Object.assign(socialStore, { me: null, friends: [], incoming: [], outgoing: [], requests: { mine: [], friends: [] }, loadedAt: 0, loading: false, error: "" });
		refresh();
		return true;
	}
	Object.assign(socialStore, { loading: false, error: "", loadedAt: 0 });
	if (socialStore.viewing) void loadSocial(true);
	onOnline();
	refresh();
	return true;
}

/**
 * What an Amigos window shows before its content: the sign-in card, the loading card, the error card with "Tentar de
 * novo", or the content (the first-time profile included). "loading" only while a load is really on its way: every
 * load ends in "ready" or "error" within SOCIAL_LOAD_TIMEOUT_MS.
 */
export type SocialPhase = "signed-out" | "loading" | "error" | "ready";
export function socialPhase(): SocialPhase {
	if (!socialOnline()) return "signed-out";
	if (socialStore.me) return "ready";
	return socialStore.error && !socialStore.loading ? "error" : "loading";
}

export function applySocialReply(message: { id?: unknown; code?: unknown; body?: unknown; network?: unknown }) {
	const done = waiting.get(String(message.id ?? ""));
	if (!done) return;
	waiting.delete(String(message.id));
	done({ code: Number(message.code) || 0, body: parse(message.body), network: message.network === true });
}
export function applySocialFlushed(message: { id?: unknown }) {
	const done = flushes.get(String(message.id ?? ""));
	if (!done) return;
	flushes.delete(String(message.id));
	done();
}
/** A code from checkout://add/<code> or the Play Install Referrer (invite=<code>): offered on the Amigos page. */
export function applySocialLink(message: { code?: unknown; source?: unknown }) {
	const code = normalizeCode(message.code);
	if (!isCode(code)) return false;
	socialStore.offeredCode = code;
	return true;
}

// ------------------------------------------------------------------------------------------------------------ inbox

/**
 * The inbox cycle (start, after login, every 5 min with the cloud sync): fetch, apply to the save (exactly once),
 * write the save to disk, then ack. A crash anywhere before the ack only means the items come again and are acked
 * without paying twice (social.appliedInbox).
 */
export async function runInboxCycle(reason = "tick") {
	if (!socialOnline() || socialStore.inboxRunning) return { applied: 0, acked: 0 };
	// Players who never opened Amigos have no social profile on the server (and nothing in an inbox): no background calls.
	if (!socialTouched()) return { applied: 0, acked: 0 };
	if (socialStore.visit) {
		socialStore.tickWaiting = true;
		return { applied: 0, acked: 0 };
	}
	socialStore.inboxRunning = true;
	try {
		const reply = await call("GET", "/v1/social/inbox");
		socialStore.lastInboxAt = Date.now();
		// After a login (maybe another phone or a new account): make sure the profile exists and the mirror is right.
		if (reason === "login" && !socialStore.me) void loadProfile();
		if (reply.code !== 200 || !reply.body || !Array.isArray(reply.body.items)) return { applied: 0, acked: 0, reason };
		const items = reply.body.items as unknown[];
		if (!items.length) return { applied: 0, acked: 0 };
		// A visit started while the request was out: the save stays frozen; the same items come next time.
		if (socialStore.visit) {
			socialStore.tickWaiting = true;
			return { applied: 0, acked: 0 };
		}
		const { outcomes, ack } = useGameStore.getState().applySocialInbox(items);
		celebrate(outcomes.filter((outcome) => outcome.applied));
		refresh();
		if (!ack.length) return { applied: outcomes.filter((o) => o.applied).length, acked: 0 };
		await flush();
		// At most 300 ids per call.
		let acked = 0;
		const ids = ack.map((id) => (/^\d+$/.test(id) ? Number(id) : id));
		for (let i = 0; i < ids.length; i += 300) {
			const chunk = ids.slice(i, i + 300);
			const answer = await call("POST", "/v1/social/inbox/ack", { ids: chunk });
			if (answer.code === 204 || answer.code === 200) acked += chunk.length;
		}
		return { applied: outcomes.filter((o) => o.applied).length, acked };
	} finally {
		socialStore.inboxRunning = false;
	}
}

function celebrate(outcomes: SocialInboxOutcome[]) {
	for (const outcome of outcomes) {
		if (!outcome.text) continue;
		const text = toastText(outcome.text, {
			name: outcome.name,
			coins: outcome.coins,
			minutes: outcome.minutes,
			qty: outcome.qty,
			product: productName(outcome.productId),
			diamonds: outcome.diamonds,
		});
		const icon = outcomeIcon(outcome.icon);
		toast(text, icon);
		socialStore.news.unshift({ text, icon: socialIcon(icon), at: Date.now() });
		socialStore.unseen++;
		// The friend lists change with these: reloaded next time the page opens.
		if (["friend_request", "friend_added", "request_fulfilled", "delivery"].includes(outcome.kind)) socialStore.loadedAt = 0;
	}
	socialStore.news.length = Math.min(socialStore.news.length, 12);
}

// ------------------------------------------------------------------------------------------------------------ loading

/** The player opened Amigos once on this save (the save keeps the code): the inbox is polled from then on. */
export const socialTouched = () => Boolean(useGameStore.getState().social?.profile?.code) || Boolean(socialStore.me);

/** Only the profile (after a login, once social was touched): creates it on this account if needed. */
async function loadProfile() {
	const me = await call("GET", "/v1/social/me");
	if (me.code !== 200 || !me.body) return false;
	socialStore.me = me.body as SocialMe;
	if (!socialStore.visit) useGameStore.getState().rememberSocialProfile({ code: socialStore.me.code, marketName: socialStore.me.marketName, avatar: socialStore.me.avatar ?? "" });
	return true;
}

/** Resolves to null when the work takes longer than `ms`. */
function within<T>(work: Promise<T>, ms: number): Promise<T | null> {
	return new Promise((resolve) => {
		const timer = setTimeout(() => resolve(null), ms);
		work.then(
			(value) => {
				clearTimeout(timer);
				resolve(value);
			},
			() => {
				clearTimeout(timer);
				resolve(null);
			},
		);
	});
}

/**
 * The Amigos page opened: profile, friends and requests (user-triggered, at most every 20 s unless forced). The first
 * `GET /v1/social/me` of an account creates its profile (the first-time setup follows: name + face). Always ends in the
 * profile or an error (the time limit included), never in a loading card that nothing resolves.
 */
export async function loadSocial(force = false) {
	if (!socialOnline() || socialStore.loading) return false;
	if (!force && socialStore.me && Date.now() - socialStore.loadedAt < 20_000) return false;
	const generation = ++loadGeneration;
	socialStore.loading = true;
	socialStore.error = "";
	refresh();
	try {
		const answers = await within(Promise.all([call("GET", "/v1/social/me"), call("GET", "/v1/social/friends"), call("GET", "/v1/social/requests")]), loadTimeout);
		// The account changed while the calls were out (signed out, another login): a newer load or the sign-in card
		// takes over.
		if (generation !== loadGeneration) return false;
		if (!answers) {
			console.error(`CHECKOUT_SOCIAL load timed out after ${loadTimeout} ms`);
			socialStore.error = "Sem conexão. Tente de novo daqui a pouco.";
			return false;
		}
		const [me, friends, requests] = answers;
		if (me.code !== 200 || !me.body || typeof me.body !== "object" || !(me.body as SocialMe).code) {
			socialStore.error = trouble(me);
			return false;
		}
		socialStore.me = me.body as SocialMe;
		if (friends.code === 200 && friends.body) {
			socialStore.friends = Array.isArray(friends.body.friends) ? friends.body.friends.map(friendOf) : [];
			socialStore.incoming = Array.isArray(friends.body.incoming) ? friends.body.incoming : [];
			socialStore.outgoing = Array.isArray(friends.body.outgoing) ? friends.body.outgoing : [];
		}
		if (requests.code === 200 && requests.body) {
			socialStore.requests = {
				mine: requestsOf(requests.body.mine),
				friends: requestsOf(requests.body.friends),
			};
		}
		socialStore.loadedAt = Date.now();
		// The save keeps a mirror (the stock page shows the open requests without a call). Never while visiting.
		if (!socialStore.visit) {
			const store = useGameStore.getState();
			store.rememberSocialProfile({ code: socialStore.me.code, marketName: socialStore.me.marketName, avatar: socialStore.me.avatar ?? "" });
			store.rememberSocialRequests(socialStore.requests.mine);
		}
		if (!socialStore.draft.avatar) socialStore.draft.avatar = socialStore.me.avatar ?? "";
		return true;
	} finally {
		if (generation === loadGeneration) {
			socialStore.loading = false;
			refresh();
		}
	}
}

/** Opening any Amigos page loads the data and clears the badge; leaving them ends the window (no loads meanwhile). */
export function onSocialRoute(route: string) {
	const name = route.split(":")[0];
	socialStore.viewing = name === "amigos" || name.startsWith("amigos-");
	if (!socialStore.viewing) return;
	socialStore.unseen = 0;
	void loadSocial(false);
}

// ------------------------------------------------------------------------------------------------------------ the visit

/** The friend's save as GET …/market returns it: the CloudSave object, its `data` text, or `{state, version}`. */
export async function loadFriendState(data: unknown): Promise<GameState | null> {
	try {
		let value = typeof data === "string" ? JSON.parse(data) : data;
		if (value && typeof value === "object" && typeof (value as { data?: unknown }).data === "string") value = JSON.parse((value as { data: string }).data);
		const save = value as { state?: unknown; version?: number };
		if (!save || typeof save !== "object" || !save.state || typeof save.state !== "object") return null;
		const options = useGameStore.persist.getOptions();
		const copy = JSON.parse(JSON.stringify(save.state));
		const version = typeof save.version === "number" ? save.version : 0;
		const migrated = version === options.version ? copy : await options.migrate!(copy, version);
		// Like the persist middleware's merge: a new game under what the save holds. Nothing here is the player's.
		const fresh = JSON.parse(JSON.stringify(useGameStore.getInitialState(), (_key, item) => (typeof item === "function" ? undefined : item)));
		return { ...fresh, ...(migrated as object) } as GameState;
	} catch (error) {
		console.error(`CHECKOUT_SOCIAL friend save: ${String(error)}`);
		return null;
	}
}

export const isVisiting = () => socialStore.visit !== null;

/** The friend's market for Unity: read-only (closed, no customers, no event, nothing to tap but the builds). */
export function visitSnapshot(): SimulatorSnapshot | null {
	const visit = socialStore.visit;
	if (!visit) return null;
	const snapshot = createSimulatorSnapshot(visit.state, visit.session, visit.revision);
	return {
		...snapshot,
		isOpen: false,
		customers: [],
		checkouts: [],
		checkoutResults: [],
		incidents: [],
		dock: [],
		restockSlots: [],
		staffTasks: [],
		reveals: [],
		decorPlays: [],
		delivery: { ...snapshot.delivery, orders: [], active: 0 },
		day: { ...snapshot.day, phase: "planning" },
		event: { ...snapshot.event, id: "", name: "", description: "", effectLabel: "", kind: "", endsAt: 0, interaction: "", stops: [], seal: false, windowRequests: [], windowServed: 0, windowGoal: 0 },
	};
}

/**
 * Opens a market to walk around in. A friend's (Amigos, the friends board): like, gift, help, deliver. A player of the
 * Mundo / País boards who is not a friend (`fromRanking`, Lucas 10/11: "só dá para visitar e ver como é o mercado da
 * pessoa"): GET /v1/social/players/:id/market, which the server allows only for the top of the world or a country,
 * and the visit is only to look (viewOnly). A friend found on those boards opens as a friend.
 */
export async function startVisit(friendId: string, fromRanking = false) {
	if (socialStore.visit || socialStore.busy.has(`visit:${friendId}`)) return { ok: false, reason: "" };
	const viewOnly = fromRanking && !socialStore.friends.some((friend) => friend.id === friendId);
	socialStore.busy.add(`visit:${friendId}`);
	refresh();
	try {
		const reply = await call("GET", `/v1/social/${viewOnly ? "players" : "friends"}/${encodeURIComponent(friendId)}/market`);
		if (reply.code !== 200 || !reply.body) {
			const reason = trouble(reply, {
				"no-save": viewOnly ? "Esse jogador ainda não salvou o mercado na nuvem." : "Esse amigo ainda não salvou o mercado na nuvem.",
				"not-friends": "Vocês não são mais amigos.",
				"not-public": "Esse mercado saiu do ranking.",
			});
			toast(t(reason), "warning", false);
			return { ok: false, reason };
		}
		const state = await loadFriendState(reply.body.data);
		if (!state) {
			toast(t(viewOnly ? "Não deu para abrir esse mercado." : "Não deu para abrir o mercado desse amigo."), "warning", false);
			return { ok: false, reason: "bad-save" };
		}
		const known = socialStore.friends.find((friend) => friend.id === friendId);
		const friend = friendOf({ ...(known ?? {}), ...(reply.body.profile ?? {}) });
		socialStore.visit = {
			friend,
			public: reply.body.public ?? friend.public ?? null,
			state,
			session: `visit-${friendId}-${Date.now()}`,
			revision: 1,
			helped: new Set(),
			liked: friend.likedToday === true,
			gifted: friend.giftedToday === true,
			earned: { likes: 0, helps: 0, sends: [] },
			viewOnly,
		};
		send({ kind: "social-visit", active: true, friendId, name: marketName(friend) });
		onVisit(true);
		return { ok: true, reason: "" };
	} finally {
		socialStore.busy.delete(`visit:${friendId}`);
		refresh();
	}
}

/** "Voltar ao meu mercado": the player's own market comes back exactly as it was; then what they earned is booked. */
export function endVisit() {
	const visit = socialStore.visit;
	if (!visit) return false;
	socialStore.visit = null;
	send({ kind: "social-visit", active: false, friendId: visit.friend.id, name: "" });
	// The player's own market (snapshot and HUD) first, exactly as it was; then what was earned is booked.
	onVisit(false);
	const store = useGameStore.getState();
	let coins = 0;
	for (let i = 0; i < visit.earned.likes; i++) coins += store.claimSocialHelperReward("like");
	for (let i = 0; i < visit.earned.helps; i++) coins += useGameStore.getState().claimSocialHelperReward("help");
	for (const item of visit.earned.sends) coins += useGameStore.getState().completeSocialDelivery(item.productId, item.qty) ?? 0;
	if (coins > 0) toast(toastText("Visita: +{1} moedas", { coins }), "coin");
	if (socialStore.tickWaiting) {
		socialStore.tickWaiting = false;
		setTimeout(() => void runInboxCycle("after-visit"), 1_500);
	}
	return true;
}

/** Units the player can still send: the stock room minus what is promised during this visit. */
export function sendableStock(productId: number) {
	const have = useGameStore.getState().inventory[productId] ?? 0;
	const promised = socialStore.visit?.earned.sends.filter((item) => item.productId === productId).reduce((sum, item) => sum + item.qty, 0) ?? 0;
	return Math.max(0, have - promised);
}

// ------------------------------------------------------------------------------------------------------------ actions

export const socialActions = [
	"socialRefresh",
	"socialGiftAll",
	"socialOpenMail",
	"socialPickAvatar",
	"socialSaveProfile",
	"socialShowPhoto",
	"socialAddFriend",
	"socialAccept",
	"socialDecline",
	"socialRemove",
	"socialReport",
	"socialGift",
	"socialLike",
	"socialHelp",
	"socialVisit",
	"socialVisitPlayer",
	"socialLeave",
	"socialSend",
	"socialRequest",
	"socialCancelRequest",
	"socialRedeem",
	"socialShare",
	"socialCopy",
	"socialQr",
	"socialMock",
];
/** These may run while visiting (everything else waits for the player to come home). */
export const visitActions = ["socialGift", "socialLike", "socialHelp", "socialLeave", "socialSend", "socialRefresh"];

type Result = { ok: boolean; reason: string };
const done = (ok: boolean, reason = ""): Result => ({ ok, reason });

/** A social button: answered at once (the button's toast is silent); the outcome comes later as a social toast. */
export function requestSocialAction(action: string, args: unknown[]): Result {
	if (!socialActions.includes(action)) return done(false, "invalid-action");
	if (socialStore.visit && !visitActions.includes(action)) return done(false, "Volte ao seu mercado primeiro.");
	// A ranking player's market is only to look at (no like, gift, help or delivery).
	if (socialStore.visit?.viewOnly && action !== "socialLeave" && action !== "socialRefresh") return done(false, "Neste mercado você só pode olhar.");
	const online = socialOnline();
	const [a, b, c, d] = args;
	switch (action) {
		case "socialRefresh":
			void loadSocial(true);
			return done(true);
		case "socialPickAvatar":
			socialStore.draft.avatar = String(a ?? "");
			return done(true);
		case "socialQr":
			socialStore.showQr = !socialStore.showQr;
			return done(true);
		case "socialCopy": {
			const code = socialStore.me?.code;
			if (!code) return done(false, "Não foi possível agora.");
			send({ kind: "social-copy", text: formatCode(code) });
			toast(t("Código copiado!"), "share");
			return done(true);
		}
		case "socialShare": {
			const code = socialStore.me?.code;
			if (!code) return done(false, "Não foi possível agora.");
			const name = socialStore.me?.marketName || "";
			send({
				kind: "social-share",
				url: inviteUrl(code),
				code: formatCode(code),
				text: t(name ? "Vem jogar Checkout comigo! Meu mercado: {0}. Código de amigo: {1}" : "Vem jogar Checkout comigo! Código de amigo: {1}")
					.replaceAll("{0}", name)
					.replaceAll("{1}", formatCode(code)),
				// The postcard's lines, drawn by Unity over the picture of the market (never baked in an asset).
				name: name || t("Meu mercado"),
				caption: t("Vem jogar comigo!"),
				codeLabel: t("Código de amigo"),
				avatar: avatarIcon(socialStore.me?.avatar),
				stage: t(stageName(useGameStore.getState().era.id)),
			});
			return done(true);
		}
		case "socialMock": {
			if (!socialStore.mock) return done(false, "invalid-action");
			const ok = socialMock().control(String(a ?? ""), String(b ?? ""));
			// ("signed-out" on / off: the fake account signs out / in, like Unity's status after a login)
			syncSocialOnline();
			return done(ok, ok ? "" : "game-rule-rejected");
		}
	}
	if (!online) return done(false, "Entre na sua conta para jogar com amigos.");
	switch (action) {
		case "socialSaveProfile":
			return run("profile", () => saveProfile(String(a ?? ""), String(b ?? socialStore.draft.avatar)));
		case "socialShowPhoto":
			return run("photo", () => saveShowPhoto(a === true || a === "true"));
		case "socialAddFriend":
			return run("add", () => addFriend(String(a ?? "")));
		case "socialAccept":
			return run(`accept:${a}`, () => answerRequest(String(a ?? ""), true));
		case "socialDecline":
			return run(`decline:${a}`, () => answerRequest(String(a ?? ""), false));
		case "socialRemove":
			if (socialStore.confirmRemove !== String(a)) {
				socialStore.confirmRemove = String(a ?? "");
				return done(true);
			}
			return run(`remove:${a}`, () => removeFriend(String(a ?? "")));
		case "socialReport":
			return run(`report:${a}`, () => report(String(a ?? "")));
		case "socialGift":
			return run(`gift:${a}`, () => gift(String(a ?? "")));
		case "socialLike":
			return run(`like:${a}`, () => like(String(a ?? "")));
		case "socialHelp":
			return run(`help:${a}:${b}`, () => help(String(a ?? ""), String(b ?? "")));
		case "socialVisit":
			return run(`visit-start:${a}`, () => startVisit(String(a ?? "")).then((r) => r.ok));
		// "Visitar" on a Mundo / País row (Lucas 10/11): a friend opens as a friend, anyone else only to look.
		case "socialVisitPlayer":
			return run(`visit-start:${a}`, () => startVisit(String(a ?? ""), true).then((r) => r.ok));
		case "socialLeave":
			return done(endVisit());
		case "socialSend": {
			const productId = Number(c);
			const qty = Number(d);
			if (sendableStock(productId) < qty || !canSendProduct(useGameStore.getState(), productId, qty))
				return done(false, toastText("Você não tem {3}× {4} no estoque.", { qty, product: productName(productId) }));
			return run(`send:${a}`, () => sendProduct(Number(a), String(b ?? ""), productId, qty));
		}
		case "socialRequest": {
			const productId = Number(a);
			const qty = Math.max(SOCIAL_REQUEST_MIN, Math.min(SOCIAL_REQUEST_MAX, Math.floor(Number(b) || 0)));
			if (!itemCatalog.some((item) => item.id === productId)) return done(false, "game-rule-rejected");
			return run(`request:${productId}`, () => askFriends(productId, qty));
		}
		case "socialCancelRequest":
			return run(`cancel:${a}`, () => cancelRequest(Number(a)));
		case "socialRedeem":
			return run("redeem", () => redeem(String(a ?? "")));
		case "socialGiftAll":
			return run("gift-all", () => giftAll());
		case "socialOpenMail":
			return done(openMail(a === "all" || a === undefined ? "all" : [String(a)]));
	}
	return done(false, "invalid-action");
}

/** Runs one server action; its key keeps the button waiting until the answer. */
function run(key: string, work: () => Promise<unknown>): Result {
	if (socialStore.busy.has(key)) return done(false, "");
	socialStore.busy.add(key);
	work()
		.catch((error) => console.error(`CHECKOUT_SOCIAL ${key}: ${String(error)}`))
		.finally(() => {
			socialStore.busy.delete(key);
			refresh();
		});
	return done(true);
}

async function saveProfile(name: string, avatar: string) {
	const body: Record<string, unknown> = {};
	const trimmed = name.trim();
	// The same name again only when the server hid it (then it must be a new one: the server says so).
	if (trimmed && (trimmed !== (socialStore.me?.marketName ?? "") || socialStore.me?.nameHidden)) body.marketName = trimmed;
	if (avatar) body.avatar = avatar;
	if (avatar === (socialStore.me?.avatar ?? "")) delete body.avatar;
	if (!Object.keys(body).length) {
		toast(t("Perfil salvo!"), "success");
		return true;
	}
	const reply = await call("PUT", "/v1/social/me", body);
	if (reply.code !== 200) {
		toast(t(trouble(reply, { "name-not-allowed": "Esse nome não é permitido. Escolha outro.", "bad-avatar": "Escolha outro rosto." })), "warning", false);
		return false;
	}
	socialStore.me = reply.body as SocialMe;
	socialStore.draft = { avatar: socialStore.me.avatar ?? "", name: "" };
	if (!socialStore.visit)
		useGameStore.getState().rememberSocialProfile({ code: socialStore.me.code, marketName: socialStore.me.marketName, avatar: socialStore.me.avatar ?? "" });
	toast(t("Perfil salvo!"), "success");
	return true;
}

/** "Mostrar minha foto do Google para amigos" (PUT /v1/social/me {showPhoto}). */
async function saveShowPhoto(show: boolean) {
	const reply = await call("PUT", "/v1/social/me", { showPhoto: show });
	if (reply.code !== 200 || !reply.body) {
		toast(t(trouble(reply)), "warning", false);
		return false;
	}
	socialStore.me = reply.body as SocialMe;
	toast(t(show ? "Seus amigos veem a sua foto do Google." : "Seus amigos veem o seu rosto do jogo."), "success");
	return true;
}

async function addFriend(value: string) {
	const code = normalizeCode(value);
	if (!isCode(code)) {
		toast(t("O código tem 8 letras e números, como K7Q2-MX4P."), "warning", false);
		return false;
	}
	const reply = await call("POST", "/v1/social/friends/add", { code });
	if (reply.code !== 200) {
		toast(
			t(trouble(reply, { "not-found": "Código não encontrado.", self: "Esse é o seu próprio código.", "already-friends": "Vocês já são amigos.", limit: "Lista de amigos cheia, ou muitos pedidos esperando resposta." })),
			"warning",
			false,
		);
		return false;
	}
	if (socialStore.offeredCode === code) socialStore.offeredCode = "";
	toast(t(reply.body?.status === "friends" ? "Agora vocês são amigos!" : "Pedido de amizade enviado!"), "friends");
	await loadSocial(true);
	return true;
}

async function answerRequest(id: string, accept: boolean) {
	const reply = await call("POST", `/v1/social/friends/${accept ? "accept" : "decline"}`, { id });
	if (reply.code !== 200 && reply.code !== 204) {
		toast(t(trouble(reply, { "not-found": "Esse pedido de amizade não existe mais.", limit: "A lista de amigos está cheia." })), "warning", false);
		await loadSocial(true);
		return false;
	}
	if (accept) toast(t("Agora vocês são amigos!"), "friends");
	await loadSocial(true);
	return true;
}

async function removeFriend(id: string) {
	const reply = await call("DELETE", `/v1/social/friends/${encodeURIComponent(id)}`);
	socialStore.confirmRemove = "";
	if (reply.code !== 204 && reply.code !== 200) {
		toast(t(trouble(reply)), "warning", false);
		return false;
	}
	toast(t("Amigo removido."), "friends");
	await loadSocial(true);
	return true;
}

async function report(id: string) {
	const reply = await call("POST", "/v1/social/report", { id });
	if (reply.code !== 204 && reply.code !== 200) {
		toast(t(trouble(reply)), "warning", false);
		return false;
	}
	toast(t("Obrigado! Vamos verificar esse nome."), "success");
	return true;
}

async function gift(to: string) {
	const reply = await call("POST", "/v1/social/gift", { to });
	const friend = socialStore.friends.find((item) => item.id === to);
	if (reply.code !== 204 && reply.code !== 200) {
		if (errorOf(reply) === "already-today" && friend) friend.giftedToday = true;
		toast(t(trouble(reply, { "already-today": "Você já mandou um presente hoje. Volte amanhã!", "not-friends": "Vocês não são mais amigos." })), "warning", false);
		return false;
	}
	if (friend) friend.giftedToday = true;
	if (socialStore.visit?.friend.id === to) socialStore.visit.gifted = true;
	toast(toastText("Presente enviado para {0}!", { name: marketName(friend ?? socialStore.visit?.friend ?? { marketName: null, code: "" }) }), "gift");
	return true;
}

/** "Mandar presente para todos": one gift to every friend not gifted today, one after the other. */
async function giftAll() {
	const targets = socialStore.friends.filter((friend) => !friend.giftedToday);
	if (!targets.length) {
		toast(t("Você já mandou presente para todos hoje."), "gift");
		return false;
	}
	let sent = 0;
	for (const friend of targets) {
		const reply = await call("POST", "/v1/social/gift", { to: friend.id });
		if (reply.code === 204 || reply.code === 200 || errorOf(reply) === "already-today") friend.giftedToday = true;
		if (reply.code === 204 || reply.code === 200) sent++;
		else if (reply.network || reply.code === 0) break;
		refresh();
	}
	if (sent) fx("sparkle");
	toast(sent === 1 ? t("Presente enviado para 1 amigo!") : toastText("Presentes enviados para {3} amigos!", { qty: sent }), "gift", sent > 0);
	return sent > 0;
}

/** "Abrir" / "Abrir tudo" in the Correio: the boxes pay their coins (confetti, the coins fly to the counter). */
function openMail(ids: string[] | "all") {
	const opened = useGameStore.getState().openSocialMail(ids);
	if (!opened) return false;
	fx("confetti", opened.coins);
	toast(opened.count === 1 ? toastText("Você abriu um presente: +{1} moedas", { coins: opened.coins }) : toastText("Você abriu {3} presentes: +{1} moedas", { qty: opened.count, coins: opened.coins }), "gift");
	refresh();
	return true;
}

/** A little celebration in Unity: confetti (and coins flying to the counter), or a sparkle where the button was. */
function fx(kind: "confetti" | "sparkle", coins = 0) {
	send({ kind: "social-fx", fx: kind, coins });
}

async function like(to: string) {
	const reply = await call("POST", "/v1/social/like", { to });
	const friend = socialStore.friends.find((item) => item.id === to);
	if (reply.code !== 200) {
		if (errorOf(reply) === "already-today") {
			if (friend) friend.likedToday = true;
			if (socialStore.visit?.friend.id === to) socialStore.visit.liked = true;
		}
		toast(t(trouble(reply, { "already-today": "Você já curtiu esse mercado hoje.", "not-friends": "Vocês não são mais amigos." })), "warning", false);
		return false;
	}
	if (friend) {
		friend.likedToday = true;
		friend.likes = Number(reply.body?.likes) || friend.likes + 1;
	}
	const reward = getSocialRewards(useGameStore.getState().era.id).like;
	// The liker's coins: at once at home, booked on the way back from a visit (the save is frozen there).
	if (socialStore.visit?.friend.id === to) {
		socialStore.visit.liked = true;
		socialStore.visit.friend.likes = Number(reply.body?.likes) || socialStore.visit.friend.likes + 1;
		socialStore.visit.earned.likes++;
	} else useGameStore.getState().claimSocialHelperReward("like");
	fx("sparkle", reward);
	toast(toastText("Você curtiu o mercado: +{1} moedas", { coins: reward }), "like");
	return true;
}

async function help(to: string, buildId: string) {
	const reply = await call("POST", "/v1/social/help", { to, buildId });
	if (reply.code !== 200) {
		if (errorOf(reply) === "already-helped") {
			socialStore.helped.add(`${to}|${buildId}`);
			socialStore.visit?.helped.add(buildId);
		}
		toast(
			t(trouble(reply, {
				"already-helped": "Você já ajudou nesta obra.",
				"build-full": "Esta obra já recebeu muita ajuda.",
				"daily-limit": "Você já ajudou 30 vezes hoje. Volte amanhã!",
				"no-build": "Esta obra já terminou.",
				"not-friends": "Vocês não são mais amigos.",
			})),
			"warning",
			false,
		);
		return false;
	}
	socialStore.helped.add(`${to}|${buildId}`);
	const reward = getSocialRewards(useGameStore.getState().era.id).help;
	if (socialStore.visit?.friend.id === to) {
		socialStore.visit.helped.add(buildId);
		socialStore.visit.earned.helps++;
	} else useGameStore.getState().claimSocialHelperReward("help");
	fx("sparkle", reward);
	toast(toastText("Você ajudou na obra: −5 min para o amigo, +{1} moedas para você", { coins: reward }), "handshake");
	return true;
}

async function sendProduct(requestId: number, owner: string, productId: number, qty: number) {
	const reply = await call("POST", `/v1/social/requests/${requestId}/fulfill`);
	if (reply.code !== 204 && reply.code !== 200) {
		toast(t(trouble(reply, { taken: "Outro amigo já atendeu este pedido.", "not-found": "Este pedido não existe mais.", "not-friends": "Vocês não são mais amigos." })), "warning", false);
		await loadSocial(true);
		return false;
	}
	const strip = (list: SocialRequestView[]) => list.filter((item) => item.id !== requestId);
	socialStore.requests.friends = strip(socialStore.requests.friends);
	for (const friend of socialStore.friends) friend.openRequests = strip(friend.openRequests ?? []);
	let reward: number;
	if (socialStore.visit && socialStore.visit.friend.id === owner) {
		socialStore.visit.friend.openRequests = strip(socialStore.visit.friend.openRequests ?? []);
		socialStore.visit.earned.sends.push({ productId, qty });
		const product = itemCatalog.find((item) => item.id === productId);
		reward = product ? Math.max(1, Math.round(product.purchasePrice * qty * 1.25)) : 0;
	} else reward = useGameStore.getState().completeSocialDelivery(productId, qty) ?? 0;
	toast(toastText("Você mandou {3}× {4}: +{1} moedas", { qty, product: productName(productId), coins: reward }), "package");
	return true;
}

async function askFriends(productId: number, qty: number) {
	const reply = await call("POST", "/v1/social/requests", { productId: String(productId), qty });
	if (reply.code !== 200) {
		toast(t(trouble(reply, { limit: "Você já tem 2 pedidos abertos.", "bad-request": "Não foi possível agora." })), "warning", false);
		return false;
	}
	const created = requestOf(reply.body);
	socialStore.requests.mine = [...socialStore.requests.mine.filter((item) => item.id !== created.id), created];
	useGameStore.getState().rememberSocialRequests(socialStore.requests.mine);
	toast(toastText("Pedido enviado aos amigos: {3}× {4}", { qty, product: productName(productId) }), "package");
	return true;
}

async function cancelRequest(id: number) {
	const reply = await call("DELETE", `/v1/social/requests/${id}`);
	if (reply.code !== 204 && reply.code !== 200) {
		toast(t(trouble(reply)), "warning", false);
		return false;
	}
	socialStore.requests.mine = socialStore.requests.mine.filter((item) => item.id !== id);
	useGameStore.getState().rememberSocialRequests(socialStore.requests.mine);
	toast(t("Pedido cancelado."), "package");
	return true;
}

async function redeem(value: string) {
	const code = normalizeCode(value);
	if (!isCode(code)) {
		toast(t("O código tem 8 letras e números, como K7Q2-MX4P."), "warning", false);
		return false;
	}
	const reply = await call("POST", "/v1/social/invite/redeem", { code });
	if (reply.code !== 200) {
		toast(
			t(trouble(reply, {
				"not-found": "Código não encontrado.",
				self: "Esse código não vale para você.",
				"already-invited": "Você já usou um código de convite.",
				"too-late": "Códigos de convite valem nos primeiros 7 dias de jogo. Adicione como amigo!",
			})),
			"warning",
			false,
		);
		return false;
	}
	socialStore.offeredCode = "";
	// "invited": the invite counts, but one of the friend lists is full (no new friend).
	toast(
		t(reply.body?.status === "invited" ? "Convite aceito! Chegue ao Späti e os dois ganham 30 diamantes." : "Convite aceito! Vocês são amigos. Chegue ao Späti e os dois ganham 30 diamantes."),
		"invite",
	);
	await loadSocial(true);
	return true;
}

// ------------------------------------------------------------------------------------------------------------ views

/** Builds a friend has running that the player has not helped yet (badge on the friend's card). */
export function helpableBuilds(friend: SocialFriend, now = Date.now()) {
	return (friend.public?.builds ?? []).filter((build) => build.endsAt > now && !socialStore.helped.has(`${friend.id}|${build.id}`));
}

export type VisitBuildView = {
	buildId: string;
	/** "interior" | "evolution" | "era" | "lot" and the id Unity finds the site by (construction / evolution id, era, lot). */
	kind: string;
	targetId: string;
	label: string;
	helped: boolean;
	button: Button;
};
export type VisitView = {
	active: boolean;
	friendId: string;
	friendName: string;
	avatar: string;
	subtitle: string;
	note: string;
	buttons: Button[];
	builds: VisitBuildView[];
};

/** "1 curtida" / "12 curtidas" (translated). */
export const likesText = (likes: number) => (likes === 1 ? t("1 curtida") : t(`${fmt(likes)} curtidas`));

const buildLabel = (item: string, kind: string) => {
	if (kind === "era") return t("Obra da expansão");
	if (kind === "lot") return t("Limpeza do terreno");
	return kind === "evolution" ? t("Evolução") : t("Obra");
};

/** The top bar of a visit and the "Ajudar" button of each running build (Unity puts those over the sites). */
export function visitView(now = Date.now()): VisitView | null {
	const visit = socialStore.visit;
	if (!visit) return null;
	const friend = visit.friend;
	const requests = (friend.openRequests ?? []).filter((request) => request.expiresAt > now);
	const builds = (visit.public?.builds ?? []).filter((build) => build.endsAt > now);
	if (visit.viewOnly)
		return {
			active: true,
			friendId: friend.id,
			friendName: marketName(friend),
			avatar: avatarIcon(friend.avatar, null),
			subtitle: [t(`Nível ${friend.level ?? ""}`), t(stageName(friend.era ?? visit.state.era.id))].filter(Boolean).join(" · "),
			note: "Você está só olhando o mercado de um jogador do ranking.",
			buttons: [act("Voltar ao meu mercado", "socialLeave", [], { icon: socialIcon("market"), variant: "coin", ok: "" })],
			builds: [],
		};
	return {
		active: true,
		friendId: friend.id,
		friendName: marketName(friend),
		avatar: avatarIcon(friend.avatar, friend.photo),
		subtitle: [t(`Nível ${friend.level ?? ""}`), t(stageName(friend.era ?? visit.state.era.id)), likesText(friend.likes ?? 0)].filter(Boolean).join(" · "),
		note: builds.length ? "Toque em Ajudar nas obras do seu amigo: cada ajuda tira 5 minutos." : "Passeie pelo mercado do seu amigo.",
		buttons: [
			act(visit.liked ? "Curtido" : "Curtir", "socialLike", [friend.id], {
				icon: socialIcon("like"),
				variant: visit.liked ? "secondary" : "success",
				enabled: !visit.liked && !socialStore.busy.has(`like:${friend.id}`),
				ok: "",
				fail: "Você já curtiu esse mercado hoje.",
			}),
			act(visit.gifted ? "Enviado" : "Presente", "socialGift", [friend.id], {
				icon: socialIcon("gift"),
				variant: visit.gifted ? "secondary" : "success",
				enabled: !visit.gifted && !socialStore.busy.has(`gift:${friend.id}`),
				ok: "",
				fail: "Você já mandou um presente hoje. Volte amanhã!",
			}),
			button(requests.length ? `Pedidos (${requests.length})` : "Pedidos", { icon: socialIcon("package"), route: "!visita", variant: requests.length ? "primary" : "secondary", badge: requests.length ? String(requests.length) : "" }),
			act("Voltar ao meu mercado", "socialLeave", [], { icon: socialIcon("market"), variant: "coin", ok: "" }),
		],
		builds: builds.map((build) => {
			const [, ...rest] = build.id.split(":");
			const helped = visit.helped.has(build.id) || socialStore.helped.has(`${friend.id}|${build.id}`);
			const targetId = build.kind === "era" || build.kind === "lot" ? rest[0] : rest.join(":");
			return {
				buildId: build.id,
				kind: build.kind,
				targetId,
				label: buildLabel(build.item, build.kind),
				helped,
				button: act(helped ? "Ajudado" : "Ajudar", "socialHelp", [friend.id, build.id], {
					icon: socialIcon("handshake"),
					variant: helped ? "secondary" : "success",
					enabled: !helped && !socialStore.busy.has(`help:${friend.id}:${build.id}`),
					ok: "",
					fail: "Você já ajudou nesta obra.",
				}),
			};
		}),
	};
}

/** The red count on the Amigos button: inbox results not seen yet and gift boxes waiting in the Correio. */
export function socialBadge() {
	return socialStore.unseen + normalizeSocialState(useGameStore.getState().social).mailbox.length;
}

/** Helps given today, counting the ones of a visit still to be booked. */
export const socialHelpsToday = () => helpsToday(useGameStore.getState()) + (socialStore.visit?.earned.helps ?? 0);
