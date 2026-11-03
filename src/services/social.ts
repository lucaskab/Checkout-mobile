import type { GameState } from "@/@types/game";
import type {
	SocialInboxItem,
	SocialInboxOutcome,
	SocialPublicBlock,
	SocialPublicBuild,
	SocialLogEntry,
	SocialMail,
	SocialRequestMirror,
	SocialState,
} from "@/@types/social";
import { getMarketEra } from "@/data/economy";
import { scheduleEvolutions } from "@/data/fixture-evolution";
import { constructionDuration, scheduleInteriorConstructions } from "@/data/interior-construction";
import { itemCatalog } from "@/data/market-products";
import {
	getDeliveryReward,
	getSocialRewards,
	inviteRewardDecorId,
	SOCIAL_APPLIED_KEEP,
	SOCIAL_GIFTS_PER_DAY,
	SOCIAL_HELP_MINUTES,
	SOCIAL_HISTORY_KEEP,
	SOCIAL_INVITE_DIAMONDS_MAX,
	SOCIAL_MAILBOX_KEEP,
	SOCIAL_INVITE_MILESTONES,
	SOCIAL_PUBLIC_BUILDS,
	SOCIAL_REQUEST_MAX,
	SOCIAL_REQUEST_MIN,
} from "@/data/social";
import { isLeagueDivision, LEAGUE_CHEST_GIFTS, LEAGUE_REWARD_DIAMONDS_MAX, RANKING_CARDS_KEEP, RANKING_WEEKS_KEEP } from "@/data/rankings";
import { normalizeRankingsState } from "@/services/rankings";
import { appendInventoryLots, createInventoryLots, reconcileInventoryLots, takeInventoryLots } from "@/services/inventory-lots";

// Social v1 on the player's own save (docs/social-api.md). Everything here is pure: the store applies the patches.
// The inbox is at-least-once and applied exactly once: an id in `social.appliedInbox` is acked without paying again.

const MINUTE = 60_000;

export function createSocialState(): SocialState {
	return {
		appliedInbox: [],
		gifts: { day: "", claimed: 0 },
		profile: { code: "", marketName: "", avatar: "" },
		requests: [],
		invites: { milestones: [], invited: false },
		totals: { gifts: 0, likes: 0, helpsReceived: 0, helpsGiven: 0, deliveries: 0, sent: 0 },
		mailbox: [],
		history: [],
		daily: { day: "", helps: 0 },
	};
}

const num = (value: unknown, fallback = 0) => (typeof value === "number" && Number.isFinite(value) ? value : fallback);
const str = (value: unknown) => (typeof value === "string" ? value : "");
/** Product ids travel as text on the server ("47", docs/social-api.md); the game's catalog ids are numbers. */
export const productIdOf = (value: unknown) => (typeof value === "string" && /^\d+$/.test(value.trim()) ? Number(value) : num(value, NaN));

function normalizeRequest(value: unknown): SocialRequestMirror | null {
	const item = value as Partial<SocialRequestMirror> | null;
	if (!item || typeof item !== "object") return null;
	const id = num(item.id, NaN);
	const productId = productIdOf(item.productId);
	if (!Number.isFinite(id) || !Number.isFinite(productId)) return null;
	return { id, productId, qty: Math.max(1, Math.floor(num(item.qty, 1))), createdAt: num(item.createdAt), expiresAt: num(item.expiresAt) };
}

function normalizeMail(value: unknown): SocialMail | null {
	const item = value as Partial<SocialMail> | null;
	if (!item || typeof item !== "object" || (typeof item.id !== "string" && typeof item.id !== "number")) return null;
	return { id: String(item.id), kind: "gift", name: str(item.name), avatar: str(item.avatar), coins: Math.max(0, Math.floor(num(item.coins))), at: num(item.at) };
}

function normalizeLog(value: unknown): SocialLogEntry | null {
	const item = value as Partial<SocialLogEntry> | null;
	if (!item || typeof item !== "object" || !str(item.text)) return null;
	return {
		kind: str(item.kind),
		text: str(item.text),
		icon: str(item.icon),
		name: str(item.name),
		avatar: str(item.avatar),
		coins: num(item.coins),
		diamonds: num(item.diamonds),
		minutes: num(item.minutes),
		productId: num(item.productId),
		qty: num(item.qty),
		at: num(item.at),
	};
}

