export type ShelfUpgradeCurrency = "coins" | "diamonds";

export type ShelfCapacityUpgrade = {
	capacity: number;
	coinCost: number;
	diamondCost: number;
	playerLevel: number;
};

export type ShelfSlotUpgrade = {
	coinCost: number;
	playerLevel: number;
	unlockedSlots: number;
};

export type ShelfUnlockUpgrade = {
	coinCost: number;
	playerLevel: number;
	unlockedShelves: number;
};
