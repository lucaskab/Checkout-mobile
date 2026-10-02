import type { GameState } from "@/@types/game";
import type { StoreIncidentShelf } from "@/@types/store-incident";
import { itemCatalog } from "@/data/market-products";
import { getFixtureName } from "@/data/shelf-types";
import {
	getPhysicalShelfId,
	isShelfSlotUnlocked,
	resolveShelfSlotCounts,
	shelfProductSlots,
} from "@/data/shelf-slots";

// Physical shelves that hold a product: where mishaps can happen.
export function getIncidentShelves(
	state: Pick<
		GameState,
		| "shelfAssignments"
		| "shelfPrices"
		| "shelfSlotCounts"
		| "shelfStock"
		| "unlockedShelfSlots"
	> & { era?: Pick<GameState["era"], "id"> },
): StoreIncidentShelf[] {
	const counts = resolveShelfSlotCounts(
		state.shelfSlotCounts,
		state.unlockedShelfSlots,
	);
	const byShelf = new Map<string, StoreIncidentShelf>();
	for (const slot of shelfProductSlots) {
		const productId = state.shelfAssignments[slot.id];
		const shelfId = getPhysicalShelfId(slot.id);
		if (!productId || byShelf.has(shelfId) || !isShelfSlotUnlocked(slot.id, counts))
			continue;
		const product = itemCatalog.find((item) => item.id === productId);
		if (!product) continue;
		byShelf.set(shelfId, {
			category: product.category,
			price: state.shelfPrices[slot.id] ?? product.sellingPrice,
			productId,
			productName: product.name,
			shelfId,
			shelfName: getFixtureName(shelfId, state.era?.id),
			stock: state.shelfStock[slot.id] ?? 0,
		});
	}
	return Array.from(byShelf.values());
}
