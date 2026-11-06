import type { MarketEraId } from "@/@types/economy";

// Checkouts and self-checkout kiosks per expansion (Lucas 05/11: "quanto mais o mercado expande, mais pessoas tem, e as
// filas vão ficando maiores"). The market starts with its own checkout (checkout:main); every further checkout is a
// shop fixture bought in Melhorias and placed in build mode, and each one needs its own cashier (one cashier per
// staffed counter: src/stores/game-store.ts hireEmployee / processCheckoutCounter). Kiosks come in pairs and work
// without staff. Unity mirrors the same tables (CheckoutLanes.Counters / KioskPairs).

export type CheckoutFixture = { itemId: string; pieceIds: string[]; era: MarketEraId };

/** The extra checkouts, in the order they open (the main one comes with the market). */
export const extraCheckouts: CheckoutFixture[] = [
	{ itemId: "extra-checkout", pieceIds: ["checkout:extra"], era: "mercadinho" },
	{ itemId: "checkout-3", pieceIds: ["checkout:3"], era: "supermercado" },
	{ itemId: "checkout-4", pieceIds: ["checkout:4"], era: "hipermercado" },
	{ itemId: "checkout-5", pieceIds: ["checkout:5"], era: "rede" },
];

/** Self-checkout kiosks, two per purchase. ("extra-kiosks" was a +rate upgrade with no kiosks of its own: it is the
 * second pair now, so who bought it gets its two kiosks.) */
export const kioskPairs: CheckoutFixture[] = [
	{ itemId: "self-checkout", pieceIds: ["kiosk:1", "kiosk:2"], era: "mercadinho" },
	{ itemId: "extra-kiosks", pieceIds: ["kiosk:3", "kiosk:4"], era: "hipermercado" },
	{ itemId: "kiosks-3", pieceIds: ["kiosk:5", "kiosk:6"], era: "rede" },
];

export const checkoutFixtures = [...extraCheckouts, ...kioskPairs];

/** One customer every 12 s per kiosk (a customer scans more slowly than a trained cashier). */
export const KIOSK_INTERVAL_MS = 12_000;

export function getCheckoutFixture(itemId: string) {
	return checkoutFixtures.find((fixture) => fixture.itemId === itemId) ?? null;
}

/** Built checkouts (the main one + the extra ones finished by the builders: ownership comes with the works' end). */
export function getCheckoutCount(ownedItemIds: readonly string[]) {
	return 1 + extraCheckouts.filter((fixture) => ownedItemIds.includes(fixture.itemId)).length;
}

export function getKioskCount(ownedItemIds: readonly string[]) {
	return kioskPairs.filter((fixture) => ownedItemIds.includes(fixture.itemId)).length * 2;
}

/** How many checkouts / kiosks an expansion can hold (its last fixture's era reached). */
export function getCheckoutCapacity(eraIndex: number, eraIndexOf: (id: MarketEraId) => number) {
	return {
		checkouts: 1 + extraCheckouts.filter((fixture) => eraIndexOf(fixture.era) <= eraIndex).length,
		kiosks: kioskPairs.filter((fixture) => eraIndexOf(fixture.era) <= eraIndex).length * 2,
	};
}
