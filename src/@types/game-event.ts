export type GameEventKind = "positive" | "negative";

export type GameEventEffects = {
	customerArrivalMultiplier: number;
	customerBudgetMultiplier: number;
	experienceMultiplier: number;
	productionDurationMultiplier: number;
	revenueMultiplier: number;
	supplierCostMultiplier: number;
	supplierDurationMultiplier: number;
};

export type GameEventDefinition = {
	description: string;
	durationMinutes: number;
	effectLabel: string;
	effects: Partial<GameEventEffects>;
	id: string;
	kind: GameEventKind;
	name: string;
};

export type ActiveGameEvent = {
	endsAt: number;
	eventId: string;
	startedAt: number;
	/** Turn that started it (ends with that turn); absent for dev-triggered events. */
	turnKey?: string;
};

export type GameEventsState = {
	activeEvent: ActiveGameEvent | null;
	lastEventId: string | null;
	/** When this turn's event starts; 0 once the turn already had its event (or no turn is open). */
	nextEventAt: number;
	randomSeed: number;
	/** Turn the schedule belongs to (day number, shift and opening time); one event per turn. */
	turnKey?: string | null;
};

/** The market turn the events run in: events only run while it is open and never outlast it. */
export type GameEventTurn = {
	endsAt: number;
	key: string;
	open: boolean;
	startedAt: number;
};
