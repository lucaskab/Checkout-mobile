import type { GameShelfSlotCounts } from "@/@types/game";
import { shelves } from "./market-products";

export const productsPerShelf = 4;
export const maximumSlotsPerShelf = 7;
export const maximumShelfCount = shelves.length;
export const maximumShelfSlots = maximumShelfCount * maximumSlotsPerShelf;

// The first slot retains the original ID, preserving existing saves and prices.
export function getShelfSlotIds(shelfId: string, slotCount = productsPerShelf) {
	if (slotCount <= 0) {
		return [];
	}

	const normalizedSlotCount = Math.min(
		maximumSlotsPerShelf,
		Math.max(productsPerShelf, Math.floor(slotCount)),
	);

	return [
		shelfId,
		...Array.from(
			{ length: normalizedSlotCount - 1 },
			(_, index) => `${shelfId}:${index + 1}`,
		),
	];
}

export function getPhysicalShelfId(slotId: string) {
	return slotId.split(":")[0];
}

export function getShelfSlotCount(
	shelfId: string,
	shelfSlotCounts: GameShelfSlotCounts | undefined,
) {
	const slotCount = shelfSlotCounts?.[shelfId];

	if (typeof slotCount !== "number" || !Number.isFinite(slotCount)) {
		return 0;
	}

	return slotCount <= 0
		? 0
		: Math.min(
				maximumSlotsPerShelf,
				Math.max(productsPerShelf, Math.floor(slotCount)),
			);
}

export function getUnlockedPhysicalShelfCount(
	value: number | GameShelfSlotCounts,
) {
	if (typeof value === "number") {
		return Math.min(
			maximumShelfCount,
			Math.ceil(Math.max(0, value) / productsPerShelf),
		);
	}

	let unlockedCount = 0;
	for (const shelf of shelves) {
		if (getShelfSlotCount(shelf.id, value) <= 0) {
			break;
		}

		unlockedCount += 1;
	}

	return unlockedCount;
}

export function getTotalUnlockedShelfSlots(
	shelfSlotCounts: GameShelfSlotCounts,
) {
	return shelves.reduce(
		(total, shelf) => total + getShelfSlotCount(shelf.id, shelfSlotCounts),
		0,
	);
}

export function normalizeShelfSlotCounts(
	persistedCounts: Partial<GameShelfSlotCounts> | undefined,
	legacyUnlockedShelfSlots: unknown,
) {
	const legacyShelfCount =
		typeof legacyUnlockedShelfSlots === "number" &&
		Number.isFinite(legacyUnlockedShelfSlots)
			? Math.max(1, getUnlockedPhysicalShelfCount(legacyUnlockedShelfSlots))
			: 1;

	return Object.fromEntries(
		shelves.map((shelf, index) => {
			const persistedCount = persistedCounts?.[shelf.id];
			const defaultCount = index < legacyShelfCount ? productsPerShelf : 0;

			if (
				typeof persistedCount !== "number" ||
				!Number.isFinite(persistedCount)
			) {
				return [shelf.id, defaultCount];
			}

			return [
				shelf.id,
				persistedCount <= 0
					? 0
					: Math.min(
							maximumSlotsPerShelf,
							Math.max(productsPerShelf, Math.floor(persistedCount)),
						),
			];
		}),
	) as GameShelfSlotCounts;
}

export function resolveShelfSlotCounts(
	persistedCounts: Partial<GameShelfSlotCounts> | undefined,
	legacyUnlockedShelfSlots: unknown,
) {
	const normalizedCounts = normalizeShelfSlotCounts(
		persistedCounts,
		legacyUnlockedShelfSlots,
	);
	const persistedTotal = persistedCounts
		? Object.values(persistedCounts).reduce<number>(
				(total, count) =>
					total +
					(typeof count === "number" && Number.isFinite(count) ? count : 0),
				0,
			)
		: null;

	if (
		persistedTotal !== null &&
		typeof legacyUnlockedShelfSlots === "number" &&
		Math.floor(persistedTotal) === Math.floor(legacyUnlockedShelfSlots)
	) {
		return normalizedCounts;
	}

	return normalizeShelfSlotCounts(undefined, legacyUnlockedShelfSlots);
}

export const shelfProductSlots = shelves.flatMap((shelf) =>
	getShelfSlotIds(shelf.id, maximumSlotsPerShelf).map((id) => ({
		...shelf,
		id,
	})),
);

export function isShelfSlotUnlocked(
	slotId: string,
	shelfSlotCounts: number | GameShelfSlotCounts,
) {
	const physicalShelfId = getPhysicalShelfId(slotId);
	const physicalShelfIndex = shelves.findIndex(
		(shelf) => shelf.id === physicalShelfId,
	);
	const slotIndex = getShelfSlotIds(
		physicalShelfId,
		maximumSlotsPerShelf,
	).indexOf(slotId);

	if (physicalShelfIndex < 0 || slotIndex < 0) {
		return false;
	}

	if (typeof shelfSlotCounts === "number") {
		return (
			physicalShelfIndex < getUnlockedPhysicalShelfCount(shelfSlotCounts) &&
			slotIndex < productsPerShelf
		);
	}

	return slotIndex < getShelfSlotCount(physicalShelfId, shelfSlotCounts);
}
