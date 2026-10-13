import type { GameState } from "@/@types/game";
import type { OnboardingMarks, OnboardingReward, OnboardingState } from "@/@types/onboarding";
import { getNextMarketEra } from "@/data/economy";
import { getMarketLot } from "@/data/market-lots";
import {
	ONBOARDING_GUIDE,
	ONBOARDING_GUIDE_ART,
	type OnboardingStepDef,
	type OnboardingStepId,
	onboardingSteps,
	onboardingTips,
} from "@/data/onboarding";
import { getShelfCapacity } from "@/data/shelf-capacity";
import { getShelfSlotCount, getShelfSlotIds, resolveShelfSlotCounts } from "@/data/shelf-slots";
import { shelves } from "@/data/market-products";
import { checkEraEvolution } from "@/services/market-era";
import { getMissingLots } from "@/services/market-lots";

// First-time onboarding (see src/data/onboarding.ts for the texts).
// The guided first day is a list of steps; each one is finished by PLAYING (opening a window, ringing a
// customer up, placing an order…), read from the game state and the page on screen, so the tutorial can
// never ask for something the game did not do. Pure functions: the store applies the result
// (processOnboarding) and the desktop view draws getCoachView.

/** Page on screen ("" = none), e.g. "shelf:produce", "day", "products". */
export type OnboardingRoute = string;

/** Time a "bubble" step waits after the condition is met before moving on (lets the player read). */
const READ_MS = 900;
/** The first truck of the tutorial arrives this fast. */
export const ONBOARDING_EXPRESS_MS = 20_000;

const stepIndex = (id: string) => onboardingSteps.findIndex((step) => step.id === id);
const stepDef = (id: string): OnboardingStepDef | undefined => onboardingSteps.find((step) => step.id === id);

export function createOnboardingState(): OnboardingState {
	return {
		status: "active",
		step: onboardingSteps[0].id,
		stepStartedAt: 0,
		marks: { served: 0, orders: 0, unloaded: 0, restocked: 0 },
		reward: null,
		tipsSeen: [],
		tip: "",
		completed: [],
	};
}

/** Tips that a player who already knows the basics (old save, skipped tutorial) does not need. */
const BASIC_TIPS = ["contratos", "repor", "fila", "loja"];

/**
 * Old saves have no onboarding: a market that already sold or grew is treated as done (the guided day
 * would ask a veteran to open a stall they left behind), a fresh one starts the tutorial.
 */
export function normalizeOnboardingState(
	value: Partial<OnboardingState> | undefined,
	progress: { level: number; dayNumber: number; served: number },
): OnboardingState {
	const initial = createOnboardingState();
	if (!value || typeof value !== "object") {
		const veteran = progress.level > 1 || progress.dayNumber > 1 || progress.served > 0;
		return veteran ? { ...initial, status: "done", step: "", tipsSeen: [...BASIC_TIPS] } : initial;
	}
	const status = value.status === "done" || value.status === "skipped" ? value.status : "active";
	const step = status === "active" && stepIndex(value.step ?? "") >= 0 ? (value.step as string) : status === "active" ? initial.step : "";
	return {
		...initial,
		...value,
		status,
		step,
		marks: { ...initial.marks, ...(value.marks ?? {}) },
		tipsSeen: Array.isArray(value.tipsSeen) ? value.tipsSeen : [],
		completed: Array.isArray(value.completed) ? value.completed : [],
		tip: typeof value.tip === "string" ? value.tip : "",
	};
}

export function getOnboardingMarks(state: GameState): OnboardingMarks {
	return {
		served: state.checkout.served,
		orders: state.statistics.supplierOrdersPlaced,
		unloaded: state.receiving.unloadedUnits,
		restocked: state.statistics.restockedUnits,
	};
}

const routeName = (route: OnboardingRoute) => route.split(":")[0];

