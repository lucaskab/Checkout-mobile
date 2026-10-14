// Suppliers sell in boxes and every box holds the same 5 units, whatever the product (Lucas 14/10: "sempre venha
// cinco"). A shelf spot starts with room for 5 too (src/data/shelf-capacity.ts), so a shelf that runs out takes
// exactly one box, and every capacity upgrade adds whole boxes. The player orders and pays per box; the
// stockroom keeps the boxes and the shelves are filled from them (src/stores/game-store.ts restockShelf).

/** Units in every supplier box. */
export const UNITS_PER_BOX = 5;

/** Units in one supplier box of this product. */
export function getCaseSize(product: { id: number; category: string; caseSize?: number }) {
	void product;
	return UNITS_PER_BOX;
}

/** How many whole boxes `units` fill (a box that is partly used still counts as one). */
export function getBoxCount(units: number, caseSize: number) {
	return units <= 0 ? 0 : Math.ceil(units / Math.max(1, caseSize));
}
