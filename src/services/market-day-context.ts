import type { GameState } from "@/@types/game";
import type { DayCatalogProduct, DayStoreContext } from "@/@types/market-day";
import { itemCatalog, itemCategories } from "@/data/market-products";
import {
	isShelfSlotUnlocked,
	resolveShelfSlotCounts,
	shelfProductSlots,
} from "@/data/shelf-slots";

const categoryLabels = new Map<string, string>(
	itemCategories.map((category) => [category.id, category.label]),
);

export const dayCatalog: DayCatalogProduct[] = itemCatalog.map((product) => ({
	category: product.category,
	categoryLabel: categoryLabels.get(product.category) ?? product.category,
	id: product.id,
	name: product.name,
	purchasePrice: product.purchasePrice,
	sellingPrice: product.sellingPrice,
}));

// What customers can find right now, used to build special requests and contracts.
export function getDayStoreContext(
	state: Pick<
		GameState,
		| "inventory"
		| "market"
		| "shelfAssignments"
		| "shelfSlotCounts"
		| "shelfStock"
		| "unlockedShelfSlots"
	>,
): DayStoreContext {
	const counts = resolveShelfSlotCounts(
		state.shelfSlotCounts,
		state.unlockedShelfSlots,
	);
	const unlocked = new Set(state.market.unlockedProductIds);
	const shelfProductIds = Array.from(
		new Set(
			shelfProductSlots.flatMap((slot) => {
				const productId = state.shelfAssignments[slot.id];
				return productId &&
					unlocked.has(productId) &&
					isShelfSlotUnlocked(slot.id, counts) &&
					(state.shelfStock[slot.id] ?? 0) > 0
					? [productId]
					: [];
			}),
		),
	);
	const storageProductIds = Object.entries(state.inventory)
		.filter(([id, quantity]) => quantity > 0 && unlocked.has(Number(id)))
		.map(([id]) => Number(id));
	return {
		catalog: dayCatalog,
		shelfProductIds,
		storageProductIds,
		unlockedProductIds: state.market.unlockedProductIds,
	};
}

export function getDayProduct(productId: number) {
	return dayCatalog.find((product) => product.id === productId);
}
