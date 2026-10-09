import type { MarketEraId } from "@/@types/economy";
import type { StoreIncidentKind } from "@/@types/store-incident";

export type GameEventKind = "positive" | "negative";

/** Shelves of these categories lose condition every minute (wilting in the heat, freezers thawing). */
export type GameEventPassiveWear = {
	categories: string[];
	perMinute: number;
};

/** The health inspector checks every fixture when the visit ends. */
export type GameEventInspection = {
	/** A fixture below this condition is written up. */
	minCondition: number;
	/** Fine per fixture written up, as a share of the day's revenue goal. */
	fineShareOfGoal: number;
	/** Reputation won when every fixture passes. */
	cleanReputationBonus: number;
};

export type GameEventEffects = {
	customerArrivalMultiplier: number;
	customerBudgetMultiplier: number;
	experienceMultiplier: number;
	productionDurationMultiplier: number;
	revenueMultiplier: number;
	supplierCostMultiplier: number;
	supplierDurationMultiplier: number;
	/** How much more (or less) customers want each category (necessity ×). */
	categoryDemand: Record<string, number>;
	/** 0 = price does not matter more than usual; 1 = customers clearly prefer the cheapest products. */
	cheapPreference: number;
	/** Extra products each customer takes. */
	extraBasketItems: number;
	/** Every customer pays in cash (the card machine is down). */
	cashOnly: boolean;
	/** Stock clerks, cleaners and cashiers work this much faster (>1) or slower (<1). */
	staffSpeedMultiplier: number;
	/** Condition each sale takes from its fixture (kids handling everything ×2). */
	shelfWearMultiplier: number;
	passiveWear: GameEventPassiveWear | null;
	/** One product on sale is in the video: customers want it this much more. */
	featuredProductBoost: number;
	inspection: GameEventInspection | null;
	/** The street lights and the power-hungry fixtures are off. */
	powerOutage: boolean;
	/**
	 * What the player does during the event (src/services/event-interactions.ts): "inspection" = the health
	 * inspector's checklist, "window-sales" = selling drinks to drivers stuck in the jam.
	 */
	interaction: GameEventInteraction | null;
};

export type GameEventInteraction = "inspection" | "window-sales";

/** One spot the inspector checks: a real mishap (store incident) the player must fix in time. */
export type InspectionStop = {
	id: string;
	/** When the inspector gets there. */
	at: number;
	/** When the time to fix it runs out (0 until the stop opens). */
	deadline: number;
	incidentId: string | null;
	kind: StoreIncidentKind | null;
	shelfId: string | null;
	status: "waiting" | "open" | "fixed" | "failed";
};

export type InspectionRun = {
	startedAt: number;
	stops: InspectionStop[];
};

/** A driver stuck in the jam asking for a drink through the window. */
export type WindowSaleRequest = {
	id: string;
	/** Lane (0 = next to the sidewalk) and car in the lane of the jam scene. */
	lane: number;
	slot: number;
	productId: number;
	createdAt: number;
	expiresAt: number;
	servedAt?: number;
	status: "waiting" | "served" | "missed";
};

export type WindowSalesState = {
	requests: WindowSaleRequest[];
	nextAt: number;
	served: number;
	goal: number;
	rewardPaid: boolean;
	seq: number;
};

/** When the event can be drawn: from an expansion on, and only if the market has what it needs. */
export type GameEventRequirements = {
	/** First expansion where the event can happen. */
	minEra: MarketEraId;
	/** Someone on the payroll must be working (cashier, stock clerk or cleaner). */
	needsStaff?: boolean;
	/** The market must own a fixture that runs on power (fridge or freezer). */
	needsRefrigeration?: boolean;
};

export type GameEventDefinition = {
	description: string;
	durationMinutes: number;
	effectLabel: string;
	effects: Partial<GameEventEffects>;
	id: string;
	kind: GameEventKind;
	name: string;
	requirements: GameEventRequirements;
	/** No longer drawn on the turn (kept so old saves and the dev menu still know it). */
	retired?: boolean;
};

/** What the market has, to know which events make sense right now. */
export type GameEventContext = {
	eraId: MarketEraId;
	hasWorkingStaff: boolean;
	hasRefrigeration: boolean;
};

export type ActiveGameEvent = {
	endsAt: number;
	eventId: string;
	startedAt: number;
	/** Turn that started it (ends with that turn); absent for dev-triggered events. */
	turnKey?: string;
	/** Viralizou!: the product in the video. */
	featuredProductId?: number;
};

/** What an event left behind (the inspector's report), shown for a few seconds after it ends. */
export type GameEventOutcome = {
	at: number;
	eventId: string;
	kind: GameEventKind;
	text: string;
};

export type GameEventsState = {
	activeEvent: ActiveGameEvent | null;
	lastEventId: string | null;
	/** When this turn's event starts; 0 once the turn already had its event (or no turn is open). */
	nextEventAt: number;
	randomSeed: number;
	/** Turn the schedule belongs to (day number, shift and opening time); one event per turn. */
	turnKey?: string | null;
	/** Last time the active event's passive wear was applied. */
	wearTickAt?: number;
	outcome?: GameEventOutcome | null;
	/** Vigilância sanitária: the inspector's visit of the running event. */
	inspection?: InspectionRun | null;
	/** Engarrafamento: the drinks asked through car windows during the running event. */
	windowSales?: WindowSalesState | null;
	/** The approval seal on the door: until the end of this turn (turn key). */
	sealTurnKey?: string | null;
};

/** The market turn the events run in: events only run while it is open and never outlast it. */
export type GameEventTurn = {
	endsAt: number;
	key: string;
	open: boolean;
	startedAt: number;
};
