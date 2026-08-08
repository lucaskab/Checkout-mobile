export type ShopCategory =
	| "equipamentos"
	| "tecnologia"
	| "marketing"
	| "logistica"
	| "decoracao"
	| "premium"
	| "consumiveis"
	| "lendarios";

export type ShopCurrency = "coins" | "diamonds";

export type ShopItemQuality =
	| "comum"
	| "incomum"
	| "raro"
	| "epico"
	| "lendario"
	| "mitico";

export type ShopItemDefinition = {
	category: ShopCategory;
	coinPrice?: number;
	description: string;
	diamondPrice?: number;
	id: string;
	isConsumable?: boolean;
	level: number;
	name: string;
	quality?: ShopItemQuality;
};

export type GameShopState = {
	consumableAmounts: Record<string, number>;
	ownedItemIds: string[];
};
