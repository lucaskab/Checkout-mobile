import type { MarketEraId } from "@/@types/economy";
import type { SocialPublicBlock } from "@/@types/social";
import { getUnlockedProductIds, itemCatalog } from "@/data/market-products";
import { ERA_LOTS } from "@/data/market-lots";
import { withCheckoutRegister } from "@/data/fixture-tiers";
import { ERA_BUILDING_EXPANSIONS } from "@/services/market-era";
import { useGameStore } from "@/stores/game-store";
import { createMockRankings } from "./rankings-mock";

// A stand-in for the social routes of docs/social-api.md, in this process, for the Editor's QA (the Worker is not
// deployed yet). Unity says "mock" in its `social` status message (Editor only) and desktop/social.ts then answers its
// calls here instead of sending them to Unity. Same answers, codes and limits as the contract; friends' saves are
// built from a new game (the player's own store is never read or written here).

export type MockReply = { code: number; body: unknown; network: boolean };
type Person = {
	id: string;
	code: string;
	marketName: string | null;
	avatar: string;
	level: number;
	era: MarketEraId;
	likes: number;
	lastSeen: number;
	createdAt: number;
	invitedBy: string | null;
	invitesRewarded: number;
	public: SocialPublicBlock | null;
	save: string;
};
type InboxRow = { id: number; to: string; kind: string; from: string | null; payload: Record<string, unknown>; createdAt: number; acked: boolean };
type RequestRow = { id: number; owner: string; productId: string; qty: number; status: "open" | "fulfilled" | "cancelled" | "expired"; createdAt: number; expiresAt: number };

const HOUR = 3_600_000;
const DAY = 24 * HOUR;
const utcDay = (now: number) => new Date(now).toISOString().slice(0, 10);
const reply = (code: number, body: unknown = null): MockReply => ({ code, body, network: false });
const fail = (code: number, error: string) => reply(code, { error });

/** A friend's save: a new game moved to `era` / `level`, painted, with running builds (what the visit shows). */
/**
 * A furnished Späti as the game itself laid it out (Unity's "eventssocialcapture" on the QA copy, 02/11): the shelves
 * on the shop floor, a shelf being built, plants inside and the bench, flowers, a tree and a lamp on the block. The
 * friend "Mercado da Ana" uses it, so a visit shows a real Späti (a stall keeps unplaced pieces in the inventory).
 */
export const SPATI_LAYOUT: { id: string; type: string; x: number; z: number; rot: number; outside?: boolean }[] = [{"id": "shelf:drinks", "type": "shelf", "x": -4.414, "z": -0.087, "rot": 270}, {"id": "shelf:produce", "type": "shelf", "x": -4.561, "z": -1.602, "rot": 0}, {"id": "shelf:bakery", "type": "shelf", "x": -5.408, "z": -1.602, "rot": 0}, {"id": "decor-1", "type": "plant-small", "x": -4.985, "z": -0.27, "rot": 0}, {"id": "decor-2", "type": "monstera", "x": -5.623, "z": -0.334, "rot": 0}, {"id": "decor-3", "type": "fruit-pyramid", "x": -5.408, "z": -4.267, "rot": 0}, {"id": "decor-4", "type": "flower-bed", "x": -9.21, "z": 4.223, "rot": 0, "outside": true}, {"id": "decor-5", "type": "park-bench", "x": -11.306, "z": 4.19, "rot": 0, "outside": true}, {"id": "decor-6", "type": "tree-planter", "x": -6.642, "z": 4.502, "rot": 0, "outside": true}, {"id": "decor-7", "type": "street-lamp", "x": -7.825, "z": 4.027, "rot": 0, "outside": true}, {"id": "decor-8", "type": "bike-rack", "x": -13.271, "z": 4.056, "rot": 0, "outside": true}];