/** A shelf with goods in the depot that is under a third full (the REPOR button shows then). */
export function hasLowShelf(state: GameState) {
	if (state.employees.employees.some((employee) => employee.isWorking && employee.role === "stock_clerk")) return false;
	const counts = resolveShelfSlotCounts(state.shelfSlotCounts, state.unlockedShelfSlots);
	return shelves.some((shelf) => {
		const count = getShelfSlotCount(shelf.id, counts);
		if (count <= 0) return false;
		const capacity = getShelfCapacity(state.shelfUpgradeLevels[shelf.id] ?? 0);
		return getShelfSlotIds(shelf.id, count).some((slotId) => {
			const productId = state.shelfAssignments[slotId];
			if (!productId) return false;
			// Same rule as the REPOR button (Unity CheckoutStockroom): only a shelf that ran out calls for a box.
			return capacity > 0 && (state.inventory[productId] ?? 0) > 0 && (state.shelfStock[slotId] ?? 0) <= 0;
		});
	});
}

const readyAtRegister = (state: GameState, now: number) => state.checkout.queue.some((item) => item.readyAt <= now);
const trucksAtDock = (state: GameState) => state.receiving.dock.some((delivery) => delivery.quantity > delivery.unloaded);

/** Is this guided step finished? (modal/bubble steps with a button also finish through onboardingNext). */
export function isStepDone(id: OnboardingStepId, state: GameState, route: OnboardingRoute, now: number): boolean {
	const o = state.onboarding;
	const marks = o.marks;
	const name = routeName(route);
	switch (id) {
		case "boas-vindas":
		case "objetivo":
			return false;
		case "mesinha":
			// "Prateleiras" opens the shelf window of the first fixture ("store"); a fixture's own route is "shelf:<id>".
			return name === "shelf" || name === "store";
		case "vitrine":
			// Closing the shelf window also moves on.
			return name !== "shelf" && name !== "store" && now - o.stepStartedAt > READ_MS;
		case "abrir":
			return name === "day" || state.market.isOpen;
		case "dia-livre":
			return state.market.isOpen;
		case "primeiro-cliente":
			return readyAtRegister(state, now) || state.checkout.served > marks.served;
		case "caixa":
			return state.checkout.served > marks.served;
		case "estoque":
			return name === "products" || name === "storage";
		case "deposito":
			return name !== "products" && name !== "storage" && now - o.stepStartedAt > READ_MS;
		case "entregas":
			return name === "suppliers" || state.statistics.supplierOrdersPlaced > marks.orders;
		case "pedir":
			return state.statistics.supplierOrdersPlaced > marks.orders;
		case "caminhao":
			return trucksAtDock(state) || state.receiving.unloadedUnits > marks.unloaded;
		case "descarregar":
			// Done once something went onto the racks (the truck may carry more than fits today).
			return state.receiving.unloadedUnits > marks.unloaded;
		case "missoes":
			return name === "missions";
	}
}

/** Is a one-off tip worth showing now? */
function tipWanted(id: string, state: GameState, route: OnboardingRoute, now: number): boolean {
	const name = routeName(route);
	switch (id) {
		case "fim-do-dia":
			return state.day.phase === "results";
		case "contratos":
			return state.day.phase === "planning" && state.day.dayNumber >= 2 && name === "day";
		case "repor":
			return state.market.isOpen && hasLowShelf(state) && route === "";
		case "fila":
			return state.checkout.queue.filter((item) => item.readyAt <= now).length >= 3 && route === "";
		case "loja":
			return state.market.level >= 3 && route === "";
		case "terreno": {
			const next = getNextMarketEra(state.era.id);
			const missing = next ? getMissingLots(state.lots, next.id).filter((lot) => !state.lots.owned.includes(lot)) : [];
			const lot = missing[0] ? getMarketLot(missing[0]) : undefined;
			return Boolean(lot && state.coins >= lot.price && route === "");
		}
		case "evoluir":
			return checkEraEvolution(state.era, state.coins, state.lots).ok && route === "";
		case "equipe":
			return state.market.level >= 9 && state.era.id !== "mesinha" && state.era.id !== "tenda" && state.era.id !== "banca" && route === "";
		case "producao":
			return state.market.level >= 18 && route === "";
		default:
			return false;
	}
}

