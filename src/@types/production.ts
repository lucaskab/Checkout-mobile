export type ProductionSectorId =
	| "padaria"
	| "queijaria"
	| "acougue"
	| "peixaria"
	| "bebidas"
	| "sorvetes"
	| "adega";

export type ProductionIngredient = {
	productId: number;
	quantity: number;
};

export type ProductionRecipe = {
	durationMs: number;
	id: string;
	ingredients: ProductionIngredient[];
	outputProductId: number;
	outputQuantity: number;
	requiredLevel: number;
	sectorId: ProductionSectorId;
};

export type ProductionEconomy = {
	craftedBatchRevenue: number;
	ingredientPurchaseCost: number;
	ingredientSaleValue: number;
	opportunityProfit: number;
	productionUnitCost: number;
	savingsPercent: number;
	supplierUnitPrice: number;
};

export type ProductionSector = {
	description: string;
	id: ProductionSectorId;
	name: string;
	requiredLevel: number;
	slotCount: number;
	subtitle: string;
};

export type ProductionJob = {
	endsAt: number;
	id: string;
	outputProductId: number;
	outputQuantity: number;
	recipeId: string;
	sectorId: ProductionSectorId;
	slotIndex: number;
	startedAt: number;
};

export type GameProductionState = {
	jobs: ProductionJob[];
	totalCrafted: number;
};

export type StartProductionInput = {
	recipeId: string;
	sectorId: ProductionSectorId;
};
