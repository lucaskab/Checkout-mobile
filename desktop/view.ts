import { t } from "@/i18n";
import type { SimulatorPanel } from "@/@types/simulator";
import { getGameEvent } from "@/data/game-events";
import { getActiveEventEffectLabel, getRecentEventOutcome } from "@/services/game-events";
import { type GameIconId, gameIconAssets, getGameEventIcon, getShopItemIcon } from "@/data/game-icon-assets";
import { getShopItem } from "@/data/shop-items";
import { getActiveBoosts } from "@/services/shop-effects";
import { itemCatalog } from "@/data/market-products";
import {
	getUnlockedPhysicalShelfCount,
	resolveShelfSlotCounts,
} from "@/data/shelf-slots";
import {
	getContractProgress,
	getPendingRequests,
} from "@/services/market-day";
import { getClaimableMissionCount } from "@/services/missions";
import { canClaimDailyLogin, canDoubleDailyLogin } from "@/services/daily-login";
import { getRewardedAdOffer } from "@/services/rewarded-ads";
import { adsStore, isAdOpening } from "./ads";
import { cloudStore } from "./cloud";
import { getExperienceToNextLevel } from "@/services/progression";
import { getNextSimulatorUnlocks } from "@/services/simulator-progression";
import { getStoredInteriorBuilds } from "@/services/interior-construction";
import { type CoachView, type GoalView, getCoachView, getNextGoal } from "@/services/onboarding";
import { type LevelUpView, levelUpView } from "./level-up";
import { type CelebrationView, celebrationView } from "./celebration";
import { pages } from "./pages";
import {
	act,
	type Button,
	button,
	type Card,
	card,
	fmt,
	gameIcon,
	type Page,
	page,
	ratio,
	type State,
} from "./view-kit";

// The whole desktop HUD in one message: Unity only draws it and sends routes/actions back.
export type DesktopView = {
	kind: "view";
	revision: number;
	level: number;
	xp: number;
	xpGoal: number;
	progressLabel: string;
	progressRoute: string;
	coins: string;
	diamonds: string;
	isOpen: boolean;
	// "Meta do dia" = the contract accepted for the day (none on a free day).
	daily: string;
	dailyProgress: number;
	dailyClaimable: boolean;
	goalText: string;
	goalIcon: string;
	goalDone: boolean;
	// Market day (turn): planning → open → results.
	dayPhase: string;
	dayTitle: string;
	dayDetail: string;
	dayProgress: number;
	requestCount: number;
	requestLabel: string;
	requestUrgent: boolean;
	claimableMissions: number;
	hasEvent: boolean;
	eventName: string;
	eventTimer: string;
	eventEffect: string;
	eventIcon: string;
	eventNegative: boolean;
	/** Boosters running now: the HUD shows a glowing chip for each and tints the screen edges. */
	boosts: BoostView[];
	tools: Button[];
	/** Side buttons always on screen: daily gift, free video, diamond store, save with Google (quickButtons). */
	quick: Button[];
	hasOffline: boolean;
	offline: Card;
	// Level-up celebration with everything the new level opened (desktop/level-up.ts); null when seen.
	levelUp: LevelUpView | null;
	// Conquest celebration (lot cleared, new expansion, sector or shelf ready: desktop/celebration.ts); null when none.
	celebration: CelebrationView | null;
	/** Tutorial / tip card of the guide (src/services/onboarding.ts); key "" = nothing to show. */
	coach: CoachView;
	/** The next big objective under the top bar (text "" = none). */
	goal: GoalView;
	hasPage: boolean;
	canBack: boolean;
	page: Page;
};

export type BoostView = {
	id: string;
	name: string;
	icon: string;
	/** What it does right now, in a few words. */
	effect: string;
	/** Seconds left and the full length, for the countdown and the draining bar. */
	seconds: number;
	total: number;
	/** Hex colour of its aura. */
	tint: string;
};

// Each booster has its own colour and a short line for the HUD chip.
const boostLooks: Record<string, { tint: string; effect: string }> = {
	"energy-coffee": { tint: "F0A030", effect: "Equipe 2x mais rápida" },
	"happy-hour": { tint: "E35DB0", effect: "+50% de clientes" },
	"flash-sale": { tint: "E5452B", effect: "+2 produtos por cliente" },
};