/** A shown tip goes away on its own once the player did what it asked. */
function tipSolved(id: string, state: GameState, route: OnboardingRoute, now: number): boolean {
	const name = routeName(route);
	switch (id) {
		case "fim-do-dia":
			return state.day.phase !== "results";
		case "contratos":
			return state.day.phase !== "planning" || name !== "day";
		case "repor":
			return !hasLowShelf(state);
		case "fila":
			return !state.checkout.queue.some((item) => item.readyAt <= now);
		case "loja":
		case "evoluir":
		case "equipe":
			return name === "loja";
		case "terreno":
			return name === "loja";
		case "producao":
			return name === "sectors" || name === "sector";
		default:
			return true;
	}
}

type OnboardingUpdate = Partial<Pick<GameState, "onboarding" | "coins" | "logistics" | "market">>;

function giveReward(state: GameState, def: OnboardingStepDef, now: number): OnboardingUpdate {
	if (!def.reward) return {};
	const reward: OnboardingReward = { key: `${def.id}-${now}`, ...def.reward };
	return {
		coins: state.coins + def.reward.coins,
		logistics: { ...state.logistics, premiumCurrency: state.logistics.premiumCurrency + def.reward.diamonds },
		onboarding: { ...state.onboarding, reward },
	};
}

/** Moves the tutorial to the step after `id`, with fresh counters. */
function advance(state: GameState, id: OnboardingStepId, now: number): OnboardingUpdate {
	const def = stepDef(id);
	// Replaying the tutorial (Guia) does not pay its prizes again.
	const update = def && stepPaysReward(state, id) ? giveReward(state, def, now) : {};
	const base = update.onboarding ?? state.onboarding;
	const next = onboardingSteps[stepIndex(id) + 1];
	const onboarding: OnboardingState = {
		...base,
		status: next ? "active" : "done",
		step: next?.id ?? "",
		stepStartedAt: now,
		marks: getOnboardingMarks(state),
		completed: [...base.completed.filter((item) => item !== id), id],
	};
	let logistics = update.logistics ?? state.logistics;
	// The tutorial's first truck is an express one, so the player sees the whole loop in one sitting.
	if (id === "pedir") {
		const newest = [...logistics.orders].sort((a, b) => b.createdAt - a.createdAt)[0];
		if (newest && newest.status !== "entregue" && newest.deliveryDurationMs > ONBOARDING_EXPRESS_MS)
			logistics = {
				...logistics,
				orders: logistics.orders.map((order) =>
					order.id === newest.id ? { ...order, createdAt: now, deliveryDurationMs: ONBOARDING_EXPRESS_MS } : order,
				),
			};
	}
	return { ...update, logistics, onboarding };
}

/**
 * Every second and after every page change: finishes the current step when the game shows it was done,
 * makes the first customer come soon, and (after the guided day) picks the next one-off tip.
 * Returns null when nothing changes.
 */
export function stepOnboarding(state: GameState, route: OnboardingRoute, now: number): OnboardingUpdate | null {
	const o = state.onboarding;
	if (o.status === "active") {
		const id = o.step as OnboardingStepId;
		// A step that has just begun first records where the counters stand.
		if (!o.stepStartedAt) return { onboarding: { ...o, stepStartedAt: now, marks: getOnboardingMarks(state) } };
		if (isStepDone(id, state, route, now)) return advance(state, id, now);
		// The very first customer comes right away instead of after a quiet minute.
		if (id === "primeiro-cliente" && state.market.isOpen && (state.market.nextCustomerAt ?? 0) > now + 4_000)
			return { market: { ...state.market, nextCustomerAt: now + 2_500 } };
		return null;
	}
	// One-off tips: the one on screen leaves when solved; otherwise the first unseen tip that applies shows.
	if (o.tip) {
		if (!tipSolved(o.tip, state, route, now)) return null;
		return { onboarding: { ...o, tipsSeen: [...o.tipsSeen, o.tip], tip: "" } };
	}
	const tip = onboardingTips.find((item) => !o.tipsSeen.includes(item.id) && tipWanted(item.id, state, route, now));
	return tip ? { onboarding: { ...o, tip: tip.id } } : null;
}

/** "Continuar" / "Entendi" on a modal or bubble step (only steps with a button). */
export function continueOnboarding(state: GameState, now: number): OnboardingUpdate | null {
	const o = state.onboarding;
	if (o.status !== "active") return null;
	const def = stepDef(o.step);
	if (!def?.button) return null;
	return advance(state, def.id, now);
}

