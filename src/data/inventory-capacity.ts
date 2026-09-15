import type { InventoryCapacityUpgrade } from "@/@types/inventory-capacity";
import type { ItemDefinition } from "@/@types/item";

export const inventoryCapacityUpgrades: InventoryCapacityUpgrade[] = [
	{ coinCost: 600, playerLevel: 3, storageBonus: 10 },
	{ coinCost: 2_400, playerLevel: 6, storageBonus: 25 },
	{ coinCost: 8_000, playerLevel: 10, storageBonus: 45 },
	{ coinCost: 22_000, playerLevel: 15, storageBonus: 70 },
];

export function getInventoryCapacity(
	_product: Pick<ItemDefinition, "id">,
	upgradeLevel = 0,
) {
	const baseCapacity = 5;
	const upgrade =
		upgradeLevel > 0 ? inventoryCapacityUpgrades[upgradeLevel - 1] : undefined;

	return baseCapacity + (upgrade?.storageBonus ?? 0);
}

export function getNextInventoryCapacityUpgrade(upgradeLevel = 0) {
	return inventoryCapacityUpgrades[upgradeLevel] ?? null;
}

export function normalizeInventoryCapacityLevel(upgradeLevel: unknown) {
	if (typeof upgradeLevel !== "number" || !Number.isFinite(upgradeLevel)) {
		return 0;
	}

	return Math.min(
		inventoryCapacityUpgrades.length,
		Math.max(0, Math.floor(upgradeLevel)),
	);
}
