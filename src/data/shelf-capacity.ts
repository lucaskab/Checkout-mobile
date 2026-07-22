import type { ShelfCapacityUpgrade } from "@/@types/shelf-capacity";

export const shelfCapacityUpgrades: ShelfCapacityUpgrade[] = [
	{ capacity: 3, coinCost: 0, diamondCost: 0, playerLevel: 1 },
	{ capacity: 5, coinCost: 1_200, diamondCost: 6, playerLevel: 4 },
	{ capacity: 8, coinCost: 6_000, diamondCost: 14, playerLevel: 8 },
	{ capacity: 12, coinCost: 22_000, diamondCost: 28, playerLevel: 14 },
	{ capacity: 17, coinCost: 70_000, diamondCost: 48, playerLevel: 22 },
];

export function getShelfCapacity(upgradeLevel = 0) {
	return (
		shelfCapacityUpgrades[
			Math.min(upgradeLevel, shelfCapacityUpgrades.length - 1)
		]?.capacity ?? shelfCapacityUpgrades[0].capacity
	);
}

export function getNextShelfCapacityUpgrade(upgradeLevel = 0) {
	return shelfCapacityUpgrades[upgradeLevel + 1] ?? null;
}