export function skipOnboarding(state: GameState): OnboardingUpdate | null {
	if (state.onboarding.status !== "active") return null;
	return { onboarding: { ...state.onboarding, status: "skipped", step: "", reward: null } };
}

/** Plays the guided day again (from the shelf window on: the welcome is not repeated). Prizes are not paid twice. */
export function restartOnboarding(state: GameState, now: number): OnboardingUpdate {
	return {
		onboarding: {
			...state.onboarding,
			status: "active",
			step: "mesinha",
			stepStartedAt: now,
			marks: getOnboardingMarks(state),
			tip: "",
			reward: null,
		},
	};
}

export function dismissOnboardingTip(state: GameState): OnboardingUpdate | null {
	const o = state.onboarding;
	if (!o.tip) return null;
	return { onboarding: { ...o, tipsSeen: [...o.tipsSeen, o.tip], tip: "" } };
}

/** Prizes already paid are not paid again when the tutorial is replayed. */
export function stepPaysReward(state: GameState, id: OnboardingStepId) {
	return !state.onboarding.completed.includes(id);
}

// ------------------------------------------------------------------------------------------------ view

/** What Unity's coach draws (flat, JsonUtility-friendly). key "" = nothing on screen. */
export type CoachView = {
	key: string;
	/** "modal" | "spotlight" | "bubble" */
	mode: string;
	speaker: string;
	art: string;
	title: string;
	text: string;
	/** Shorter instruction while a game window (register, shop, dock…) is open. */
	gameText: string;
	target: string;
	/** Button on the card ("" = finish by playing). */
	button: string;
	buttonAction: string;
	/** "Pular tutorial" link (only on the welcome card). */
	canSkip: boolean;
	/** Tip ("Entendi" closes it) instead of a tutorial step. */
	isTip: boolean;
	step: number;
	total: number;
	/** Prize to celebrate once per key ("" = none). */
	rewardKey: string;
	rewardText: string;
	/** Stages of the market, drawn on the welcome card as the road ahead. */
	path: string[];
};

const emptyCoach = (): CoachView => ({
	key: "",
	mode: "",
	speaker: ONBOARDING_GUIDE,
	art: ONBOARDING_GUIDE_ART,
	title: "",
	text: "",
	gameText: "",
	target: "",
	button: "",
	buttonAction: "",
	canSkip: false,
	isTip: false,
	step: 0,
	total: 0,
	rewardKey: "",
	rewardText: "",
	path: [],
});

const PATH = ["Mesinha", "Tenda", "Banca", "Contêiner", "Späti", "Quitanda", "Minimercado", "Mercadinho", "Supermercado", "Hipermercado", "Rede"];