/** Old saves (no `social`) and anything odd in the field: a clean slice, keeping whatever is valid. */
export function normalizeSocialState(value: unknown): SocialState {
	const base = createSocialState();
	const state = value as Partial<SocialState> | null | undefined;
	if (!state || typeof state !== "object") return base;
	const totals = (state.totals ?? {}) as Partial<SocialState["totals"]>;
	return {
		appliedInbox: Array.isArray(state.appliedInbox)
			? state.appliedInbox.filter((id) => typeof id === "string" || typeof id === "number").map(String).slice(-SOCIAL_APPLIED_KEEP)
			: [],
		gifts: { day: str(state.gifts?.day), claimed: Math.max(0, Math.floor(num(state.gifts?.claimed))) },
		profile: { code: str(state.profile?.code), marketName: str(state.profile?.marketName), avatar: str(state.profile?.avatar) },
		requests: Array.isArray(state.requests) ? state.requests.map(normalizeRequest).filter((item): item is SocialRequestMirror => !!item) : [],
		invites: {
			milestones: Array.isArray(state.invites?.milestones)
				? state.invites.milestones.filter((m): m is number => SOCIAL_INVITE_MILESTONES.includes(m as 1 | 3 | 5))
				: [],
			invited: state.invites?.invited === true,
		},
		totals: {
			gifts: Math.max(0, num(totals.gifts)),
			likes: Math.max(0, num(totals.likes)),
			helpsReceived: Math.max(0, num(totals.helpsReceived)),
			helpsGiven: Math.max(0, num(totals.helpsGiven)),
			deliveries: Math.max(0, num(totals.deliveries)),
			sent: Math.max(0, num(totals.sent)),
		},
		mailbox: Array.isArray(state.mailbox) ? state.mailbox.map(normalizeMail).filter((item): item is SocialMail => !!item).slice(-SOCIAL_MAILBOX_KEEP) : [],
		history: Array.isArray(state.history) ? state.history.map(normalizeLog).filter((item): item is SocialLogEntry => !!item).slice(0, SOCIAL_HISTORY_KEEP) : [],
		daily: { day: str(state.daily?.day), helps: Math.max(0, Math.floor(num(state.daily?.helps))) },
	};
}

/** The server counts days in UTC. */
export const utcDay = (now: number) => new Date(now).toISOString().slice(0, 10);

// ---------------------------------------------------------------------------------------------------------------- builds

type BuildState = Pick<GameState, "interiorConstructions" | "evolutions" | "era" | "lots">;

/** The builds running or queued, as the public block lists them (oldest end first). */
export function getSocialBuilds(state: BuildState, now = Date.now()): SocialPublicBuild[] {
	const builds: SocialPublicBuild[] = [];
	// Ids are unique per build instance (the server counts helps per owner and id for 30 days): the stage works and the
	// lot clearing carry their start time; interior builds and evolutions already have one in their own ids.
	if (state.era?.construction && state.era.construction.endsAt > now)
		builds.push({
			id: `era:${state.era.construction.eraId}:${state.era.construction.startedAt}`,
			kind: "era",
			item: state.era.construction.eraId,
			tier: getMarketEra(state.era.construction.eraId).index,
			endsAt: state.era.construction.endsAt,
		});
	if (state.lots?.clearing && state.lots.clearing.endsAt > now)
		builds.push({
			id: `lot:${state.lots.clearing.lotId}:${state.lots.clearing.startedAt}`,
			kind: "lot",
			item: state.lots.clearing.lotId,
			tier: 0,
			endsAt: state.lots.clearing.endsAt,
		});
	for (const item of state.interiorConstructions ?? [])
		if (!item.pending && item.endsAt > now)
			builds.push({ id: `interior:${item.id}`, kind: "interior", item: `${item.kind}-${item.targetId}`, tier: 0, endsAt: item.endsAt });
	for (const item of state.evolutions ?? [])
		if (item.endsAt > now)
			builds.push({ id: `evolution:${item.id}`, kind: "evolution", item: `${item.kind}-${item.targetId}`, tier: item.toTier, endsAt: item.endsAt });
	return builds.sort((a, b) => a.endsAt - b.endsAt).slice(0, SOCIAL_PUBLIC_BUILDS);
}

