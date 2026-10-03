import type {
	GameEventDefinition,
	GameEventEffects,
	GameEventsState,
	GameEventTurn,
} from "@/@types/game-event";
import { gameEvents, getGameEvent } from "@/data/game-events";

const MINIMUM_EVENT_GAP_MS = 20 * 60_000;
const MAXIMUM_EVENT_GAP_MS = 35 * 60_000;
// One event per 10-minute turn: it starts between the 1st and the 4th minute, lasts 3–5 minutes
// and always ends with the turn (the market closing ends it).
const EVENT_START_MIN_MS = 60_000;
const EVENT_START_SPREAD_MS = 3 * 60_000;
const EVENT_MIN_DURATION_MS = 3 * 60_000;
const EVENT_MAX_DURATION_MS = 5 * 60_000;
const EVENT_MIN_REMAINING_MS = 90_000;
const EVENT_END_MARGIN_MS = 5_000;

const defaultEffects: GameEventEffects = {
	customerArrivalMultiplier: 1,
	customerBudgetMultiplier: 1,
	experienceMultiplier: 1,
	productionDurationMultiplier: 1,
	revenueMultiplier: 1,
	supplierCostMultiplier: 1,
	supplierDurationMultiplier: 1,
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
) {
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
			endsAt: now + event.durationMinutes * 60_000,
			eventId: event.id,
			startedAt: now,
		},
		lastEventId: event.id,
		nextEventAt: 0,
		randomSeed: events.randomSeed + 1,
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
 * turn, starting 1–4 minutes in, lasting 3–5 minutes and ending when the turn closes. Without a
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

		const duration = Math.min(
			remaining,
			Math.min(
				EVENT_MAX_DURATION_MS,
				Math.max(EVENT_MIN_DURATION_MS, event.durationMinutes * 60_000),
			),
		);

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
			endsAt: now + event.durationMinutes * 60_000,
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
