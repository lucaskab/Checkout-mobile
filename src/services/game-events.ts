import type { GameShelfCare } from "@/@types/game";
import type {
	ActiveGameEvent,
	GameEventContext,
	GameEventDefinition,
	GameEventEffects,
	GameEventInspection,
	GameEventsState,
	GameEventTurn,
} from "@/@types/game-event";
import { getMarketEra, marketEras } from "@/data/economy";
import { gameEvents, getGameEvent } from "@/data/game-events";
import { itemCatalog } from "@/data/market-products";

const MINIMUM_EVENT_GAP_MS = 20 * 60_000;
const MAXIMUM_EVENT_GAP_MS = 35 * 60_000;
// One event per 5-minute turn: it starts between 0:40 and 1:40, lasts 1:30–2:30 (a longer event of the
// list a little longer) and always ends with the turn (the market closing ends it).
const EVENT_START_MIN_MS = 40_000;
const EVENT_START_SPREAD_MS = 60_000;
const EVENT_MIN_DURATION_MS = 90_000;
const EVENT_MAX_DURATION_MS = 150_000;
/** Each "minute" of an event's durationMinutes lasts this long in the game. */
const EVENT_MS_PER_MINUTE = 30_000;
const EVENT_MIN_REMAINING_MS = 60_000;
const EVENT_END_MARGIN_MS = 5_000;

/** How long an event lasts: durationMinutes (4–5 in the list) scaled to the short turn, 1:30–2:30. */
export function getEventDurationMs(event: Pick<GameEventDefinition, "durationMinutes">) {
	return Math.min(
		EVENT_MAX_DURATION_MS,
		Math.max(EVENT_MIN_DURATION_MS, event.durationMinutes * EVENT_MS_PER_MINUTE),
	);
}

/** "2:30 min" — the event's real length in the game. */
export function formatEventDuration(event: Pick<GameEventDefinition, "durationMinutes">) {
	const seconds = Math.round(getEventDurationMs(event) / 1000);
	return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")} min`;
}

const defaultEffects: GameEventEffects = {
	customerArrivalMultiplier: 1,
	customerBudgetMultiplier: 1,
	experienceMultiplier: 1,
	productionDurationMultiplier: 1,
	revenueMultiplier: 1,
	supplierCostMultiplier: 1,
	supplierDurationMultiplier: 1,
	categoryDemand: {},
	cheapPreference: 0,
	extraBasketItems: 0,
	cashOnly: false,
	staffSpeedMultiplier: 1,
	shelfWearMultiplier: 1,
	passiveWear: null,
	featuredProductBoost: 1,
	inspection: null,
	powerOutage: false,
	interaction: null,
};

export function createInitialGameEventsState(
	now = Date.now(),
): GameEventsState {
	return {
		activeEvent: null,
		lastEventId: null,
		nextEventAt: now + getEventGap(1),
		randomSeed: 1,
	};
}

export function getActiveGameEventEffects(
	events: GameEventsState,
	now = Date.now(),
): GameEventEffects {
	if (!events.activeEvent || events.activeEvent.endsAt <= now) {
		return defaultEffects;
	}

	const event = getGameEvent(events.activeEvent.eventId);

	return {
		...defaultEffects,
		...event?.effects,
	};
}

export function activateGameEvent(
	events: GameEventsState,
	eventId: string,
	now = Date.now(),
) {
	const event = getGameEvent(eventId);

	if (!event) {
		return null;
	}

	return {
		activeEvent: {
			endsAt: now + getEventDurationMs(event),
			eventId: event.id,
			startedAt: now,
		},
		lastEventId: event.id,
		nextEventAt: 0,
		randomSeed: events.randomSeed + 1,
		turnKey: events.turnKey ?? null,
		wearTickAt: now,
		outcome: null,
		inspection: null,
		windowSales: null,
		sealTurnKey: events.sealTurnKey ?? null,
	};
}

export function getTurnEventKey(day: {
	dayNumber: number;
	shift?: string;
	startedAt: number | null;
}) {
	return `${day.dayNumber}:${day.shift ?? "dia"}:${day.startedAt ?? 0}`;
}

/**
 * Moves the event clock. With a turn, events only run while the market is open: at most one per
 * turn, starting 0:40–1:40 in, lasting 1:30–2:30 and ending when the turn closes. Without a
 * turn (old callers) the real-time gap of 20–35 minutes is kept.
 */
