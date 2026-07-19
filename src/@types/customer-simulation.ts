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
};

export type MarketVisitOptions = {
	products: MarketSimulationProduct[];
	seed: number;
	storeReputation: number;
};
