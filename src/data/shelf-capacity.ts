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

function getNextLegacyShelfSlotUpgrade(unlockedSlots: number) {
	const nextUnlockedSlots = unlockedSlots + 1;
	const configuredUpgrade = shelfSlotUpgrades.find(
		(upgrade) => upgrade.unlockedSlots === nextUnlockedSlots,
	);

	if (configuredUpgrade) {
		return configuredUpgrade;
	}

	if (!lastShelfSlotUpgrade || nextUnlockedSlots <= 7) {
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

export function getNextShelfUnlockUpgrade(unlockedShelves: number) {
	const nextUnlockedShelves = unlockedShelves + 1;

	if (nextUnlockedShelves > maximumShelfCount) {
		return null;
	}

	const legacyUpgrade = getNextLegacyShelfSlotUpgrade(
		unlockedShelves * productsPerShelf,
	);

	return legacyUpgrade
		? ({
				coinCost: legacyUpgrade.coinCost,
				playerLevel: legacyUpgrade.playerLevel,
				unlockedShelves: nextUnlockedShelves,
			} satisfies ShelfUnlockUpgrade)
		: null;
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
