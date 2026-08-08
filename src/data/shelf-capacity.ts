import type {
	ShelfCapacityUpgrade,
	ShelfSlotUpgrade,
} from "@/@types/shelf-capacity";

export const initialUnlockedShelfSlots = 4;

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

export const shelfSlotUpgrades: ShelfSlotUpgrade[] = [
	{ coinCost: 600, playerLevel: 3, unlockedSlots: 5 },
	{ coinCost: 2_500, playerLevel: 6, unlockedSlots: 6 },
	{ coinCost: 9_000, playerLevel: 10, unlockedSlots: 7 },
];

export function getNextShelfSlotUpgrade(unlockedSlots: number) {
	return (
		shelfSlotUpgrades.find(
			(upgrade) => upgrade.unlockedSlots === unlockedSlots + 1,
		) ?? null
	);
}

export function normalizeUnlockedShelfSlots(unlockedSlots: unknown) {
	const maximumSlots =
		shelfSlotUpgrades.at(-1)?.unlockedSlots ?? initialUnlockedShelfSlots;

	if (typeof unlockedSlots !== "number" || !Number.isFinite(unlockedSlots)) {
		return initialUnlockedShelfSlots;
	}

	return Math.min(
		maximumSlots,
		Math.max(initialUnlockedShelfSlots, Math.floor(unlockedSlots)),
	);
}
