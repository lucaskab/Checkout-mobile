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
	category: string;
	demand: number;
	emoji: string;
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
	unlockLevel: number;
	visualAttractiveness: number;
	xpPerSale: number;
};
