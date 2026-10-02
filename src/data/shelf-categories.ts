// Which products each fixture can hold (src/data/shelf-types.ts): the produce stand only fruit and
// vegetables, the upright cooler only drinks, the chest freezer only ice cream, the frozen-food freezer only
// frozen food, each sector counter only its own kind of goods. Only new placements are checked: products
// already on a shelf in old saves stay where they are until the player moves them.

import {
	getFixtureName,
	getSectorCounter,
	getShelfCategories,
	getShelfType,
} from "@/data/shelf-types";

/** Products that are sold cold (fridges and chilled counters). */
export const CHILLED_CATEGORIES = [
	"bebidas",
	"refrigerantes",
	"aguas",
	"energeticos",
	"alcoolicos",
	"laticinios",
	"frios",
	"queijos",
] as const;

/** Products that must stay frozen. */
export const FROZEN_CATEGORIES = ["congelados", "sorvetes"] as const;

export type ShelfKind = "fridge" | "freezer" | "shelf" | "counter";

const kinds: Record<string, ShelfKind> = {
	dairy: "fridge",
	drinks: "fridge",
	pizza: "freezer",
	icecream: "freezer",
};

export function getShelfKind(physicalShelfId: string): ShelfKind {
	if (getSectorCounter(physicalShelfId)) return "counter";
	return kinds[physicalShelfId] ?? "shelf";
}

export const shelfKindNames: Record<ShelfKind, string> = {
	fridge: "Geladeira",
	freezer: "Freezer",
	shelf: "Prateleira",
	counter: "Balcão",
};

/** Can a product of `category` go on the fixture `physicalShelfId`? With the reason when it cannot. */
export function canShelfHold(physicalShelfId: string, category: string): { ok: boolean; reason: string } {
	const categories = getShelfCategories(physicalShelfId);
	if (categories.includes(category)) return { ok: true, reason: "" };
	const holds = getShelfType(physicalShelfId)?.holds ?? getSectorCounter(physicalShelfId)?.holds;
	return {
		ok: false,
		reason: holds
			? `${getFixtureName(physicalShelfId)}: só ${holds}.`
			: "Este lugar não aceita este produto.",
	};
}
