import type { GameShelfAssignments } from "@/@types/game";
import type { StoreShelf } from "@/@types/store";
import { itemCatalog } from "@/data/market-products";

export function getCurrentShelf(
	shelf: StoreShelf,
	getShelfAssignments: () => GameShelfAssignments,
): StoreShelf {
	const shelfAssignments = getShelfAssignments();
	const product = itemCatalog.find(
		(item) => item.id === shelfAssignments[shelf.id],
	);

	return {
		...shelf,
		name: product?.name ?? shelf.name,
		productId: product?.id,
	};
}
