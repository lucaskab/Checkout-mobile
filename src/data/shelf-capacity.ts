import type {
	ShelfCapacityUpgrade,
	ShelfSlotUpgrade,
	ShelfUnlockUpgrade,
} from "@/@types/shelf-capacity";
import {
	maximumShelfCount,
	maximumShelfSlots,
	maximumSlotsPerShelf,
	productsPerShelf,
} from "@/data/shelf-slots";
import { shelfTypes } from "@/data/shelf-types";


export const initialUnlockedShelfSlots = productsPerShelf;

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
const lastShelfSlotUpgrade = shelfSlotUpgrades.at(-1);

export function getNextShelfSlotUpgrade(unlockedSlots: number) {
	const nextUnlockedSlots = unlockedSlots + 1;
	const configuredUpgrade = shelfSlotUpgrades.find(
		(upgrade) => upgrade.unlockedSlots === nextUnlockedSlots,
	);

	if (configuredUpgrade) {
		return configuredUpgrade;
	}

	if (
		!lastShelfSlotUpgrade ||
		nextUnlockedSlots > maximumSlotsPerShelf ||
		unlockedSlots < lastShelfSlotUpgrade.unlockedSlots
	) {
		return null;
	}

	const progressionStep =
		nextUnlockedSlots - lastShelfSlotUpgrade.unlockedSlots;

	return {
		coinCost:
			Math.round(
				(lastShelfSlotUpgrade.coinCost * 1.8 ** progressionStep) / 100,
			) * 100,
		playerLevel: lastShelfSlotUpgrade.playerLevel + progressionStep * 4,
		unlockedSlots: nextUnlockedSlots,
	} satisfies ShelfSlotUpgrade;
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
