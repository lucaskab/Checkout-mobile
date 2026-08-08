import type { SupplierOrderSlotUpgrade } from "@/@types/supplier-capacity";

export const initialSupplierOrderSlots = 3;

export const supplierOrderSlotUpgrades: SupplierOrderSlotUpgrade[] = [
	{ coinCost: 800, diamondCost: 5, playerLevel: 3, slots: 4 },
	{ coinCost: 3_000, diamondCost: 12, playerLevel: 6, slots: 5 },
	{ coinCost: 10_000, diamondCost: 25, playerLevel: 10, slots: 6 },
	{ coinCost: 30_000, diamondCost: 45, playerLevel: 14, slots: 7 },
	{ coinCost: 75_000, diamondCost: 75, playerLevel: 20, slots: 8 },
];

export function getNextSupplierOrderSlotUpgrade(slots: number) {
	return (
		supplierOrderSlotUpgrades.find((upgrade) => upgrade.slots === slots + 1) ??
		null
	);
}

export function normalizeSupplierOrderSlots(slots: unknown) {
	const maximumSlots =
		supplierOrderSlotUpgrades.at(-1)?.slots ?? initialSupplierOrderSlots;

	if (typeof slots !== "number" || !Number.isFinite(slots)) {
		return initialSupplierOrderSlots;
	}

	return Math.min(
		maximumSlots,
		Math.max(initialSupplierOrderSlots, Math.floor(slots)),
	);
}
