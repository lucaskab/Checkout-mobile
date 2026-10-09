export type ShopCategory =
	| "equipamentos"
	| "tecnologia"
	| "marketing"
	| "logistica"
	| "decoracao"
	| "premium"
	| "consumiveis";

export type ShopCurrency = "coins" | "diamonds";

export type ShopItemQuality =
	| "comum"
	| "incomum"
	| "raro"
	| "epico"
	| "lendario"
	| "mitico";

/**
 * What an upgrade does, in one place (src/services/shop-effects.ts adds them up). The item's
 * description must say exactly this: every number here is the one the player reads.
 */
export type ShopItemEffect = {
	/** +share of customers: they come more often and more of them fit in a turn (0.05 = +5%). */
	customers?: number;
	/** Extra products each customer may put in the basket. */
	basketItems?: number;
	/** +share of the money of every sale (0.05 = +5%). */
	revenue?: number;
	/** +share of the money of sales in these product categories only. */
	categoryRevenue?: { categories: string[]; bonus: number };
	/** The working cashier (and the counter) rings customers up this many times as fast. */
	cashierSpeed?: number;
	/** Customers who ring themselves up, in cashier-efficiency units (1 = one every 9 s), cashier or not. */
	selfCheckout?: number;
	/** Customers wait this many times as long in line before giving up. */
	checkoutPatience?: number;
	/** The stock clerk carries this share more per trip (0.25 = +25%). */
	restock?: number;
	/** Suppliers charge this share less (0.05 = 5% cheaper). */
	supplierDiscount?: number;
	/** Deliveries take this many times as long (0.75 = 25% faster). */
	deliveryTime?: number;
	/** Points added to the store's reputation. */
	reputation?: number;
	/** +share of the coins earned while away (0.25 = +25%). */
	offline?: number;
};

export type ShopItemDefinition = {
	category: ShopCategory;
	coinPrice?: number;
	description: string;
	diamondPrice?: number;
	/** Passive effect while owned (or while the booster runs). */
	effect?: ShopItemEffect;
	id: string;
	isConsumable?: boolean;
	/** Boosters: how long one use lasts. */
	durationMs?: number;
	level: number;
	name: string;
	quality?: ShopItemQuality;
	/** Another upgrade that must be installed first. */
	requiresItemId?: string;
};

export type GameShopState = {
	/** Boosters bought and not used yet. */
	consumableAmounts: Record<string, number>;
	/** Boosters running now: item id → when it ends (ms). */
	activeBoosts: Record<string, number>;
	ownedItemIds: string[];
};