function boostViews(state: State, now: number): BoostView[] {
	return getActiveBoosts(state.shop, now).flatMap(({ id, remainingMs }) => {
		const item = getShopItem(id);
		if (!item) return [];
		const look = boostLooks[id] ?? { tint: "F2B03D", effect: item.description };
		return [
			{
				id,
				name: item.name,
				icon: gameIcon(getShopItemIcon(id)),
				effect: look.effect,
				seconds: Math.ceil(remainingMs / 1000),
				total: Math.round((item.durationMs ?? remainingMs) / 1000),
				tint: look.tint,
			},
		];
	});
}

// The money makers and the account, always one tap away (Lucas 14/10: "está muito escondido"): the daily gift
// (lights up when it can be claimed or doubled), the free video (plays right away when one is ready), the diamond
// store, and "Salvar" while the player has not signed in with Google.
function quickButtons(state: State, now: number): Button[] {
	const giftReady = canClaimDailyLogin(state.dailyLogin, now);
	const giftDouble = canDoubleDailyLogin(state.dailyLogin, now);
	const offer = getRewardedAdOffer(state.rewardedAds, now);
	const adReady = offer.available && adsStore.status !== "unavailable" && !isAdOpening();
	const signedIn = !["unavailable", "signed-out", "signing-in"].includes(cloudStore.status);
	const quick: Button[] = [
		button("Presente", {
			icon: gameIcon("gift"),
			route: "!gratis",
			variant: giftReady || giftDouble ? "success" : "secondary",
			badge: giftReady ? "!" : giftDouble ? "2x" : "",
		}),
		adReady
			? act(`+${offer.reward}`, "watchRewardedAd", ["diamonds"], { icon: gameIcon("television"), variant: "gem", badge: "Grátis", ok: "" })
			: button(isAdOpening() ? "Abrindo…" : "Vídeo", {
					icon: gameIcon("television"),
					route: "!gratis",
					variant: "secondary",
				}),
		button("Loja", { icon: gameIcon("diamond"), route: "!currency", variant: "gem" }),
	];
	if (!signedIn && cloudStore.status !== "unavailable")
		quick.push(button("Salvar", { icon: gameIcon("smartphone"), route: "!conta", variant: "primary", badge: "!" }));
	return quick;
}

export const tools: {
	id: SimulatorPanel | "dev" | "loja";
	label: string;
	icon: GameIconId;
	requiredLevel: number;
}[] = [
	// Everything that is bought (furniture, upgrades, team, expansions, decorations, coins) is in the shop.
	{ id: "loja", label: "Loja", icon: "market", requiredLevel: 1 },
	{ id: "store", label: "Prateleiras", icon: "shelf", requiredLevel: 1 },
	// Estoque is also the depot (route "storage" opens it on the dock).
	{ id: "products", label: "Estoque", icon: "warehouse", requiredLevel: 1 },
	{ id: "suppliers", label: "Entregas", icon: "deliveryTruck", requiredLevel: 1 },
	{ id: "sectors", label: "Produção", icon: "conveyor", requiredLevel: 18 },
	{ id: "missions", label: "Missões", icon: "trophy", requiredLevel: 1 },
	{ id: "achievements", label: "Conquistas", icon: "crown", requiredLevel: 1 },
	{ id: "dev", label: "Dev", icon: "toolbox", requiredLevel: 1 },
];

// Old panels that are now shop categories.
const shopRoutes: Record<string, string> = {
	team: "loja:equipe",
	shop: "loja:melhorias",
	expansions: "loja:expansoes",
	currency: "loja:moedas",
};

function progression(state: State) {
	const nextUnlocks = getNextSimulatorUnlocks(
		state.market.level,
		getUnlockedPhysicalShelfCount(
			resolveShelfSlotCounts(state.shelfSlotCounts, state.unlockedShelfSlots),
		),
	);
	const next = nextUnlocks[0];
	const recent = itemCatalog
		.filter((product) => state.market.recentUnlockProductIds.includes(product.id))
		.map((product) => product.name);
	const label = recent.length
		? `Novo: ${recent.slice(0, 2).join(" e ")}`
		: next
			? `Próximo: ${next.label}${nextUnlocks.length > 1 ? ` +${nextUnlocks.length - 1}` : ""} · nível ${next.requiredLevel}`
			: "Catálogo completo";
	const panel = next?.panel ?? "store";
	return { label, route: shopRoutes[panel] ?? panel };
}