/** The public block sent with every cloud save: running builds, the stage and the market's rating (0–5). */
export function computePublicBlock(state: BuildState & Pick<GameState, "market">, now = Date.now()): SocialPublicBlock {
	const satisfaction = num(state.market?.customerSatisfaction, 50);
	return {
		builds: getSocialBuilds(state, now),
		stage: state.era?.id ?? "mesinha",
		marketRating: Math.round(Math.max(0, Math.min(100, satisfaction)) / 2) / 10,
	};
}

/**
 * A friend's help on one of the player's builds: `minutes` off, never ending before now. Queued works give up part of
 * their own working time (the ones after them start earlier too). Null when the build is no longer there.
 */
export function applyBuildHelp(state: BuildState, buildId: string, minutes: number, now = Date.now()): Partial<GameState> | null {
	const [kind, ...rest] = buildId.split(":");
	const target = rest.join(":");
	const ms = Math.max(0, minutes) * MINUTE;
	if (!target || ms <= 0) return null;
	// "era:<eraId>:<startedAt>" / "lot:<lotId>:<startedAt>": a later build in the same place is another build.
	const [place, started] = rest;
	const sameStart = (startedAt: number) => started === undefined || Number(started) === startedAt;
	if (kind === "era") {
		const works = state.era?.construction;
		if (!works || works.eraId !== place || !sameStart(works.startedAt) || works.endsAt <= now) return null;
		return { era: { ...state.era, construction: { ...works, endsAt: Math.max(now, works.endsAt - ms) } } };
	}
	if (kind === "lot") {
		const clearing = state.lots?.clearing;
		if (!clearing || clearing.lotId !== place || !sameStart(clearing.startedAt) || clearing.endsAt <= now) return null;
		return { lots: { ...state.lots, clearing: { ...clearing, endsAt: Math.max(now, clearing.endsAt - ms) } } };
	}
	if (kind === "interior") {
		const item = state.interiorConstructions.find((entry) => entry.id === target);
		if (!item || item.pending || item.endsAt <= now) return null;
		const running = item.startedAt <= now;
		const next = state.interiorConstructions.map((entry) =>
			entry.id !== target
				? entry
				: running
					? { ...entry, endsAt: Math.max(now, entry.endsAt - ms) }
					: { ...entry, durationMs: Math.max(0, constructionDuration(entry) - ms) },
		);
		return { interiorConstructions: scheduleInteriorConstructions(next, now) };
	}
	if (kind === "evolution") {
		const item = state.evolutions.find((entry) => entry.id === target);
		if (!item || item.endsAt <= now) return null;
		const running = item.startedAt <= now;
		const next = state.evolutions.map((entry) =>
			entry.id !== target
				? entry
				: running
					? { ...entry, endsAt: Math.max(now, entry.endsAt - ms) }
					: { ...entry, durationMs: Math.max(0, entry.durationMs - ms), endsAt: entry.startedAt + Math.max(0, entry.durationMs - ms) },
		);
		return { evolutions: scheduleEvolutions(next, now) };
	}
	return null;
}

// ----------------------------------------------------------------------------------------------------------------- inbox

const outcome = (id: string, kind: string, fields: Partial<SocialInboxOutcome> = {}): SocialInboxOutcome => ({
	id,
	kind,
	applied: false,
	ack: true,
	text: "",
	icon: "",
	name: "",
	coins: 0,
	diamonds: 0,
	minutes: 0,
	productId: 0,
	qty: 0,
	...fields,
});

/** The friend's name as the toasts show it (the server hides a reported name: "Mercado #<code>"). */
export function senderName(item: Pick<SocialInboxItem, "from">) {
	const from = item.from;
	if (!from) return "";
	const name = typeof from.marketName === "string" ? from.marketName.trim() : "";
	return name || (from.code ? `#${from.code}` : "");
}

type InboxState = Pick<
	GameState,
	"social" | "coins" | "logistics" | "era" | "inventory" | "inventoryLots" | "interior" | "interiorConstructions" | "evolutions" | "lots"
> &
	Partial<Pick<GameState, "rankings">>;

/**
 * Applies the inbox items to the save, oldest first, each one exactly once. Returns the patch for the store, what each
 * item did (toasts) and the ids the game may ack once the save is written.
 */
