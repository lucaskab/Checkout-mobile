import { getBoxCount, getCaseSize } from "@/data/case-sizes";
import { getInventoryBoxCapacity } from "@/data/inventory-capacity";

// The stockroom keeps supplier boxes: each product has a number of box places on the racks
// (src/data/inventory-capacity.ts). A box opened for the shelves keeps its place until it is empty, so the
// places in use are the boxes the stock fills, rounded up.

type Product = { id: number; category: string; caseSize?: number };

/** Box places of `product` in use by `units` in stock. */
export function getStoredBoxes(product: Product, units: number) {
	return getBoxCount(units, getCaseSize(product));
}

/** Free box places for `product`, after what is in stock and what is on the way (`incomingUnits`). */
export function getFreeBoxPlaces(product: Product, units: number, upgradeLevel: number | undefined, incomingUnits = 0) {
	const caseSize = getCaseSize(product);
	return Math.max(
		0,
		getInventoryBoxCapacity(upgradeLevel ?? 0) - getBoxCount(units, caseSize) - getBoxCount(incomingUnits, caseSize),
	);
}

/** Units that can still go into the stockroom as whole boxes. */
export function getStockroomRoom(product: Product, units: number, upgradeLevel: number | undefined, incomingUnits = 0) {
	return getFreeBoxPlaces(product, units, upgradeLevel, incomingUnits) * getCaseSize(product);
}
