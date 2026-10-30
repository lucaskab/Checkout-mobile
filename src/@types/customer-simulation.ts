export type CustomerArchetype =
	| "economico"
	| "normal"
	| "impulsivo"
	| "familia"
	| "premium";

export type CustomerMood = "calmo" | "com-pressa" | "feliz" | "estressado";

export type CustomerProfile = {
	archetype: CustomerArchetype;
	budget: number;
	id: string;
	impulsivity: number;
	loyalty: number;
	mood: CustomerMood;
	priceSensitivity: number;
};

export type SimulatedProduct = {
	category: string;
	marketPrice: number;
	name: string;
	necessity: number;
	popularity?: number;
	preferredCustomers?: CustomerArchetype[];
	promotionRate: number;
	sellingPrice: number;
	visualAttractiveness?: number;
};

export type PurchaseDecision = {
	chance: number;
	customer: CustomerProfile;
	didBuy: boolean;
	marketDifference: number;
	pricePenalty: number;
	quantity: number;
	score: number;
};

export type SimulationResult = {
	averageChance: number;
	conversionRate: number;
	decisions: PurchaseDecision[];
	revenue: number;
	totalUnits: number;
};

export type SimulationOptions = {
	customerCount: number;
	product: SimulatedProduct;
	seed: number;
	storeReputation: number;
};

export type MarketSimulationProduct = SimulatedProduct & {
	availableQuantity: number;
	productId: number;
	shelfId: string;
};

export type MarketPurchase = {
	productId: number;
	quantity: number;
	revenue: number;
	shelfId: string;
};

export type MarketVisit = {
	customer: CustomerProfile;
	purchases: MarketPurchase[];
	revenue: number;
	totalUnits: number;
	/** What the customer carried (only when the visit was given the market's stations). */
	carrier?: import("./fixture-tiers").CartCarrier;
	/** Extra products the customer planned and left behind: no basket or cart big enough. */
	cartShortfall?: number;
};

export type MarketVisitOptions = {
	budgetMultiplier?: number;
	maxProductsBonus?: number;
	products: MarketSimulationProduct[];
	revenueMultiplier?: number;
	/** Extra revenue share by product category (shop upgrades such as the drinks fridge). */
	categoryRevenueBonuses?: Record<string, number>;
	seed: number;
	storeReputation: number;
	/**
	 * Basket and cart stations in the market. Given, the customer plans 0..+4 extra products by archetype and takes
	 * the smallest carrier that holds them (src/data/fixture-tiers.ts). Left out: the old fixed bonus only.
	 */
	carriers?: import("./fixture-tiers").CartCarrier[];
};
