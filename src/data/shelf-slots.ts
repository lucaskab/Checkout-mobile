import { shelves } from "./market-products";

export const productsPerShelf = 4;

// The first slot retains the original ID, preserving existing saves and prices.
export function getShelfSlotIds(shelfId: string) {
	return [
		shelfId,
		...Array.from(
			{ length: productsPerShelf - 1 },
			(_, index) => `${shelfId}:${index + 1}`,
		),
	];
}

export function getPhysicalShelfId(slotId: string) {
	return slotId.split(":")[0];
}

export const shelfProductSlots = shelves.flatMap((shelf) =>
	getShelfSlotIds(shelf.id).map((id) => ({ ...shelf, id })),
);

export function isShelfSlotUnlocked(slotId: string, unlockedShelves: number) {
	return shelves
		.slice(0, unlockedShelves)
		.some((shelf) => getShelfSlotIds(shelf.id).includes(slotId));
}