export function createMockFriendSave(options: {
	era: MarketEraId;
	level: number;
	coins: number;
	paint?: { paletteId: string; primary: string; accent: string };
	builds?: { id: string; kind: "shelf" | "sector" | "shop"; targetId: string; minutesLeft: number }[];
	evolutions?: { id: string; kind: string; targetId: string; toTier: number; minutesLeft: number }[];
	/** Placed furniture and decorations (the decorations are owned once each). */
	interior?: typeof SPATI_LAYOUT;
	now: number;
}) {
	const store = useGameStore;
	const initial = store.getInitialState();
	const persisted = JSON.parse(JSON.stringify(store.persist.getOptions().partialize!(initial))) as Record<string, any>;
	const { era, level, now } = options;
	const lots = ERA_LOTS[era] ?? [];
	persisted.era = { ...persisted.era, id: era, construction: null };
	persisted.coins = options.coins;
	persisted.market = {
		...persisted.market,
		level,
		isOpen: false,
		unlockedProductIds: Array.from(new Set([...(persisted.market.unlockedProductIds ?? []), ...getUnlockedProductIds(level, era)])),
	};
	persisted.lots = { ...(persisted.lots ?? {}), owned: [...lots], cleared: [...lots], clearing: null };
	persisted.shop = { ...persisted.shop, ownedItemIds: withCheckoutRegister(persisted.shop?.ownedItemIds ?? [], era) };
	persisted.unlockedMarketExpansionIds = [...(ERA_BUILDING_EXPANSIONS[era] ?? [])];
	persisted.marketExpansionConstruction = null;
	if (options.paint) persisted.marketPaint = { ...persisted.marketPaint, ...options.paint };
	if (options.interior) {
		const owned: Record<string, number> = { ...(persisted.interior?.owned ?? {}) };
		for (const item of options.interior) if (item.id.startsWith("decor-")) owned[item.type] = (owned[item.type] ?? 0) + 1;
		persisted.interior = { ...(persisted.interior ?? {}), items: options.interior.map((item) => ({ ...item })), owned };
	}
	persisted.interiorConstructions = (options.builds ?? []).map((build) => ({
		id: build.id,
		kind: build.kind,
		targetId: build.targetId,
		startedAt: now - 10 * 60_000,
		endsAt: now + build.minutesLeft * 60_000,
		durationMs: (build.minutesLeft + 10) * 60_000,
	}));
	persisted.evolutions = (options.evolutions ?? []).map((item) => ({
		id: item.id,
		kind: item.kind,
		targetId: item.targetId,
		toTier: item.toTier,
		durationMs: (item.minutesLeft + 5) * 60_000,
		startedAt: now - 5 * 60_000,
		endsAt: now + item.minutesLeft * 60_000,
	}));
	return JSON.stringify({ state: persisted, version: store.persist.getOptions().version ?? 0 });
}

function publicOf(save: string, era: MarketEraId): SocialPublicBlock {
	const { state } = JSON.parse(save) as { state: { interiorConstructions: any[]; evolutions: any[] } };
	return {
		builds: [
			...state.interiorConstructions.map((item) => ({ id: `interior:${item.id}`, kind: "interior" as const, item: `${item.kind}-${item.targetId}`, tier: 0, endsAt: item.endsAt })),
			...state.evolutions.map((item) => ({ id: `evolution:${item.id}`, kind: "evolution" as const, item: `${item.kind}-${item.targetId}`, tier: item.toTier, endsAt: item.endsAt })),
		],
		stage: era,
		marketRating: 4.3,
	};
}

/**
 * The fake server. `me` is the QA player. Three friends (Ana at the Späti, Bruno at the banca, Carla at the tenda),
 * one incoming request (Duda) and a few unacked inbox items, so every screen has something on it the first time.
 */
