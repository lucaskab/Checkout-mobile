import type { DayForecast } from "@/services/day-forecast";

// A market day is a turn: pick a contract, open, sell, close and review.
export type MarketDayPhase = "planning" | "open" | "results";

export type DayContractKind =
	| "revenue"
	| "profit"
	| "customers"
	| "satisfaction"
	| "category";

export type DayContractDifficulty = 1 | 2 | 3;

export type DayReward = {
	coins: number;
	diamonds: number;
	experience: number;
};

export type DayContract = {
	category?: string;
	categoryLabel?: string;
	description: string;
	difficulty: DayContractDifficulty;
	icon: string;
	id: string;
	kind: DayContractKind;
	reward: DayReward;
	target: number;
	title: string;
	/** A "Desafio" contract: the third kept in a row is harder and pays more (src/services/contract-pressure.ts). */
	challenge?: boolean;
};

export type DayStats = {
	incidentsFixed: number;
	checkoutsLost: number;
	customers: number;
	profit: number;
	revenue: number;
	satisfactionSamples: number;
	satisfactionTotal: number;
	soldByCategory: Record<string, number>;
	unitsSold: number;
};

export type DayGrade = "S" | "A" | "B" | "C" | "D";

export type DayResult = {
	averageSatisfaction: number;
	bonus: DayReward;
	closedAt: number;
	contract: DayContract | null;
	contractCompleted: boolean;
	contractProgress: number;
	dayNumber: number;
	durationMs: number;
	grade: DayGrade;
	highlights: string[];
	score: number;
	stats: DayStats;
	total: DayReward;
	/** The missed contract's consolation video, once watched: what it gave (null/absent = not yet). */
	consolation?: (DayReward & { label: string }) | null;
};

export type GameDayState = {
	contract: DayContract | null;
	dayNumber: number;
	endsAt: number | null;
	/**
	 * Customer loyalty (0-100): a few more visits per day (getLoyaltyArrivalMultiplier). It only moved with the
	 * customers' special requests, removed from the game (Lucas 29/10), so it is frozen now and not shown anywhere;
	 * saves keep the value they earned (never below INITIAL_LOYALTY) so no market loses customers.
	 */
	loyalty: number;
	offers: DayContract[];
	/** Version of the rules the offers were sized with (DAY_OFFERS_REVISION); older offers are made again. */
	offersRevision?: number;
	phase: MarketDayPhase;
	result: DayResult | null;
	/** Turn of the day: "noite" from the Späti on (other customers, bigger night baskets). */
	shift?: TurnShift;
	startedAt: number | null;
	stats: DayStats;
	/** Contracts kept in a row (>0) or missed in a row (<0): paces the next offers (contract-pressure.ts). */
	contractMomentum?: number;
};

export type TurnShift = "dia" | "noite";

export type DayCatalogProduct = {
	category: string;
	categoryLabel: string;
	id: number;
	name: string;
	purchasePrice: number;
	sellingPrice: number;
};

// What the store can offer right now: products on shelves (with stock) and in storage.
export type DayStoreContext = {
	catalog: DayCatalogProduct[];
	/** What one day of this market should bring (sizes the contracts); see services/day-forecast.ts. */
	forecast?: DayForecast;
	shelfProductIds: number[];
	storageProductIds: number[];
	unlockedProductIds: number[];
};
