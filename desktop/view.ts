import type { SimulatorPanel } from "@/@types/simulator";
import { getGameEvent } from "@/data/game-events";
import { type GameIconId, getGameEventIcon } from "@/data/game-icon-assets";
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
import { getExperienceToNextLevel } from "@/services/progression";
import { getNextSimulatorUnlocks } from "@/services/simulator-progression";
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
	daily: string;
	dailyProgress: number;
	dailyClaimable: boolean;
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
	tools: Button[];
	hasOffline: boolean;
	offline: Card;
	hasPage: boolean;
	canBack: boolean;
	page: Page;
};

const tools: {
	id: SimulatorPanel | "dev";
	label: string;
	icon: GameIconId;
	requiredLevel: number;
}[] = [
	{ id: "store", label: "Prateleiras", icon: "shelf", requiredLevel: 1 },
	{ id: "products", label: "Estoque", icon: "basket", requiredLevel: 1 },
	{ id: "storage", label: "Depósito", icon: "warehouse", requiredLevel: 1 },
	{ id: "suppliers", label: "Entregas", icon: "deliveryTruck", requiredLevel: 1 },
	{ id: "sectors", label: "Produção", icon: "market", requiredLevel: 2 },
	{ id: "team", label: "Equipe", icon: "computer", requiredLevel: 2 },
	{ id: "shop", label: "Melhorias", icon: "toolbox", requiredLevel: 2 },
	{ id: "expansions", label: "Expansões", icon: "construction", requiredLevel: 4 },
	{ id: "missions", label: "Missões", icon: "trophy", requiredLevel: 1 },
	{ id: "achievements", label: "Conquistas", icon: "crown", requiredLevel: 1 },
	{ id: "currency", label: "Diamantes", icon: "diamond", requiredLevel: 1 },
	{ id: "dev", label: "Dev", icon: "toolbox", requiredLevel: 1 },
];

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
	return { label, route: next?.panel ?? "store" };
}

function offline(state: State) {
	const summary = state.offlineSummary;
	if (!summary) return card("");
	const minutes = Math.max(1, Math.round(summary.durationMs / 60_000));
	return card("Enquanto você estava fora", {
		icon: gameIcon("coin"),
		lines: [
			`${fmt(minutes)} min fora`,
			`${fmt(summary.customers)} clientes atendidos`,
			`+${fmt(summary.coins)} moedas`,
		],
		buttons: [act("Coletar", "dismissOfflineSummary", [], { variant: "success" })],
	});
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
		daily: `${fmt(state.daily.revenue)} / ${fmt(state.daily.goal)}`,
		dailyProgress: ratio(state.daily.revenue, state.daily.goal),
		dailyClaimable: state.daily.goalReached && !state.daily.claimed,
		dayPhase: day.phase,
		dayTitle:
			day.phase === "open"
				? `DIA ${day.dayNumber} · ${clock((day.endsAt ?? now) - now)}`
				: day.phase === "results"
					? `DIA ${day.dayNumber} · NOTA ${day.result?.grade ?? "-"}`
					: `DIA ${day.dayNumber}`,
		dayDetail:
			day.phase === "open"
				? day.contract
					? `${day.contract.title} · ${contract.completed ? "cumprido!" : contract.label}`
					: "Dia livre"
				: day.phase === "results"
					? "Resultado pronto para coletar"
					: "Escolha o contrato e abra",
		dayProgress: day.phase === "open" && day.contract ? contract.ratio : day.phase === "results" ? 1 : 0,
		requestCount: pending.length,
		requestLabel: urgent
			? `${clock(urgent.expiresAt - now)} · ${urgent.customerName}: ${urgent.message}`
			: "",
		requestUrgent: Boolean(urgent && urgent.expiresAt - now < 15_000),
		claimableMissions: getClaimableMissionCount(state),
		hasEvent,
		eventName: hasEvent && event ? event.name : "",
		eventTimer: hasEvent
			? `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`
			: "",
		eventEffect: hasEvent && event ? event.effectLabel : "",
		eventIcon: hasEvent && event ? gameIcon(getGameEventIcon(event.id)) : "",
		eventNegative: hasEvent && event?.kind === "negative",
		tools: tools.map((tool) => {
			const locked = state.market.level < tool.requiredLevel;
			return button(tool.label, {
				icon: gameIcon(tool.icon),
				route: `!${tool.id}`,
				variant: "secondary",
				enabled: !locked,
				active: (stack[0] ?? "").split(":")[0] === tool.id,
				fail: locked ? `Nível ${tool.requiredLevel}` : "",
			});
		}),
		hasOffline: Boolean(state.offlineSummary),
		offline: summary,
		hasPage: Boolean(route),
		canBack: stack.length > 1,
		page: current,
	};
}
