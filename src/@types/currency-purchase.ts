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
};

export type CurrencyPurchaseState = {
	processedTransactionIds: string[];
};

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