const contractUnit = (kind: string) =>
	kind === "satisfaction"
		? "%"
		: kind === "revenue" || kind === "profit"
			? " moedas"
			: kind === "customers"
				? " clientes"
				: kind === "category"
					? " vendas"
					: " pedidos";
const prize = (reward: { coins: number; diamonds: number; experience: number }) =>
	[
		// each piece in the player's language before the pieces join the sentence ("40 coins + 11 XP")
		reward.coins ? t(`${fmt(reward.coins)} moedas`) : "",
		reward.diamonds ? t(`${fmt(reward.diamonds)} diamantes`) : "",
		reward.experience ? `${fmt(reward.experience)} XP` : "",
	]
		.filter(Boolean)
		.join(" + ");
function contractIcon(icon: string) {
	return icon in gameIconAssets ? gameIcon(icon as GameIconId) : gameIcon("target");
}

function offline(state: State) {
	const summary = state.offlineSummary;
	if (!summary) return card("");
	const minutes = Math.max(1, Math.round(summary.durationMs / 60_000));
	return card("Enquanto você estava fora", {
		icon: gameIcon("coin"),
		lines: [
			`${fmt(minutes)} min fora`,
			summary.customers === 1 ? "1 cliente atendido" : `${fmt(summary.customers)} clientes atendidos`,
			summary.coins === 1 ? "+1 moeda" : `+${fmt(summary.coins)} moedas`,
		],
		buttons: [act("Coletar", "dismissOfflineSummary", [], { variant: "success" })],
	});
}

/** The event chip's second line: the effect, or the interaction's progress while the player plays it. */
function eventEffectLine(
	state: State,
	event: NonNullable<ReturnType<typeof getGameEvent>>,
	active: State["events"]["activeEvent"],
	now: number,
	clock: (ms: number) => string,
) {
	const inspection = event.effects.interaction === "inspection" ? state.events.inspection : null;
	if (inspection) {
		const fixed = inspection.stops.filter((stop) => stop.status === "fixed").length;
		const open = inspection.stops.find((stop) => stop.status === "open");
		return open
			? `Checklist do fiscal ${fixed}/${inspection.stops.length} · resolva em ${clock(open.deadline - now)}`
			: `Checklist do fiscal ${fixed}/${inspection.stops.length} · o fiscal está andando pelo mercado`;
	}
	const sales = event.effects.interaction === "window-sales" ? state.events.windowSales : null;
	if (sales) {
		const honking = sales.requests.some((request) => request.status === "waiting");
		return honking
			? `Venda pela janela ${sales.served}/${sales.goal} · um motorista está buzinando: clique no carro!`
			: `Venda pela janela ${sales.served}/${sales.goal} · espere a buzina`;
	}
	return getActiveEventEffectLabel(event, active);
}

