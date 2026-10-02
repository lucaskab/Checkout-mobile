import { itemCatalog } from "@/data/market-products";
import { canShelfHold } from "@/data/shelf-categories";

// What a fixture can sell RIGHT NOW: the products already open that fit it. On the sidewalk the
// styrofoam cooler shows "água mineral e refrigerante", not every drink the fridge will hold one day.

const lower = (name: string) => name.charAt(0).toLocaleLowerCase("pt-BR") + name.slice(1);

/** Products already open that a fixture (shelf or sector counter) can hold, in catalog order. */
export function getFixtureProducts(physicalShelfId: string, unlockedProductIds: readonly number[]) {
	return itemCatalog.filter(
		(product) =>
			unlockedProductIds.includes(product.id) && canShelfHold(physicalShelfId, product.category).ok,
	);
}

/** "água mineral e refrigerante" (or "" when nothing open fits yet). */
export function describeFixtureProducts(physicalShelfId: string, unlockedProductIds: readonly number[]) {
	const names = getFixtureProducts(physicalShelfId, unlockedProductIds).map((product) => lower(product.name));
	if (names.length <= 1) return names[0] ?? "";
	return `${names.slice(0, -1).join(", ")} e ${names[names.length - 1]}`;
}
