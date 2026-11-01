import { itemCatalog } from "@/data/market-products";
import { canShelfHold } from "@/data/shelf-categories";
import { getSectorCounterFor } from "@/data/shelf-types";

// What a fixture can sell RIGHT NOW: the products already open that fit it. On the sidewalk the
// styrofoam cooler shows "água mineral e refrigerante", not every drink the fridge will hold one day.

const lower = (name: string) => name.charAt(0).toLocaleLowerCase("pt-BR") + name.slice(1);

/** Products already open that a fixture (shelf or sector counter) can hold, in catalog order. */
export function getFixtureProducts(physicalShelfId: string, unlockedProductIds: readonly number[]) {
	return itemCatalog.filter(
		(product) => unlockedProductIds.includes(product.id) && canFixtureSell(physicalShelfId, product).ok,
	);
}

/** Exclusive products (the reward of an evolution) only go on their own fixture or their sector's counter. */
export function isExclusiveAllowed(physicalShelfId: string, product: { exclusive?: { fixture: string } }) {
	if (!product.exclusive) return true;
	const fixture = product.exclusive.fixture;
	return physicalShelfId === fixture || getSectorCounterFor(fixture)?.id === physicalShelfId;
}

/** Can this fixture sell this product: its kind of product, and exclusives only on their own fixture. */
export function canFixtureSell(
	physicalShelfId: string,
	product: { category: string; exclusive?: { fixture: string } },
): { ok: boolean; reason: string } {
	if (!isExclusiveAllowed(physicalShelfId, product))
		return { ok: false, reason: "Este produto é exclusivo de outro móvel." };
	return canShelfHold(physicalShelfId, product.category);
}

/** "água mineral e refrigerante" (or "" when nothing open fits yet). */
export function describeFixtureProducts(physicalShelfId: string, unlockedProductIds: readonly number[]) {
	const names = getFixtureProducts(physicalShelfId, unlockedProductIds).map((product) => lower(product.name));
	if (names.length <= 1) return names[0] ?? "";
	return `${names.slice(0, -1).join(", ")} e ${names[names.length - 1]}`;
}
