import type { GameShelfSlotCounts } from "@/@types/game";
import { shelves } from "./market-products";
import { isSectorShelfId, sectorCounters } from "./shelf-types";

/** Each production sector sells at its own counter: a "shelf" that opens when the sector is built. */
export const sectorShelves = sectorCounters.map((counter) => ({ id: counter.id as string, name: counter.name }));
/** Every place products can be sold: the shelves (in opening order) and the sector counters. */
export const allFixtures = [...shelves, ...sectorShelves];

export const productsPerShelf = 4;
export const maximumSlotsPerShelf = 7;
export const maximumShelfCount = shelves.length;
export const maximumShelfSlots = allFixtures.length * maximumSlotsPerShelf;

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
	return allFixtures.reduce(
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

	const counts = Object.fromEntries(
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
	// Shelves open in order. When the order changes (the drinks cooler moved up to the third place), a shelf
	// left locked before an open one opens too, so older saves never end up with a gap.
	const last = shelves.reduce((found, shelf, index) => (counts[shelf.id] > 0 ? index : found), -1);
	for (let index = 0; index < last; index++)
		if (counts[shelves[index].id] <= 0) counts[shelves[index].id] = productsPerShelf;
	// Sector counters open with their sector, in any order.
	for (const counter of sectorShelves) {
		const persisted = persistedCounts?.[counter.id];
		counts[counter.id] =
			typeof persisted === "number" && Number.isFinite(persisted) && persisted > 0
				? Math.min(maximumSlotsPerShelf, Math.max(productsPerShelf, Math.floor(persisted)))
				: 0;
	}
	return counts;
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

export const shelfProductSlots = allFixtures.flatMap((shelf) =>
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
	const physicalShelfIndex = allFixtures.findIndex(
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
			!isSectorShelfId(physicalShelfId) &&
			physicalShelfIndex < getUnlockedPhysicalShelfCount(shelfSlotCounts) &&
			slotIndex < productsPerShelf
		);
	}

	return slotIndex < getShelfSlotCount(physicalShelfId, shelfSlotCounts);
}