export function advanceGameEvents(
	events: GameEventsState,
	now = Date.now(),
	turn?: GameEventTurn,
	candidates: GameEventDefinition[] = gameEvents,
) {
	if (events.activeEvent) {
		// Only events the turn started end with the turn; a dev-triggered event runs its full time.
		const ownTurn = events.activeEvent.turnKey;
		const closed =
			turn && ownTurn
				? !turn.open || now >= turn.endsAt || turn.key !== ownTurn
				: false;
		if (events.activeEvent.endsAt > now && !closed) {
			return null;
		}

		const nextSeed = events.randomSeed + 1;

		return {
			...events,
			activeEvent: null,
			nextEventAt: turn ? 0 : now + getEventGap(nextSeed),
			randomSeed: nextSeed,
		};
	}

	if (turn) {
		if (!turn.open) {
			return null;
		}

		if (events.turnKey !== turn.key) {
			return {
				...events,
				nextEventAt:
					Math.max(now, turn.startedAt + EVENT_START_MIN_MS) +
					Math.round(EVENT_START_SPREAD_MS * seededRandom(events.randomSeed + 7)),
				turnKey: turn.key,
			};
		}

		if (events.nextEventAt === 0 || now < events.nextEventAt) {
			return null;
		}

		const remaining = turn.endsAt - now - EVENT_END_MARGIN_MS;
		if (remaining < EVENT_MIN_REMAINING_MS) {
			return { ...events, nextEventAt: 0 };
		}

		const event = pickEvent(events, candidates);
		if (!event) {
			return { ...events, nextEventAt: 0 };
		}

		const duration = Math.min(remaining, getEventDurationMs(event));

		return {
			...events,
			activeEvent: {
				endsAt: now + duration,
				eventId: event.id,
				startedAt: now,
				turnKey: turn.key,
			},
			lastEventId: event.id,
			nextEventAt: 0,
			randomSeed: events.randomSeed + 1,
			wearTickAt: now,
			outcome: null,
		};
	}

	if (now < events.nextEventAt) {
		return null;
	}

	const event = pickEvent(events, candidates);

	if (!event) {
		return null;
	}

	return {
		...events,
		activeEvent: {
			endsAt: now + getEventDurationMs(event),
			eventId: event.id,
			startedAt: now,
		},
		lastEventId: event.id,
		nextEventAt: 0,
		randomSeed: events.randomSeed + 1,
	};
}

function pickEvent(events: GameEventsState, candidates: GameEventDefinition[]) {
	const pool = candidates.filter((event) => event.id !== events.lastEventId);
	const list = pool.length > 0 ? pool : candidates;
	return list[Math.floor(seededRandom(events.randomSeed) * list.length)] ?? null;
}

export function normalizeGameEventsState(
	events: Partial<GameEventsState> | undefined,
	now = Date.now(),
) {
	if (!events) {
		return createInitialGameEventsState(now);
	}

	const randomSeed =
		typeof events.randomSeed === "number" && Number.isFinite(events.randomSeed)
			? Math.max(1, Math.floor(events.randomSeed))
			: 1;
	const activeDefinition = getGameEvent(events.activeEvent?.eventId);
	const hasValidActiveEvent = Boolean(
		activeDefinition &&
			events.activeEvent &&
			events.activeEvent.endsAt > now &&
			events.activeEvent.startedAt <= now,
	);

	if (hasValidActiveEvent && events.activeEvent) {
		return {
			activeEvent: events.activeEvent,
			lastEventId: activeDefinition?.id ?? null,
			nextEventAt: 0,
			randomSeed,
			turnKey: events.turnKey ?? null,
			wearTickAt: events.wearTickAt ?? now,
			outcome: events.outcome ?? null,
			inspection: events.inspection ?? null,
			windowSales: events.windowSales ?? null,
			sealTurnKey: events.sealTurnKey ?? null,
		};
	}

	const nextEventAt =
		typeof events.nextEventAt === "number" &&
		Number.isFinite(events.nextEventAt) &&
		events.nextEventAt > now
			? events.nextEventAt
			: now + getEventGap(randomSeed);

	return {
		activeEvent: null,
		lastEventId: getGameEvent(events.lastEventId)?.id ?? null,
		nextEventAt: events.turnKey ? (events.nextEventAt ?? 0) : nextEventAt,
		randomSeed,
		turnKey: events.turnKey ?? null,
		outcome: events.outcome ?? null,
		sealTurnKey: events.sealTurnKey ?? null,
	};
}

function getEventGap(seed: number) {
	const variation = seededRandom(seed);

	return Math.round(
		MINIMUM_EVENT_GAP_MS +
			(MAXIMUM_EVENT_GAP_MS - MINIMUM_EVENT_GAP_MS) * variation,
	);
}

function seededRandom(seed: number) {
	const value = Math.sin(seed * 12.9898) * 43_758.5453;

	return value - Math.floor(value);
}

const eraIndex = (id: string) => marketEras.findIndex((era) => era.id === id);

/** Can this event happen in a market like this one? (expansion reached, a team, a fridge...) */
export function isGameEventAvailable(event: GameEventDefinition, context: GameEventContext) {
	if (event.retired) return false;
	const { minEra, needsRefrigeration, needsStaff } = event.requirements;
	if (eraIndex(context.eraId) < eraIndex(minEra)) return false;
	if (needsStaff && !context.hasWorkingStaff) return false;
	if (needsRefrigeration && !context.hasRefrigeration) return false;
	return true;
}

export function getAvailableGameEvents(context: GameEventContext, events = gameEvents) {
	return events.filter((event) => isGameEventAvailable(event, context));
}

