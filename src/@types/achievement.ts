export type AchievementCategory =
	| "collection"
	| "customers"
	| "logistics"
	| "management"
	| "production"
	| "progression"
	| "sales"
	| "specialist";

export type AchievementRarity =
	| "common"
	| "uncommon"
	| "rare"
	| "epic"
	| "legendary";

export type AchievementMetric =
	| "customersServed"
	| "customersWhoBought"
	| "experience"
	| "instantDeliveries"
	| "instantProductionFinishes"
	| "level"
	| "marketOpenings"
	| "missionsClaimed"
	| "priceChanges"
	| "productionCrafted"
	| "productionJobsStarted"
	| "productsUnlocked"
	| "revenue"
	| "restockedUnits"
	| "shelfUpgrades"
	| "shopPurchases"
	| "soldProduct"
	| "supplierOrdersPlaced"
	| "uniqueProductsSold"
	| "unitsSold";

export type AchievementDefinition = {
	category: AchievementCategory;
	description: string;
	id: string;
	metric: AchievementMetric;
	rarity: AchievementRarity;
	requiredLevel: number;
	targetProductId?: number;
	thresholds: [number, number, number, number, number];
	title: string;
};

export type GameStatistics = {
	instantDeliveries: number;
	instantProductionFinishes: number;
	marketOpenings: number;
	priceChanges: number;
	productionJobsStarted: number;
	restockedUnits: number;
	shopPurchases: number;
	spoiledUnits: number;
	supplierOrdersPlaced: number;
};
