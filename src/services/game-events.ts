import type { GameEventEffects, GameEventsState } from "@/@types/game-event";
import { gameEvents, getGameEvent } from "@/data/game-events";

const MINIMUM_EVENT_GAP_MS = 20 * 60_000;
const MAXIMUM_EVENT_GAP_MS = 35 * 60_000;

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

export function advanceGameEvents(events: GameEventsState, now = Date.now()) {
	if (events.activeEvent) {
		if (events.activeEvent.endsAt > now) {
			return null;
		}

		const nextSeed = events.randomSeed + 1;

		return {
			...events,
			activeEvent: null,
			nextEventAt: now + getEventGap(nextSeed),
			randomSeed: nextSeed,
		};
	}

	if (now < events.nextEventAt) {
		return null;
	}

	const candidates = gameEvents.filter(
		(event) => event.id !== events.lastEventId,
	);
	const eventIndex = Math.floor(
		seededRandom(events.randomSeed) * candidates.length,
	);
	const event = candidates[eventIndex] ?? gameEvents[0];

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
		nextEventAt,
		randomSeed,
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
