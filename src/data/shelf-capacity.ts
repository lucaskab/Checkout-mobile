import type {
	ShelfCapacityUpgrade,
	ShelfSlotUpgrade,
	ShelfUnlockUpgrade,
} from "@/@types/shelf-capacity";
import {
	maximumShelfCount,
	maximumShelfSlots,
	productsPerShelf,
} from "@/data/shelf-slots";
import { shelfTypes } from "@/data/shelf-types";


export const initialUnlockedShelfSlots = productsPerShelf;

export const shelfCapacityUpgrades: ShelfCapacityUpgrade[] = [
	// Whole supplier boxes (UNITS_PER_BOX = 5): an empty spot always takes full boxes.
	{ capacity: 5, coinCost: 0, diamondCost: 0, playerLevel: 1 },
	{ capacity: 10, coinCost: 1_200, diamondCost: 6, playerLevel: 4 },
	{ capacity: 15, coinCost: 6_000, diamondCost: 14, playerLevel: 8 },
	{ capacity: 20, coinCost: 22_000, diamondCost: 28, playerLevel: 14 },
	{ capacity: 25, coinCost: 70_000, diamondCost: 48, playerLevel: 22 },
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

/**
 * Places for products are no longer bought one by one: they come with the fixture's evolution (T1 4 … ★ 8,
 * src/data/fixture-tiers.ts fixtureTierPlaces; claude/evolucoes-recompensas.md, Lucas 01/11). Kept for the old
 * mobile screens, which then show no "expand" button.
 */
export function getNextShelfSlotUpgrade(_unlockedSlots: number): ShelfSlotUpgrade | null {
	return null;
}

/**
 * The next shelf the player can buy (shelves open in order, src/data/shelf-types.ts): each one comes
 * with the expansion that has room for it and costs a fixed price. `playerLevel` is kept at 1 for the
 * screens that still show a level: the expansion is what gates it.
 */
export function getNextShelfUnlockUpgrade(unlockedShelves: number) {
	const nextUnlockedShelves = unlockedShelves + 1;
	const shelf = shelfTypes[unlockedShelves];
	if (nextUnlockedShelves > maximumShelfCount || !shelf) return null;
	return {
		coinCost: shelf.coinCost,
		playerLevel: 1,
		unlockedShelves: nextUnlockedShelves,
		eraId: shelf.eraId,
		shelfId: shelf.id,
	} satisfies ShelfUnlockUpgrade;
}

export function normalizeUnlockedShelfSlots(unlockedSlots: unknown) {
	if (typeof unlockedSlots !== "number" || !Number.isFinite(unlockedSlots)) {
		return initialUnlockedShelfSlots;
	}

	return Math.min(
		maximumShelfSlots,
		Math.max(initialUnlockedShelfSlots, Math.floor(unlockedSlots)),
	);
}
