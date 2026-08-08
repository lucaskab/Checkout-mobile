export type MarketExpansionId =
	| "fresh-wing"
	| "service-wing"
	| "stock-annex"
	| "premium-hall";

export type MarketExpansionDefinition = {
	coinCost: number;
	description: string;
	id: MarketExpansionId;
	name: string;
	requiredLevel: number;
};
