export type MarketEraId =
	| "mesinha"
	| "banca"
	| "tenda"
	| "conteiner"
	| "spati"
	| "mercadinho"
	| "supermercado"
	| "hipermercado"
	| "rede";

/** One stage of the market, from the table on the sidewalk to the chain of hypermarkets. */
export type MarketEraDefinition = {
	id: MarketEraId;
	/** 0 = mesinha … 8 = rede. */
	index: number;
	name: string;
	/** Coins to evolve INTO this era (0 for the first one). */
	coinCost: number;
	/** Real-world day of play where a regular player should reach it (balance target). */
	targetDay: number;
	/** Real time the builders take to set it up. */
	buildDurationMs: number;
	/** Product places on sale (tables, crates, shelf slots). */
	productSlots: number;
	/** Customers arrive this many times faster than the base rate. */
	arrivalMultiplier: number;
	/** Bigger baskets of pricier goods: scales budgets, prices and costs together. */
	ticketMultiplier: number;
	/**
	 * While the player is away the market keeps selling: each hour away earns this many turns' worth of
	 * profit (up to OFFLINE_CAP_MS per absence). 0 = nobody minds the stall.
	 */
	offlineTurnsPerHour: number;
	/** Price of the first upgrade of any item in this era (then ×ITEM_COST_GROWTH per level). */
	itemUpgradeBaseCost: number;
	/** Opens a night turn with its own customers (Späti and later). */
	nightTurn: boolean;
};

/** The evolution to the next era being built (it opens when the builders finish). */
export type MarketEraConstruction = {
	eraId: MarketEraId;
	startedAt: number;
	endsAt: number;
};

export type GameEraState = {
	id: MarketEraId;
	construction: MarketEraConstruction | null;
	/** Profit of a typical finished turn (moving average): what an hour away is worth. */
	averageTurnProfit: number;
	/** Customers of a typical finished turn (moving average), for the offline summary. */
	averageTurnCustomers: number;
};