export function createMockSocialServer(start = Date.now()) {
	let now = start;
	let nextInbox = 1;
	let nextRequest = 1;
	const people = new Map<string, Person>();
	const friends = new Set<string>();
	const friendRequests = new Set<string>();
	const inbox: InboxRow[] = [];
	const requests: RequestRow[] = [];
	const daily = new Set<string>();
	const helps = new Set<string>();
	const reports = new Set<string>();
	/** Calls answered so far (tests count them) and what a test wants to fail next. */
	const log: string[] = [];
	let failNext: { path: string; times: number } | null = null;

	const person = (id: string, code: string, marketName: string | null, avatar: string, era: MarketEraId, level: number, save = "") => {
		const value: Person = { id, code, marketName, avatar, level, era, likes: 0, lastSeen: now - HOUR, createdAt: now - 30 * DAY, invitedBy: null, invitesRewarded: 0, public: null, save };
		if (save) value.public = publicOf(save, era);
		people.set(id, value);
		return value;
	};
	const befriend = (a: string, b: string) => {
		friends.add(`${a}|${b}`);
		friends.add(`${b}|${a}`);
	};
	const areFriends = (a: string, b: string) => friends.has(`${a}|${b}`);
	const push = (to: string, kind: string, from: string | null, payload: Record<string, unknown> = {}) => {
		const row = { id: nextInbox++, to, kind, from, payload, createdAt: now, acked: false };
		inbox.push(row);
		return row;
	};

	const me = person("qa-player", "K7Q2MX4P", null, "", "mesinha", 1);
	me.createdAt = now - 2 * DAY;
	const ana = person(
		"u-ana",
		"ANA2BC3D",
		"Mercado da Ana",
		"shopper-3",
		"spati",
		9,
		createMockFriendSave({
			era: "spati",
			level: 9,
			coins: 4_200,
			paint: { paletteId: "floresta", primary: "1F4D36", accent: "E3C77A" },
			// a furnished Späti: the bakery shelf placed and being built, the produce shelf evolving (both with a
			// floating "Ajudar" in a visit), plants inside, a bench, flowers, a tree and a lamp outside
			builds: [{ id: "obra-shelf-bakery-ana", kind: "shelf", targetId: "bakery", minutesLeft: 25 }],
			interior: SPATI_LAYOUT,
			evolutions: [{ id: "evolucao-shelf-produce-2-ana", kind: "shelf", targetId: "produce", toTier: 2, minutesLeft: 42 }],
			now,
		}),
	);
	const bruno = person(
		"u-bruno",
		"BRU4N5PQ",
		"Banca do Bruno",
		"shopper-7",
		"banca",
		5,
		createMockFriendSave({
			era: "banca",
			level: 5,
			coins: 1_300,
			paint: { paletteId: "oceano", primary: "0F6A6E", accent: "F27D5E" },
			evolutions: [{ id: "evolucao-shelf-drinks-2-bruno", kind: "shelf", targetId: "drinks", toTier: 2, minutesLeft: 18 }],
			now,
		}),
	);
	// Gabi is far ahead (a supermercado on six lots with its wings): lots and wings the player has not got render
	// for the visit only and everything comes back on "Voltar".
	const gabi = person(
		"u-gabi",
		"GAB5R7TK",
		"Supermercado da Gabi",
		"shopper-6",
		"supermercado",
		30,
		createMockFriendSave({
			era: "supermercado",
			level: 30,
			coins: 48_000,
			paint: { paletteId: "oceano", primary: "0F6A6E", accent: "F27D5E" },
			builds: [{ id: "obra-shelf-snacks-gabi", kind: "shelf", targetId: "snacks", minutesLeft: 50 }],
			evolutions: [{ id: "evolucao-shelf-drinks-3-gabi", kind: "shelf", targetId: "drinks", toTier: 3, minutesLeft: 75 }],
			now,
		}),
	);
	const carla = person("u-carla", "CAR6M7XY", "Tenda da Carla", "shopper-5", "tenda", 3, createMockFriendSave({ era: "tenda", level: 3, coins: 600, now }));
	const duda = person("u-duda", "DUD8A9ZW", "Quitanda da Duda", "shopper-9", "banca", 6);
	person("u-eva", "EVA3V4RT", "Mercadinho da Eva", "shopper-2", "tenda", 2, createMockFriendSave({ era: "tenda", level: 2, coins: 300, now }));
	ana.likes = 12;
	bruno.likes = 4;
	carla.likes = 1;
	bruno.lastSeen = now - 5 * 60_000;
	carla.lastSeen = now - 3 * DAY;
	befriend(me.id, ana.id);
	befriend(me.id, bruno.id);
	befriend(me.id, carla.id);
	befriend(me.id, gabi.id);
	gabi.likes = 57;
	gabi.lastSeen = now - 20 * 60_000;
	friendRequests.add(`${duda.id}|${me.id}`);
	const apple = itemCatalog[0];
	requests.push({ id: nextRequest++, owner: ana.id, productId: String(apple.id), qty: 6, status: "open", createdAt: now - HOUR, expiresAt: now + 23 * HOUR });
	push(me.id, "gift", ana.id);
	push(me.id, "like", bruno.id);
	push(me.id, "friend_request", duda.id);
	// Items pushed from here on get ids no earlier Editor session used (a QA copy of the save remembers the ids it
	// applied, like the real app: a fresh "1, 2, 3…" would be acked unpaid as already seen).
	nextInbox = Math.max(nextInbox, 1000 + (Math.floor(Date.now() / 1000) % 1_000_000_000) * 100);

	// Rankings v1 (desktop/rankings-mock.ts): the boards and the league answer here too, with these friends in them.
	const rankings = createMockRankings({
		me: () => me,
		friendIds: () => [...people.values()].filter((p) => p.id !== me.id && areFriends(me.id, p.id)).map((p) => p.id),
		person: (id) => people.get(id),
		push: (to, kind, from, payload) => push(to, kind, from, payload),
		now: () => now,
	});
	const short = (p: Person) => ({ id: p.id, code: p.code, marketName: p.marketName, avatar: p.avatar || null });
	const brief = (p: Person) => ({ ...short(p), level: p.level, era: p.era });
	const open = (row: RequestRow) => row.status === "open" && row.expiresAt > now;
	const requestView = (row: RequestRow) => ({ id: row.id, productId: row.productId, qty: row.qty, createdAt: row.createdAt, expiresAt: row.expiresAt });
	const friendView = (p: Person) => ({
		...short(p),
		level: p.level,
		era: p.era,
		likes: p.likes,
		lastSeen: p.lastSeen,
		giftedToday: daily.has(`${me.id}|${utcDay(now)}|gift|${p.id}`),
		likedToday: daily.has(`${me.id}|${utcDay(now)}|like|${p.id}`),
		public: p.public,
		openRequests: requests.filter((row) => row.owner === p.id && open(row)).map(requestView),
	});
	let nameHidden = false;
	const profile = () => ({
		id: me.id,
		nameHidden,
		code: me.code,
		marketName: me.marketName,
		avatar: me.avatar || null,
		level: me.level,
		era: me.era,
		likes: me.likes,
		friends: [...friends].filter((pair) => pair.startsWith(`${me.id}|`)).length,
		invitedBy: me.invitedBy ? (people.get(me.invitedBy)?.code ?? null) : null,
		invites: { rewarded: me.invitesRewarded, milestones: [1, 3, 5] },
	});
	const byCode = (code: unknown) => [...people.values()].find((p) => p.code === String(code ?? "").toUpperCase().replace(/[^0-9A-Z]/g, ""));
	const once = (kind: string, target: string) => {
		const key = `${me.id}|${utcDay(now)}|${kind}|${target}`;
		if (daily.has(key)) return false;
		daily.add(key);
		return true;
	};
	const helpsToday = () => [...daily].filter((key) => key.startsWith(`${me.id}|${utcDay(now)}|help|`)).length;

	function route(method: string, path: string, body: Record<string, any>): MockReply {
		const parts = path.replace(/^\/v1\/social\/?/, "").split("/").filter(Boolean);
		const [head, second, third] = parts;
		if (method === "GET" && head === "me") return reply(200, profile());
		if (method === "PUT" && head === "me") {
			// marketName null = unchanged; the same name in another spelling is not a change (400).
			if (body.marketName !== undefined && body.marketName !== null) {
				const name = String(body.marketName).trim();
				const plain = (text: string) => text.normalize("NFD").replace(/\p{M}/gu, "").replace(/\s+/g, "").toLowerCase();
				if (name.length < 3 || name.length > 20 || !/^[\p{L}\p{N} '&.\-]+$/u.test(name) || /\bbobo\b/i.test(name)) return fail(400, "name-not-allowed");
				if (me.marketName && plain(me.marketName) === plain(name)) return fail(400, "name-not-allowed");
				me.marketName = name;
				nameHidden = false;
			}
			if (body.avatar !== undefined) {
				if (body.avatar !== null && !/^[A-Za-z0-9_-]{1,32}$/.test(String(body.avatar))) return fail(400, "bad-avatar");
				me.avatar = body.avatar ?? "";
			}
			return reply(200, profile());
		}
		if (method === "GET" && head === "friends" && !second)
			return reply(200, {
				friends: [...people.values()].filter((p) => areFriends(me.id, p.id)).map(friendView),
				incoming: [...friendRequests].filter((pair) => pair.endsWith(`|${me.id}`)).map((pair) => brief(people.get(pair.split("|")[0])!)),
				outgoing: [...friendRequests].filter((pair) => pair.startsWith(`${me.id}|`)).map((pair) => brief(people.get(pair.split("|")[1])!)),
			});
		if (method === "POST" && head === "friends" && second === "add") {
			const other = byCode(body.code);
			if (!other) return fail(404, "not-found");
			if (other.id === me.id) return fail(409, "self");
			if (areFriends(me.id, other.id)) return fail(409, "already-friends");
			// They had asked first: friends at once.
			if (friendRequests.delete(`${other.id}|${me.id}`)) {
				befriend(me.id, other.id);
				return reply(200, { status: "friends" });
			}
			friendRequests.add(`${me.id}|${other.id}`);
			return reply(200, { status: "requested" });
		}
		if (method === "POST" && head === "friends" && second === "accept") {
			if (!friendRequests.delete(`${body.id}|${me.id}`)) return fail(404, "not-found");
			befriend(me.id, String(body.id));
			return reply(200, { status: "friends" });
		}
		if (method === "POST" && head === "friends" && second === "decline") {
			friendRequests.delete(`${body.id}|${me.id}`);
			return reply(204);
		}
		if (method === "DELETE" && head === "friends" && second) {
			friends.delete(`${me.id}|${second}`);
			friends.delete(`${second}|${me.id}`);
			return reply(204);
		}
		if (method === "POST" && head === "report") {
			if (!people.has(String(body.id))) return fail(404, "not-found");
			reports.add(String(body.id));
			return reply(204);
		}
		if (method === "GET" && head === "friends" && second && third === "market") {
			const other = people.get(second);
			if (!other || !areFriends(me.id, other.id)) return fail(403, "not-friends");
			if (!other.save) return fail(404, "no-save");
			return reply(200, { profile: friendView(other), public: other.public, data: other.save });
		}
		if (method === "POST" && head === "gift") {
			if (!areFriends(me.id, String(body.to))) return fail(403, "not-friends");
			if (!once("gift", String(body.to))) return fail(409, "already-today");
			push(String(body.to), "gift", me.id);
			return reply(204);
		}
		if (method === "POST" && head === "like") {
			const other = people.get(String(body.to));
			if (!other || !areFriends(me.id, other.id)) return fail(403, "not-friends");
			if (!once("like", other.id)) return fail(409, "already-today");
			other.likes++;
			push(other.id, "like", me.id);
			return reply(200, { likes: other.likes });
		}
		if (method === "POST" && head === "help") {
			const other = people.get(String(body.to));
			if (!other || !areFriends(me.id, other.id)) return fail(403, "not-friends");
			const build = other.public?.builds.find((item) => item.id === body.buildId && item.endsAt > now);
			if (!build) return fail(404, "no-build");
			const key = `${other.id}|${build.id}`;
			if (helps.has(`${key}|${me.id}`)) return fail(409, "already-helped");
			const count = [...helps].filter((item) => item.startsWith(`${key}|`)).length;
			if (count >= 10) return fail(409, "build-full");
			if (helpsToday() >= 30) return fail(429, "daily-limit");
			helps.add(`${key}|${me.id}`);
			daily.add(`${me.id}|${utcDay(now)}|help|${key}`);
			push(other.id, "help", me.id, { buildId: build.id, minutes: 5 });
			return reply(200, { helps: count + 1 });
		}
		if (method === "GET" && head === "requests" && !second)
			return reply(200, {
				mine: requests.filter((row) => row.owner === me.id && open(row)).map(requestView),
				friends: requests.filter((row) => row.owner !== me.id && open(row) && areFriends(me.id, row.owner)).map((row) => ({ ...requestView(row), owner: row.owner })),
			});
		if (method === "POST" && head === "requests" && !second) {
			// Like the Worker: the product id is text (1–64 of A-Z a-z 0-9 _ . : -), qty an integer 1–20.
			const productId = body.productId;
			const qty = body.qty;
			if (typeof productId !== "string" || !/^[A-Za-z0-9_.:-]{1,64}$/.test(productId) || !Number.isInteger(qty) || qty < 1 || qty > 20) return fail(400, "bad-request");
			if (requests.filter((row) => row.owner === me.id && open(row)).length >= 2) return fail(429, "limit");
			const row: RequestRow = { id: nextRequest++, owner: me.id, productId, qty, status: "open", createdAt: now, expiresAt: now + DAY };
			requests.push(row);
			return reply(200, requestView(row));
		}
		if (method === "DELETE" && head === "requests" && second) {
			const row = requests.find((item) => item.id === Number(second) && item.owner === me.id && open(item));
			if (!row) return fail(404, "not-found");
			row.status = "cancelled";
			return reply(204);
		}
		if (method === "POST" && head === "requests" && second && third === "fulfill") {
			const row = requests.find((item) => item.id === Number(second));
			if (!row) return fail(404, "not-found");
			if (!open(row)) return fail(409, "taken");
			if (row.owner === me.id || !areFriends(me.id, row.owner)) return fail(403, "not-friends");
			row.status = "fulfilled";
			push(row.owner, "delivery", me.id, { requestId: row.id, productId: row.productId, qty: row.qty });
			push(row.owner, "request_fulfilled", me.id, { requestId: row.id });
			return reply(204);
		}
		if (method === "GET" && head === "inbox")
			return reply(200, {
				items: inbox
					.filter((row) => row.to === me.id && !row.acked)
					.slice(0, 100)
					.map((row) => ({ id: row.id, kind: row.kind, from: row.from ? short(people.get(row.from)!) : null, payload: row.payload, createdAt: row.createdAt })),
			});
		if (method === "POST" && head === "inbox" && second === "ack") {
			if (!Array.isArray(body.ids) || body.ids.length > 300) return fail(400, "bad-request");
			const ids = new Set(body.ids.map(Number));
			for (const row of inbox) if (row.to === me.id && ids.has(row.id)) row.acked = true;
			return reply(204);
		}
		if (method === "POST" && head === "invite" && second === "redeem") {
			const other = byCode(body.code);
			if (!other) return fail(404, "not-found");
			if (other.id === me.id) return fail(409, "self");
			if (me.invitedBy) return fail(409, "already-invited");
			if (now - me.createdAt > 7 * DAY) return fail(409, "too-late");
			me.invitedBy = other.id;
			befriend(me.id, other.id);
			// friend_added goes to the one who did not act (the inviter), never to me.
			push(other.id, "friend_added", me.id, { via: "invite" });
			return reply(200, { status: "friends" });
		}
		return fail(404, "no-route");
	}

	return {
		me,
		rankings,
		log,
		inbox,
		requests,
		/** Answers one call of the game (path with its query). */
		call(method: string, path: string, body?: unknown): MockReply {
			log.push(`${method} ${path}`);
			if (failNext && path.startsWith(failNext.path) && failNext.times > 0) {
				failNext.times--;
				return { code: 0, body: null, network: true };
			}
			const parsed = typeof body === "string" && body ? JSON.parse(body) : ((body as Record<string, unknown>) ?? {});
			if (path.startsWith("/v1/rankings")) return rankings.call(method, path, parsed);
			return route(method.toUpperCase(), path.split("?")[0], parsed);
		},
		/** QA controls (dev page / Unity autotests): what friends do while the player plays. */
		control(command: string, arg = ""): boolean {
			if (command === "time") {
				now += Number(arg) || 0;
				return true;
			}
			if (command === "fail") {
				failNext = { path: arg, times: 1 };
				return true;
			}
			if (command === "gift") return Boolean(push(me.id, "gift", arg || ana.id));
			if (command === "like") return Boolean(push(me.id, "like", arg || bruno.id));
			if (command === "help") {
				const [buildId, from] = arg.split(",");
				return Boolean(buildId && push(me.id, "help", from || carla.id, { buildId, minutes: 5 }));
			}
			if (command === "deliver") {
				const row = requests.find((item) => item.owner === me.id && open(item));
				if (!row) return false;
				row.status = "fulfilled";
				push(me.id, "delivery", ana.id, { requestId: row.id, productId: row.productId, qty: row.qty });
				push(me.id, "request_fulfilled", ana.id, { requestId: row.id });
				return true;
			}
			if (command === "invite-reward") {
				// Eva joined with the player's code and reached the Späti: 30 diamonds and, at 1 / 3 / 5, a decoration.
				me.invitesRewarded++;
				const milestone = [1, 3, 5].includes(me.invitesRewarded) ? me.invitesRewarded : undefined;
				return Boolean(push(me.id, "invite_reward", "u-eva", { diamonds: 30, role: "inviter", ...(milestone ? { milestone } : {}) }));
			}
			if (command === "hide-name") {
				nameHidden = true;
				return true;
			}
			if (command === "accepted") {
				// Eva accepted the player's request: friend_added to the player (who asked).
				const eva = people.get("u-eva")!;
				friendRequests.delete(`${me.id}|${eva.id}`);
				befriend(me.id, eva.id);
				return Boolean(push(me.id, "friend_added", eva.id, { via: "code" }));
			}
			if (command === "solo") {
				// QA: the player without friends (the Amigos window's empty state).
				for (const key of [...friends]) if (key.startsWith(`${me.id}|`) || key.endsWith(`|${me.id}`)) friends.delete(key);
				for (const key of [...friendRequests]) if (key.includes(me.id)) friendRequests.delete(key);
				return true;
			}
			if (command === "request") {
				// Duda asks to be friends again (after a decline): the badge test.
				friendRequests.add(`${duda.id}|${me.id}`);
				return Boolean(push(me.id, "friend_request", duda.id));
			}
			return rankings.control(command, arg);
		},
		set clock(value: number) {
			now = value;
		},
		get clock() {
			return now;
		},
	};
}

export type MockSocialServer = ReturnType<typeof createMockSocialServer>;