export function applyInboxItems(state: InboxState, items: readonly unknown[], now = Date.now()) {
	let social = normalizeSocialState(state.social);
	let coins = state.coins;
	let diamonds = state.logistics.premiumCurrency;
	let inventory = state.inventory;
	let inventoryLots = state.inventoryLots;
	let interior = state.interior;
	let builds: BuildState = { interiorConstructions: state.interiorConstructions, evolutions: state.evolutions, era: state.era, lots: state.lots };
	const rewards = getSocialRewards(state.era.id);
	const outcomes: SocialInboxOutcome[] = [];
	const seen = new Set(social.appliedInbox);
	const applied: string[] = [];
	const today = utcDay(now);
	if (social.gifts.day !== today) social = { ...social, gifts: { day: today, claimed: 0 } };
	const totals = { ...social.totals };
	let invites = social.invites;
	let requests = social.requests;
	let rankings = normalizeRankingsState(state.rankings, now);
	let rankingsChanged = false;
	let changed = false;
	const log: SocialLogEntry[] = [];

	for (const raw of items) {
		const item = raw as SocialInboxItem;
		if (!item || typeof item !== "object" || (typeof item.id !== "number" && typeof item.id !== "string")) continue;
		const id = String(item.id);
		const kind = typeof item.kind === "string" ? item.kind : "";
		const name = senderName(item);
		const payload = item.payload && typeof item.payload === "object" ? item.payload : {};
		// Already in this save (a crash came between the save and the ack): ack it, never pay twice.
		if (seen.has(id)) {
			outcomes.push(outcome(id, kind, { name }));
			continue;
		}
		let result: SocialInboxOutcome;
		switch (kind) {
			case "gift": {
				// Over today's cap: it waits on the server (not acked, not remembered).
				if (social.gifts.claimed >= SOCIAL_GIFTS_PER_DAY) {
					outcomes.push(outcome(id, kind, { ack: false, name }));
					continue;
				}
				// Into the Correio as a box ("Abrir" pays it): applied exactly once like every item.
				social = {
					...social,
					gifts: { day: today, claimed: social.gifts.claimed + 1 },
					mailbox: [...social.mailbox, { id, kind: "gift" as const, name, avatar: str(item.from?.avatar), coins: rewards.gift, at: now }].slice(-SOCIAL_MAILBOX_KEEP),
				};
				totals.gifts++;
				result = outcome(id, kind, { applied: true, name, coins: rewards.gift, icon: "gift", text: name ? "{0} te mandou um presente: abra no Correio" : "Chegou um presente: abra no Correio" });
				break;
			}
			case "like": {
				coins += rewards.like;
				totals.likes++;
				result = outcome(id, kind, { applied: true, name, coins: rewards.like, icon: "heart", text: name ? "{0} curtiu seu mercado: +{1} moedas" : "Curtiram seu mercado: +{1} moedas" });
				break;
			}
			case "help": {
				const buildId = str(payload.buildId);
				const minutes = Math.max(0, Math.min(60, num(payload.minutes, SOCIAL_HELP_MINUTES)));
				const patch = buildId ? applyBuildHelp(builds, buildId, minutes, now) : null;
				totals.helpsReceived++;
				if (patch) {
					builds = { ...builds, ...patch };
					result = outcome(id, kind, { applied: true, name, minutes, icon: "construction", text: name ? "{0} te ajudou na obra: −{2} min" : "Um amigo te ajudou na obra: −{2} min" });
				} else {
					// The build had already finished: a thank-you instead.
					coins += rewards.thanks;
					result = outcome(id, kind, { applied: true, name, coins: rewards.thanks, icon: "construction", text: name ? "{0} veio ajudar na obra (já pronta): +{1} moedas" : "Um amigo veio ajudar na obra (já pronta): +{1} moedas" });
				}
				break;
			}
			case "delivery": {
				const productId = Math.floor(productIdOf(payload.productId));
				const product = itemCatalog.find((entry) => entry.id === productId);
				const qty = Math.max(SOCIAL_REQUEST_MIN, Math.min(SOCIAL_REQUEST_MAX, Math.floor(num(payload.qty, 1))));
				if (!product) {
					result = outcome(id, kind, { name });
					break;
				}
				// Into the stock room, even past its room (the friend sent it: nothing is lost).
				const have = num(inventory[productId]);
				inventory = { ...inventory, [productId]: have + qty };
				inventoryLots = {
					...inventoryLots,
					[productId]: appendInventoryLots(reconcileInventoryLots(productId, have, inventoryLots[productId], now), createInventoryLots(productId, qty, now)),
				};
				const requestId = num(payload.requestId, NaN);
				requests = requests.filter((request) => request.id !== requestId);
				totals.deliveries++;
				result = outcome(id, kind, { applied: true, name, productId, qty, icon: "truck", text: name ? "{0} te mandou {3}× {4}" : "Chegaram {3}× {4} de um amigo" });
				break;
			}
			case "invite_reward": {
				const amount = Math.max(0, Math.min(SOCIAL_INVITE_DIAMONDS_MAX, Math.floor(num(payload.diamonds, 30))));
				diamonds += amount;
				const role = payload.role === "invited" ? "invited" : "inviter";
				if (role === "invited") invites = { ...invites, invited: true };
				const milestone = num(payload.milestone, 0);
				let decor = "";
				if (SOCIAL_INVITE_MILESTONES.includes(milestone as 1 | 3 | 5) && !invites.milestones.includes(milestone)) {
					invites = { ...invites, milestones: [...invites.milestones, milestone].sort((a, b) => a - b) };
					decor = inviteRewardDecorId(milestone);
					interior = { ...interior, owned: { ...interior.owned, [decor]: (interior.owned[decor] ?? 0) + 1 } };
				}
				result = outcome(id, kind, {
					applied: true,
					name,
					diamonds: amount,
					icon: "diamond",
					text: decor
						? "Convite premiado: +{5} diamantes e uma decoração exclusiva!"
						: role === "invited"
							? "Prêmio do convite: +{5} diamantes"
							: name
								? "{0} chegou ao Späti com o seu convite: +{5} diamantes"
								: "Convite premiado: +{5} diamantes",
				});
				break;
			}
			case "friend_request":
				result = outcome(id, kind, { applied: true, name, icon: "customers", text: name ? "{0} quer ser seu amigo" : "Novo pedido de amizade" });
				break;
			case "friend_added":
				result = outcome(id, kind, { applied: true, name, icon: "customers", text: name ? "Agora você e {0} são amigos" : "Você tem um amigo novo" });
				break;
			case "league_reward": {
				// Rankings v1: the end of a league week. Diamonds, the promotion chest (coins worth 3 of the player's gift
				// boxes) and the card with the podium. Once per item (appliedInbox) and once per week (rewardedWeeks).
				const week = str(payload.week);
				if (!/^\d{4}-W\d{2}$/.test(week) || rankings.rewardedWeeks.includes(week)) {
					result = outcome(id, kind, { name });
					break;
				}
				const amount = Math.max(0, Math.min(LEAGUE_REWARD_DIAMONDS_MAX, Math.floor(num(payload.diamonds))));
				const chest = payload.chest === true ? LEAGUE_CHEST_GIFTS * rewards.gift : 0;
				const division = isLeagueDivision(payload.division) ? payload.division : "bronze";
				const place = Math.max(0, Math.floor(num(payload.place)));
				diamonds += amount;
				coins += chest;
				rankings = {
					...rankings,
					rewardedWeeks: [...rankings.rewardedWeeks, week].slice(-RANKING_WEEKS_KEEP),
					cards: [
						...rankings.cards,
						{ id, week, division, place, diamonds: amount, coins: chest, movedTo: isLeagueDivision(payload.movedTo) ? payload.movedTo : division, at: now },
					].slice(-RANKING_CARDS_KEEP),
				};
				rankingsChanged = true;
				result = outcome(id, kind, {
					applied: true,
					coins: chest,
					diamonds: amount,
					icon: "trophy",
					text: amount > 0 && chest > 0 ? "Fim da liga: +{5} diamantes e um baú de +{1} moedas" : amount > 0 ? "Fim da liga: +{5} diamantes" : chest > 0 ? "Fim da liga: um baú de +{1} moedas" : "A liga da semana terminou",
				});
				break;
			}
			case "request_fulfilled": {
				const requestId = num(payload.requestId, NaN);
				requests = requests.filter((request) => request.id !== requestId);
				result = outcome(id, kind, { applied: true, name, icon: "truck", text: name ? "{0} atendeu o seu pedido" : "Um amigo atendeu o seu pedido" });
				break;
			}
			default:
				// A kind this version does not know (a newer server): acked, nothing to do.
				result = outcome(id, kind, { name });
		}
		applied.push(id);
		seen.add(id);
		changed = true;
		outcomes.push(result);
		if (result.applied && result.text) log.unshift(logEntry(result, str(item.from?.avatar), now));
	}

	social = {
		...social,
		appliedInbox: [...social.appliedInbox, ...applied].slice(-SOCIAL_APPLIED_KEEP),
		history: [...log, ...social.history].slice(0, SOCIAL_HISTORY_KEEP),
		totals,
		invites,
		requests,
	};
	const patch: Partial<GameState> = changed
		? {
				social,
				coins,
				logistics: diamonds === state.logistics.premiumCurrency ? state.logistics : { ...state.logistics, premiumCurrency: diamonds },
				inventory,
				inventoryLots,
				interior,
				interiorConstructions: builds.interiorConstructions,
				evolutions: builds.evolutions,
				era: builds.era,
				lots: builds.lots,
				...(rankingsChanged ? { rankings } : {}),
			}
		: {};
	return { patch, outcomes, ack: outcomes.filter((entry) => entry.ack).map((entry) => entry.id) };
}

