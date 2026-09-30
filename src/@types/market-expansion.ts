export type MarketExpansionId =
	| "fresh-wing"
	| "service-wing"
	| "stock-annex"
	| "premium-hall"
	| "grand-warehouse";

export type MarketExpansionCurrency = "coins" | "diamonds";

export type MarketExpansionDefinition = {
	coinCost: number;
	diamondCost: number;
	description: string;
	id: MarketExpansionId;
	name: string;
	requiredLevel: number;
	/** How long the building works take once the expansion is paid for. */
	buildDurationMs: number;
	/** Areas that must already be built (the central warehouse replaces the small depot). */
	requiresExpansionIds?: MarketExpansionId[];
};

/** The expansion currently being built: it only joins the market once `endsAt` has passed
 * (or the player speeds it up with diamonds). Only one construction runs at a time. */
export type MarketExpansionConstruction = {
	expansionId: MarketExpansionId;
	startedAt: number;
	endsAt: number;
};
