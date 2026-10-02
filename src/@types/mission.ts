import type { MarketEraId } from "@/@types/economy";

export type MissionCategory =
	| "customers"
	| "inventory"
	| "management"
	| "production"
	| "progression"
	| "sales";

export type MissionMetric =
	| "customersServed"
	| "customersWhoBought"
	| "expansion"
	| "inventoryProduct"
	| "inventoryUnits"
	| "level"
	| "productLevels"
	| "productionCrafted"
	| "revenue"
	| "shelfUpgrades"
	| "soldProduct"
	| "uniqueProductsSold"
	| "unitsSold";

export type MissionRewardItem = {
	productId: number;
	quantity: number;
};

export type MissionReward = {
	coins: number;
	items?: MissionRewardItem[];
};

export type MissionDefinition = {
	category: MissionCategory;
	description: string;
	goal: number;
	id: string;
	metric: MissionMetric;
	requiredLevel: number;
	/** Only shows from this expansion on (missions of each expansion). */
	requiredEra?: MarketEraId;
	reward: MissionReward;
	targetProductId?: number;
	title: string;
};

export type GameMissionsState = {
	claimedMissionIds: string[];
};

export type MissionStatus = "active" | "claimable" | "claimed" | "locked";