function logEntry(result: SocialInboxOutcome, avatar: string, now: number): SocialLogEntry {
	return {
		kind: result.kind,
		text: result.text,
		icon: result.icon,
		name: result.name,
		avatar,
		coins: result.coins,
		diamonds: result.diamonds,
		minutes: result.minutes,
		productId: result.productId,
		qty: result.qty,
		at: now,
	};
}

/** "Abrir" in the Correio: the boxes (`ids`, or all) pay their coins and leave the mailbox. */
export function openMailPatch(state: Pick<GameState, "social" | "coins">, ids: readonly string[] | "all") {
	const social = normalizeSocialState(state.social);
	const opened = social.mailbox.filter((mail) => ids === "all" || ids.includes(mail.id));
	if (!opened.length) return null;
	const coins = opened.reduce((sum, mail) => sum + mail.coins, 0);
	return {
		coins,
		count: opened.length,
		patch: {
			coins: state.coins + coins,
			social: { ...social, mailbox: social.mailbox.filter((mail) => !opened.includes(mail)) },
		} satisfies Partial<GameState>,
	};
}

/** Helps the player gave today (UTC), for the "Ajudas hoje" meter. */
export const helpsToday = (state: Pick<GameState, "social">, now = Date.now()) => {
	const social = normalizeSocialState(state.social);
	return social.daily.day === utcDay(now) ? social.daily.helps : 0;
};

