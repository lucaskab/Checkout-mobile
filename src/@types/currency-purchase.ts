export type CurrencyPackCategory = "bundle" | "coins" | "diamonds";

export type CurrencyPack = {
	badge: string;
	category: CurrencyPackCategory;
	coins: number;
	diamonds: number;
	fallbackPrice: string;
	id: string;
	name: string;
	productId: string;
	tier: number;
	/** Coin packs and combos: 10-minute turns of profit of the player's expansion (src/data/currency-packs.ts). */
	coinTurns?: number;
	/** Sold once per player (the welcome combo). */
	oncePerPlayer?: boolean;
};

export type CurrencyPurchaseState = {
	processedTransactionIds: string[];
	/** Packs bought (by pack id, one entry per purchase): the one-time offers check it. */
	purchasedPackIds?: string[];
};

/** What a store purchase credited (CheckoutIap / the RN store show it). */
export type CurrencyPackGrant = { packId: string; coins: number; diamonds: number };

export type GrantCurrencyPurchaseInput = {
	coins: number;
	diamonds: number;
	transactionId: string;
};

export type RevenueCatStoreStatus =
	| "loading"
	| "missing-configuration"
	| "ready"
	| "unavailable";