export function createDesktopView(
	state: State,
	revision: number,
	stack: string[],
): DesktopView {
	const route = stack.at(-1) ?? "";
	const goal = getExperienceToNextLevel(state.market.level);
	const next = progression(state);
	const active = state.events.activeEvent;
	const event = getGameEvent(active?.eventId);
	const seconds = active ? Math.ceil((active.endsAt - Date.now()) / 1000) : 0;
	const hasEvent = Boolean(event && active && seconds > 0);
	// After the event: the inspector's report stays on the chip for a few seconds.
	const outcome = hasEvent ? null : getRecentEventOutcome(state.events);
	const outcomeEvent = getGameEvent(outcome?.eventId);
	const summary = offline(state);
	const now = Date.now();
	const day = state.day;
	const contract = getContractProgress(day.contract, day.stats);
	const pending = getPendingRequests(day).sort((a, b) => a.expiresAt - b.expiresAt);
	const urgent = pending[0];
	const clock = (ms: number) => {
		const s = Math.max(0, Math.ceil(ms / 1_000));
		return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
	};
	const current = route ? pages(state, route) : page("", "", []);
	return {
		kind: "view",
		revision,
		level: state.market.level,
		xp: state.market.experience,
		xpGoal: goal,
		progressLabel: next.label,
		progressRoute: next.route,
		coins: fmt(state.coins),
		diamonds: fmt(state.logistics.premiumCurrency),
		isOpen: state.market.isOpen,
		// The day's goal is the contract the player accepted: its own target and progress. Before the
		// day starts it asks for one; a free day has no goal.
		daily: day.contract
			? day.phase === "planning"
				? "0%"
				: `${Math.round(contract.ratio * 100)}%`
			: "",
		dailyProgress: day.contract && day.phase !== "planning" ? contract.ratio : 0,
		dailyClaimable: false,
		goalText: day.contract
			? day.phase === "planning"
				? `${day.contract.title} · ${fmt(day.contract.target)}${contractUnit(day.contract.kind)}`
				: `${day.contract.title} · ${fmt(contract.current)} / ${fmt(contract.target)}${contractUnit(day.contract.kind)}`
			: day.phase === "planning"
				? "Escolha o contrato do dia"
				: "Dia livre · sem contrato",
		goalIcon: day.contract ? contractIcon(day.contract.icon) : gameIcon("clipboard"),
		goalDone: Boolean(day.contract && day.phase !== "planning" && contract.completed),
		dayPhase: day.phase,
		dayTitle:
			day.phase === "open"
				? `${day.shift === "noite" ? "NOITE" : "DIA"} ${day.dayNumber} · ${clock((day.endsAt ?? now) - now)}`
				: day.phase === "results"
					? `DIA ${day.dayNumber} · NOTA ${day.result?.grade ?? "-"}`
					: `DIA ${day.dayNumber}`,
		dayDetail:
			day.phase === "open"
				? day.contract
					? `Prêmio do contrato: ${prize(day.contract.reward)}`
					: "Dia livre"
				: day.phase === "results"
					? "Resultado pronto para coletar"
					: "Escolha o contrato e abra",
		// The day card shows how much of the day has gone by; the goal card shows the contract.
		dayProgress:
			day.phase === "open" && day.startedAt && day.endsAt
				? ratio(now - day.startedAt, day.endsAt - day.startedAt)
				: day.phase === "results"
					? 1
					: 0,
		requestCount: pending.length,
		requestLabel: urgent
			? `${clock(urgent.expiresAt - now)} · ${urgent.customerName}: ${urgent.message}`
			: "",
		requestUrgent: Boolean(urgent && urgent.expiresAt - now < 15_000),
		claimableMissions: getClaimableMissionCount(state),
		hasEvent: hasEvent || Boolean(outcome && outcomeEvent),
		eventName: hasEvent && event ? event.name : (outcomeEvent?.name ?? ""),
		eventTimer: hasEvent
			? `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`
			: "",
		eventEffect: hasEvent && event ? eventEffectLine(state, event, active, now, clock) : (outcome?.text ?? ""),
		eventIcon:
			hasEvent && event
				? gameIcon(getGameEventIcon(event.id))
				: outcomeEvent
					? gameIcon(getGameEventIcon(outcomeEvent.id))
					: "",
		eventNegative: hasEvent ? event?.kind === "negative" : outcome?.kind === "negative",
		boosts: boostViews(state, now),
		// Release builds (scripts/release/build-host.ts) hide the Dev tab.
		tools: tools.filter((tool) => tool.id !== "dev" || __DEV__).map((tool) => {
			const locked = state.market.level < tool.requiredLevel;
			const stored = getStoredInteriorBuilds(state).length;
			// Trucks waiting at the dock to be unloaded.
			const atDock = state.receiving.dock.filter((delivery) => delivery.quantity > delivery.unloaded).length;
			return button(tool.label, {
				icon: gameIcon(tool.icon),
				route: `!${tool.id}`,
				// The shop stands out in gold.
				variant: tool.id === "loja" ? "coin" : "secondary",
				enabled: !locked,
				// Estoque also lights up on the old Depósito route ("storage"), which is the same window now.
				active: ((root) => root !== "" && (root === tool.id || (tool.id === "products" && root === "storage")))(
					(stack[0] ?? "").split(":")[0],
				),
				fail: locked ? `Nível ${tool.requiredLevel}` : "",
				badge:
					tool.id === "loja" && stored > 0
						? String(stored)
						: tool.id === "products" && atDock > 0
							? String(atDock)
						: tool.id === "missions" && canClaimDailyLogin(state.dailyLogin, Date.now())
							? "!"
							: "",
			});
		}),
		quick: quickButtons(state, now),
		hasOffline: Boolean(state.offlineSummary),
		offline: summary,
		levelUp: levelUpView(state),
		celebration: celebrationView(state),
		coach: getCoachView(state, route, now),
		goal: getNextGoal(state, {
			lot: gameIcon("key"),
			coin: gameIcon("coin"),
			build: gameIcon("construction"),
			done: gameIcon("success"),
		}),
		hasPage: Boolean(route),
		canBack: stack.length > 1,
		page: current,
	};
}
