import type { InventoryLot } from "@/@types/inventory-lot";
import { itemCatalog } from "@/data/market-products";

export function createInventoryLots(
	productId: number,
	quantity: number,
	now = Date.now(),
): InventoryLot[] {
	if (quantity <= 0) {
		return [];
	}

	const product = itemCatalog.find((item) => item.id === productId);
	const expiresAt = product?.expirationHours
		? now + product.expirationHours * 60 * 60_000
		: null;

	return [{ expiresAt, quantity: Math.floor(quantity) }];
}

export function normalizeInventoryLots(lots: InventoryLot[] | undefined) {
	return (lots ?? [])
		.filter(
			(lot) =>
				Number.isFinite(lot.quantity) &&
				lot.quantity > 0 &&
				(lot.expiresAt === null || Number.isFinite(lot.expiresAt)),
		)
		.map((lot) => ({
			expiresAt: lot.expiresAt,
			quantity: Math.floor(lot.quantity),
		}))
		.sort((left, right) => (left.expiresAt ?? Infinity) - (right.expiresAt ?? Infinity));
}

export function getLotQuantity(lots: InventoryLot[] | undefined) {
	return normalizeInventoryLots(lots).reduce(
		(total, lot) => total + lot.quantity,
		0,
	);
}

export function reconcileInventoryLots(
	productId: number,
	expectedQuantity: number,
	lots: InventoryLot[] | undefined,
	now = Date.now(),
) {
	const normalizedLots = normalizeInventoryLots(lots);
	const expected = Math.max(0, Math.floor(expectedQuantity));
	const tracked = getLotQuantity(normalizedLots);

	if (tracked === expected) {
		return normalizedLots;
	}

	if (tracked < expected) {
		return [...normalizedLots, ...createInventoryLots(productId, expected - tracked, now)];
	}

	return takeInventoryLots(normalizedLots, tracked - expected).remainingLots;
}

export function takeInventoryLots(lots: InventoryLot[] | undefined, quantity: number) {
	let remainingToTake = Math.max(0, Math.floor(quantity));
	const takenLots: InventoryLot[] = [];
	const remainingLots: InventoryLot[] = [];

	for (const lot of normalizeInventoryLots(lots)) {
		const takenQuantity = Math.min(lot.quantity, remainingToTake);

		if (takenQuantity > 0) {
			takenLots.push({ ...lot, quantity: takenQuantity });
			remainingToTake -= takenQuantity;
		}

		if (lot.quantity > takenQuantity) {
			remainingLots.push({ ...lot, quantity: lot.quantity - takenQuantity });
		}
	}

	return { remainingLots, takenLots };
}

export function appendInventoryLots(
	lots: InventoryLot[] | undefined,
	incomingLots: InventoryLot[],
) {
	return normalizeInventoryLots([...(lots ?? []), ...incomingLots]);
}

export function discardExpiredInventoryLots(
	lots: InventoryLot[] | undefined,
	now = Date.now(),
) {
	const expiredLots: InventoryLot[] = [];
	const remainingLots: InventoryLot[] = [];

	for (const lot of normalizeInventoryLots(lots)) {
		if (lot.expiresAt !== null && lot.expiresAt <= now) {
			expiredLots.push(lot);
			continue;
		}

		remainingLots.push(lot);
	}

	return {
		expiredQuantity: getLotQuantity(expiredLots),
		remainingLots,
	};
}

export function getEarliestInventoryExpiry(lots: InventoryLot[] | undefined) {
	return normalizeInventoryLots(lots).find((lot) => lot.expiresAt !== null)
		?.expiresAt ?? null;
}
