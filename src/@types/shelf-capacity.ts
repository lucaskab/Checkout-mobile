export type ShelfUpgradeCurrency = "coins" | "diamonds";

export type ShelfCapacityUpgrade = {
	capacity: number;
	coinCost: number;
	diamondCost: number;
	playerLevel: number;
};
