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
};

export type GameEventsState = {
	activeEvent: ActiveGameEvent | null;
	lastEventId: string | null;
	nextEventAt: number;
	randomSeed: number;
};
