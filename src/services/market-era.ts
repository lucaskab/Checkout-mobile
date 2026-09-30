import type {
	GameEraState,
	MarketEraConstruction,
	MarketEraDefinition,
	MarketEraId,
} from "@/@types/economy";
import type { MarketExpansionId } from "@/@types/market-expansion";
import {
	getMarketEra,
	getNextMarketEra,
	marketEras,
	OFFLINE_CAP_MS,
} from "@/data/economy";

// Eras of the market (mesinha → rede): which one the player is in, the evolution being built, and
// what the market earns while the player is away. Pure rules; the store wires them in.

const HOUR = 60 * 60_000;
/** Customers of a turn before the player finished any (about one every 30 s for 10 minutes). */
const DEFAULT_TURN_CUSTOMERS = 18;
/** Share of the ticket that is profit before the player finished any turn. */
const DEFAULT_MARGIN = 0.35;
/** Weight of the newest turn in the moving averages. */
const AVERAGE_WEIGHT = 0.3;

export function createInitialEraState(id: MarketEraId = "mesinha"): GameEraState {
	return { id, construction: null, averageTurnProfit: 0, averageTurnCustomers: 0 };
}

/**
 * Saves from before the eras already have the market building: they start at the mercadinho, or
 * further along when the expansions bought make the market a supermarket or a hypermarket.
 */
export function getEraForExpansions(unlocked: readonly MarketExpansionId[]): MarketEraId {
	if (unlocked.includes("premium-hall") || unlocked.includes("grand-warehouse"))
		return "hipermercado";
	if (unlocked.includes("service-wing") || unlocked.includes("stock-annex"))
		return "supermercado";
	return "mercadinho";
}

const validIds = new Set(marketEras.map((era) => era.id));

export function normalizeEraState(
	value: unknown,
	fallback: MarketEraId,
): GameEraState {
	if (!value || typeof value !== "object") return createInitialEraState(fallback);
	const item = value as Partial<GameEraState>;
	const id = validIds.has(item.id as MarketEraId) ? (item.id as MarketEraId) : fallback;
	const construction = normalizeConstruction(item.construction, id);
	const number = (n: unknown) =>
		typeof n === "number" && Number.isFinite(n) && n > 0 ? n : 0;
	return {
		id,
		construction,
		averageTurnProfit: number(item.averageTurnProfit),
		averageTurnCustomers: number(item.averageTurnCustomers),
	};
}

function normalizeConstruction(value: unknown, current: MarketEraId): MarketEraConstruction | null {
	if (!value || typeof value !== "object") return null;
	const item = value as Partial<MarketEraConstruction>;
	if (
		!validIds.has(item.eraId as MarketEraId) ||
		typeof item.startedAt !== "number" ||
		typeof item.endsAt !== "number" ||
		!Number.isFinite(item.endsAt)
	)
		return null;
	// Only the era right after the current one can be under construction.
	if (getNextMarketEra(current)?.id !== item.eraId) return null;
	return { eraId: item.eraId as MarketEraId, startedAt: item.startedAt, endsAt: item.endsAt };
}

export type EraEvolutionCheck =
	| { ok: true; next: MarketEraDefinition }
	| { ok: false; reason: string; next: MarketEraDefinition | null };

/** Can the player start building the next era now? */
export function checkEraEvolution(era: GameEraState, coins: number): EraEvolutionCheck {
	const next = getNextMarketEra(era.id);
	if (!next) return { ok: false, reason: "Você já está na última era.", next: null };
	if (era.construction) return { ok: false, reason: "A obra da próxima era já está em andamento.", next };
	if (coins < next.coinCost) return { ok: false, reason: "Moedas insuficientes", next };
	return { ok: true, next };
}

/** Pays and starts the evolution; the era changes when the obra finishes (or right away if it has none). */
export function startEraEvolution(era: GameEraState, now: number): GameEraState {
	const next = getNextMarketEra(era.id);
	if (!next || era.construction) return era;
	if (next.buildDurationMs <= 0) return { ...era, id: next.id };
	return {
		...era,
		construction: { eraId: next.id, startedAt: now, endsAt: now + next.buildDurationMs },
	};
}

/** Finishes the obra when its time has come. Returns the same object when nothing changed. */
export function finishEraConstruction(era: GameEraState, now: number): GameEraState {
	if (!era.construction || era.construction.endsAt > now) return era;
	return { ...era, id: era.construction.eraId, construction: null };
}

/** A finished turn feeds the averages that value the time away. */
export function recordFinishedTurn(
	era: GameEraState,
	turn: { profit: number; customers: number },
): GameEraState {
	if (turn.customers <= 0) return era;
	const blend = (old: number, value: number) =>
		old > 0 ? old * (1 - AVERAGE_WEIGHT) + value * AVERAGE_WEIGHT : value;
	return {
		...era,
		averageTurnProfit: Math.round(blend(era.averageTurnProfit, Math.max(0, turn.profit))),
		averageTurnCustomers: Math.round(blend(era.averageTurnCustomers, turn.customers) * 10) / 10,
	};
}

export type OfflineEraIncome = {
	coins: number;
	customers: number;
	/** Played turns this absence was worth. */
	turns: number;
	awayMs: number;
};

/**
 * What the market sold while the player was away: every hour (up to OFFLINE_CAP_MS) is worth part of
 * a played turn, more in bigger eras (a table on the sidewalk barely sells on its own).
 * `fallbackTicket` is the average ticket so far, used before the first turn is finished.
 */
export function getOfflineEraIncome(
	era: GameEraState,
	awayMs: number,
	fallbackTicket = 18,
): OfflineEraIncome {
	const definition = getMarketEra(era.id);
	const counted = Math.min(Math.max(0, awayMs), OFFLINE_CAP_MS);
	const turns = (counted / HOUR) * definition.offlineTurnsPerHour;
	const turnProfit =
		era.averageTurnProfit > 0
			? era.averageTurnProfit
			: fallbackTicket * DEFAULT_MARGIN * DEFAULT_TURN_CUSTOMERS;
	const turnCustomers =
		era.averageTurnCustomers > 0 ? era.averageTurnCustomers : DEFAULT_TURN_CUSTOMERS;
	return {
		coins: Math.floor(turns * turnProfit),
		customers: Math.floor(turns * turnCustomers),
		turns,
		awayMs: counted,
	};
}

/** Customers and baskets of the current era. */
export function getEraEffects(id: MarketEraId) {
	const era = getMarketEra(id);
	return {
		customerArrivalMultiplier: era.arrivalMultiplier,
		ticketMultiplier: era.ticketMultiplier,
	};
}
