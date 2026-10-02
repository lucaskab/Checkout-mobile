import type { CustomerArchetype } from "./customer-simulation";

export type ItemRarity =
	| "comum"
	| "incomum"
	| "raro"
	| "epico"
	| "lendario"
	| "luxo"
	| "colecionavel";

export type SaleVelocity = "lenta" | "media" | "rapida" | "muito-rapida";

export type ItemDefinition = {
	acquisition: "production" | "supplier";
	category: string;
	demand: number;
	expirationHours: number | null;
	id: number;
	maxPrice: number;
	minPrice: number;
	name: string;
	popularity: number;
	preferredCustomers: CustomerArchetype[];
	profitPerUnit: number;
	purchasePrice: number;
	rarity: ItemRarity;
	recommendedStock: number;
	restockFrequency: "alta" | "media" | "baixa";
	reputation: number;
	saleVelocity: SaleVelocity;
	sellingPrice: number;
	shelfId?: string;
	shelfSpace: number;
	spoilChance: number;
	supplierQuantity: number;
	supplierTime: string;
	suggestedPrice: number;
	/** Expansion from which the product can be sold (src/data/economy.ts marketEras). */
	unlockEra: import("./economy").MarketEraId;
	unlockLevel: number;
	visualAttractiveness: number;
	xpPerSale: number;
};