/** The coach card for the page on screen. While the market is closed mid-tutorial it points back at ABRIR. */
export function getCoachView(state: GameState, route: OnboardingRoute, now: number): CoachView {
	const o = state.onboarding;
	const view = emptyCoach();
	if (o.reward) {
		view.rewardKey = o.reward.key;
		view.rewardText = [
			o.reward.text,
			o.reward.coins ? `+${o.reward.coins} moedas` : "",
			o.reward.diamonds ? `+${o.reward.diamonds} diamantes` : "",
		]
			.filter(Boolean)
			.join("  ");
	}
	// The day's results come first: they need a tap before anything else.
	if (state.day.phase === "results" && o.status === "active" && stepIndex(o.step) > stepIndex("dia-livre")) {
		const tip = onboardingTips.find((item) => item.id === "fim-do-dia");
		if (tip)
			return { ...view, key: "fim-do-dia", mode: "spotlight", title: tip.title, text: tip.text, target: tip.target, isTip: true };
	}
	if (o.status === "active") {
		const def = stepDef(o.step);
		if (!def) return view;
		const total = onboardingSteps.length - 1;
		const base: CoachView = {
			...view,
			key: def.id,
			mode: def.mode,
			title: def.title,
			text: def.text,
			gameText: def.gameText ?? "",
			target: def.target,
			button: def.button ?? "",
			buttonAction: def.button ? "onboardingNext" : "",
			canSkip: def.id === "boas-vindas",
			step: Math.max(1, stepIndex(def.id)),
			total,
			path: def.id === "boas-vindas" ? PATH : [],
		};
		const name = routeName(route);
		const needsOpen = ["primeiro-cliente", "caixa"].includes(def.id) && !state.market.isOpen && state.checkout.queue.length === 0;
		if (needsOpen)
			return name === "day"
				? { ...base, mode: "spotlight", title: "Abra a loja", text: "Escolha como começar o dia e abra a loja para os clientes virem.", target: "action:startDay" }
				: { ...base, mode: "spotlight", title: "Abra a loja", text: "A loja está fechada. Toque em ABRIR para os clientes voltarem.", target: "market" };
		// Steps that point at a button inside a page: first lead the player to that page.
		if (def.id === "dia-livre" && name !== "day") return { ...base, target: "market" };
		if (def.id === "pedir" && name !== "suppliers") return { ...base, target: "tool:!suppliers", text: "Toque em ENTREGAS para abrir o atacado." };
		if (def.id === "caixa" && !readyAtRegister(state, now)) return { ...base, mode: "bubble", target: "", text: "O cliente está escolhendo... já já ele vai para o caixa." };
		if (def.id === "descarregar" && !trucksAtDock(state)) return { ...base, mode: "bubble", target: "" };
		return base;
	}
	if (o.tip) {
		const tip = onboardingTips.find((item) => item.id === o.tip);
		if (tip)
			return { ...view, key: tip.id, mode: "bubble", title: tip.title, text: tip.text, target: tip.target, button: "Entendi", buttonAction: "dismissOnboardingTip", isTip: true };
	}
	return view;
}

// ------------------------------------------------------------------------------------------- next goal

/** The big objective under the top bar (Township's task / Hay Day's next goal). */
export type GoalView = {
	/** "" = no card. */
	text: string;
	detail: string;
	icon: string;
	progress: number;
	route: string;
};

/** The road to the next expansion: buy its lot, clear it, save the coins, then evolve. */
export function getNextGoal(state: GameState, icons: { lot: string; coin: string; build: string; done: string }): GoalView {
	const none: GoalView = { text: "", detail: "", icon: "", progress: -1, route: "" };
	if (state.onboarding.status === "active") return none;
	const next = getNextMarketEra(state.era.id);
	if (!next) return none;
	if (state.era.construction)
		return { text: `Obra em andamento: ${next.name}`, detail: "A nova loja abre sozinha quando os pedreiros terminarem.", icon: icons.build, progress: -1, route: "loja:expansoes" };
	const missing = getMissingLots(state.lots, next.id);
	const toBuy = missing.find((id) => !state.lots.owned.includes(id));
	if (toBuy) {
		const lot = getMarketLot(toBuy);
		const price = lot?.price ?? 0;
		return {
			text: `Compre o ${lot?.label ?? `lote ${toBuy}`}`,
			detail: `Próxima expansão: ${next.name} · ${state.coins.toLocaleString("pt-BR")} / ${price.toLocaleString("pt-BR")} moedas`,
			icon: icons.lot,
			progress: price > 0 ? Math.min(1, state.coins / price) : 1,
			route: "loja:terrenos",
		};
	}
	if (missing.length > 0) {
		const lot = getMarketLot(missing[0]);
		return {
			text: state.lots.clearing ? `Limpando o ${lot?.label ?? "terreno"}` : `Limpe o ${lot?.label ?? "terreno"}`,
			detail: `Próxima expansão: ${next.name} · o terreno precisa estar limpo`,
			icon: icons.lot,
			progress: -1,
			route: "loja:terrenos",
		};
	}
	return {
		text: state.coins >= next.coinCost ? `Evolua o mercado: ${next.name}!` : `Junte moedas para evoluir`,
		detail: `Próxima expansão: ${next.name} · ${state.coins.toLocaleString("pt-BR")} / ${next.coinCost.toLocaleString("pt-BR")} moedas`,
		icon: state.coins >= next.coinCost ? icons.done : icons.coin,
		progress: Math.min(1, state.coins / Math.max(1, next.coinCost)),
		route: "loja:expansoes",
	};
}