/** Middle selling price of the products on sale: what "cheap" means in this market right now. */
export function getReferencePrice(prices: number[]) {
	const sorted = prices.filter((price) => price > 0).sort((a, b) => a - b);
	if (sorted.length === 0) return 0;
	const middle = Math.floor(sorted.length / 2);
	return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

/**
 * How much more a customer wants a product during the event: the category (cold drinks in the heat),
 * the product in the influencer's video, and at the end of the month the cheaper products.
 */
export function getEventDemandMultiplier(
	effects: GameEventEffects,
	product: { category: string; productId: number; sellingPrice: number },
	featuredProductId: number | undefined,
	referencePrice: number,
) {
	let multiplier = effects.categoryDemand[product.category] ?? 1;
	if (featuredProductId !== undefined && product.productId === featuredProductId)
		multiplier *= effects.featuredProductBoost;
	if (effects.cheapPreference > 0 && referencePrice > 0 && product.sellingPrice > 0) {
		// Half the usual price: ×1.3; twice the usual price: ×0.75 (at full preference).
		const ratio = referencePrice / product.sellingPrice;
		const factor = Math.min(1.35, Math.max(0.65, ratio ** 0.4));
		multiplier *= 1 + (factor - 1) * effects.cheapPreference;
	}
	return multiplier;
}

/** A fixture and the categories of the products on it right now. */
export type EventFixture = { id: string; categories: string[] };

/** Time-based wear: produce wilting in the heat, fridges and freezers thawing without power. */
export function applyPassiveEventWear(
	care: GameShelfCare,
	effects: GameEventEffects,
	fixtures: EventFixture[],
	elapsedMs: number,
): GameShelfCare {
	const wear = effects.passiveWear;
	if (!wear || elapsedMs <= 0) return care;
	const amount = (wear.perMinute * elapsedMs) / 60_000;
	let next: GameShelfCare | null = null;
	for (const fixture of fixtures) {
		if (!fixture.categories.some((category) => wear.categories.includes(category))) continue;
		const current = care[fixture.id];
		const condition = typeof current === "number" && Number.isFinite(current) ? current : 100;
		if (condition <= 0) continue;
		next = next ?? { ...care };
		next[fixture.id] = Math.max(0, condition - amount);
	}
	return next ?? care;
}

export type InspectionReport = {
	/** Fixtures below the minimum condition. */
	writtenUp: string[];
	fine: number;
	reputationBonus: number;
};

/** The inspector checks every open fixture: a fine for each one below the minimum, a bonus if all pass. */
export function inspectFixtures(
	care: GameShelfCare,
	fixtureIds: string[],
	inspection: GameEventInspection,
	dailyGoal: number,
): InspectionReport {
	const writtenUp = fixtureIds.filter((id) => {
		const value = care[id];
		const condition = typeof value === "number" && Number.isFinite(value) ? value : 100;
		return condition < inspection.minCondition;
	});
	const finePerFixture = Math.max(20, Math.round(Math.max(0, dailyGoal) * inspection.fineShareOfGoal));
	return {
		writtenUp,
		fine: writtenUp.length * finePerFixture,
		reputationBonus: writtenUp.length === 0 && fixtureIds.length > 0 ? inspection.cleanReputationBonus : 0,
	};
}

/** Viralizou!: which product on sale goes into the video. */
export function pickFeaturedProduct(productIds: number[], seed: number) {
	const unique = Array.from(new Set(productIds)).sort((a, b) => a - b);
	if (unique.length === 0) return undefined;
	return unique[Math.floor(seededRandom(seed + 11) * unique.length)];
}

/** The effect line shown to the player: Viralizou! names the product in the video. */
export function getActiveEventEffectLabel(
	event: GameEventDefinition,
	active: ActiveGameEvent | null | undefined,
) {
	const productId = active?.eventId === event.id ? active.featuredProductId : undefined;
	const product = productId === undefined ? null : itemCatalog.find((item) => item.id === productId);
	return product ? event.effectLabel.replace("pelo produto do vídeo", `por ${product.name}, o produto do vídeo`) : event.effectLabel;
}

/** How long the inspector's report stays on screen after the event ends. */
export const EVENT_OUTCOME_VISIBLE_MS = 12_000;

export function getRecentEventOutcome(events: GameEventsState, now = Date.now()) {
	const outcome = events.outcome;
	return outcome && !events.activeEvent && now - outcome.at < EVENT_OUTCOME_VISIBLE_MS ? outcome : null;
}

/** Where and when the event can happen, in the player's words (dev page). */
export function describeGameEventRequirements(event: GameEventDefinition) {
	const parts = [`A partir de: ${getMarketEra(event.requirements.minEra).name}`];
	if (event.requirements.needsStaff) parts.push("precisa de funcionário trabalhando");
	if (event.requirements.needsRefrigeration) parts.push("precisa de geladeira ou freezer");
	return parts.join(" · ");
}
