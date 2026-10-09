import type { InventoryCapacityUpgrade } from "@/@types/inventory-capacity";
import type { ItemDefinition } from "@/@types/item";
import { getCaseSize } from "@/data/case-sizes";

// The stockroom holds boxes: each product has room for a number of its supplier boxes (src/data/case-sizes.ts).
// Stock is still counted in units (a box opened for the shelves keeps its loose units), so the capacity in
// units is boxes × units per box.
export const BASE_INVENTORY_BOXES = 2;

export const inventoryCapacityUpgrades: InventoryCapacityUpgrade[] = [
	{ coinCost: 600, playerLevel: 3, storageBonus: 1 },
	{ coinCost: 2_400, playerLevel: 6, storageBonus: 3 },
	{ coinCost: 8_000, playerLevel: 10, storageBonus: 6 },
	{ coinCost: 22_000, playerLevel: 15, storageBonus: 10 },
];

/** Boxes of one product the stockroom can hold at this upgrade level. */
export function getInventoryBoxCapacity(upgradeLevel = 0) {
	const upgrade = upgradeLevel > 0 ? inventoryCapacityUpgrades[upgradeLevel - 1] : undefined;
	return BASE_INVENTORY_BOXES + (upgrade?.storageBonus ?? 0);
}

/** Units of `product` the stockroom can hold (its boxes × units per box). */
export function getInventoryCapacity(
	product: Pick<ItemDefinition, "id"> & Partial<Pick<ItemDefinition, "category" | "caseSize">>,
	upgradeLevel = 0,
) {
	const caseSize = getCaseSize({ id: product.id, category: product.category ?? "", caseSize: product.caseSize });
	return getInventoryBoxCapacity(upgradeLevel) * caseSize;
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