// ------------------------------------------------------------------------------------------------- the player's own side

/** Can the player send `qty` of the product to a friend (stock room only; the shelves stay as they are)? */
export const canSendProduct = (state: Pick<GameState, "inventory">, productId: number, qty: number) =>
	qty > 0 && num(state.inventory[productId]) >= qty;

/** The friend's server said the delivery is theirs: the units leave the stock room and the sender is paid back. */
export function sendProductPatch(state: Pick<GameState, "inventory" | "inventoryLots" | "coins" | "social">, productId: number, qty: number, now = Date.now()) {
	const product = itemCatalog.find((entry) => entry.id === productId);
	if (!product || qty <= 0) return null;
	const have = num(state.inventory[productId]);
	const taken = Math.min(have, Math.floor(qty));
	const lots = takeInventoryLots(reconcileInventoryLots(productId, have, state.inventoryLots[productId], now), taken).remainingLots;
	const reward = getDeliveryReward(product.purchasePrice, qty);
	const social = normalizeSocialState(state.social);
	return {
		reward,
		patch: {
			inventory: { ...state.inventory, [productId]: have - taken },
			inventoryLots: { ...state.inventoryLots, [productId]: lots },
			coins: state.coins + reward,
			social: { ...social, totals: { ...social.totals, sent: social.totals.sent + 1 } },
		} satisfies Partial<GameState>,
	};
}
