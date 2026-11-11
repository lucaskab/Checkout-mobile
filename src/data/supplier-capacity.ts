import type { MarketEraId } from "@/@types/economy";
import { getMarketEra } from "@/data/economy";

// Supplier trucks (Lucas 11/11): the player starts with ONE truck. More come for free with the player's level and
// with the expansions of the market, and a few more can be bought with diamonds. One truck carries one order
// (a cart with several products), so the trucks are how many orders can be on the road at the same time.
//
// `logistics.supplierOrderSlots` keeps the trucks the player OWNS outright: the first one, the ones bought with
// diamonds and, for saves from before 11/11, the trucks they already had (save 53 moves them here, so nobody
// loses a truck). The free ones are not saved: they follow the level and the expansion (getEarnedTrucks).

export const initialSupplierOrderSlots = 1;
/** No more trucks than this, however they came. */
export const MAX_SUPPLIER_TRUCKS = 10;

export type TruckUnlock = { kind: "level"; level: number } | { kind: "era"; eraId: MarketEraId };

/** The free trucks, in the order a player usually reaches them. */
export const truckUnlocks: readonly TruckUnlock[] = [
	{ kind: "level", level: 4 },
	{ kind: "era", eraId: "banca" },
	{ kind: "level", level: 9 },
	{ kind: "era", eraId: "quitanda" },
	{ kind: "level", level: 16 },
	{ kind: "era", eraId: "mercadinho" },
	{ kind: "level", level: 24 },
	{ kind: "era", eraId: "hipermercado" },
];

/** Diamonds for each truck bought (the first bought costs the first price). */
export const truckDiamondPrices: readonly number[] = [15, 30, 50];

type TruckState = {
	logistics: { supplierOrderSlots: number };
	market: { level: number };
	era?: { id: string } | null;
};

const eraIndex = (id: string | undefined) => {
	try {
		return id ? (getMarketEra(id as MarketEraId)?.index ?? 0) : 0;
	} catch {
		return 0;
	}
};

export function isTruckUnlockReached(unlock: TruckUnlock, level: number, eraId: string | undefined) {
	return unlock.kind === "level" ? level >= unlock.level : eraIndex(eraId) >= eraIndex(unlock.eraId);
}

/** Free trucks the level and the expansion give now. */
export function getEarnedTrucks(level: number, eraId: string | undefined) {
	return truckUnlocks.filter((unlock) => isTruckUnlockReached(unlock, level, eraId)).length;
}

/** The trucks the player can send to the suppliers now. */
export function getSupplierTrucks(state: TruckState) {
	return Math.min(
		MAX_SUPPLIER_TRUCKS,
		normalizeSupplierOrderSlots(state.logistics?.supplierOrderSlots) +
			getEarnedTrucks(state.market?.level ?? 1, state.era?.id),
	);
}

/** The next free truck still to come (null when every one has come). */
export function getNextTruckUnlock(state: TruckState): TruckUnlock | null {
	if (getSupplierTrucks(state) >= MAX_SUPPLIER_TRUCKS) return null;
	return truckUnlocks.find((unlock) => !isTruckUnlockReached(unlock, state.market?.level ?? 1, state.era?.id)) ?? null;
}

/** Diamonds for one more truck now, or null when no more can be bought. */
export function getNextTruckDiamondPrice(state: TruckState) {
	if (getSupplierTrucks(state) >= MAX_SUPPLIER_TRUCKS) return null;
	const bought = normalizeSupplierOrderSlots(state.logistics?.supplierOrderSlots) - initialSupplierOrderSlots;
	return truckDiamondPrices[bought] ?? null;
}

/** Save 53: the trucks a save from before had stay (the free ones are counted again, the rest becomes owned). */
export function migrateOwnedTrucks(oldSlots: unknown, level: number, eraId: string | undefined) {
	const old = typeof oldSlots === "number" && Number.isFinite(oldSlots) ? Math.floor(oldSlots) : 3;
	return normalizeSupplierOrderSlots(Math.max(initialSupplierOrderSlots, old - getEarnedTrucks(level, eraId)));
}

// A truck holds 10 boxes at the start, two more for every truck past the third.
export function getMaxBoxesPerOrder(trucks: number) {
	return 10 + 2 * Math.max(0, trucks - 3);
}

export function normalizeSupplierOrderSlots(slots: unknown) {
	if (typeof slots !== "number" || !Number.isFinite(slots)) return initialSupplierOrderSlots;
	return Math.min(MAX_SUPPLIER_TRUCKS, Math.max(initialSupplierOrderSlots, Math.floor(slots)));
}
