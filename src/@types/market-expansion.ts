export type MarketExpansionId =
	| "fresh-wing"
	| "service-wing"
	| "stock-annex"
	| "premium-hall";

export type MarketExpansionCurrency = "coins" | "diamonds";

export type MarketExpansionDefinition = {
	coinCost: number;
	diamondCost: number;
	description: string;
	id: MarketExpansionId;
	name: string;
	requiredLevel: number;
};
