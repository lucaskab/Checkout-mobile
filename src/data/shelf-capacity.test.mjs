import { expect, test } from "bun:test";
import {
	getNextShelfSlotUpgrade,
	getNextShelfUnlockUpgrade,
} from "./shelf-capacity.ts";
import { maximumShelfCount } from "./shelf-slots.ts";

test("places for products are not sold apart any more: they come with the evolution", () => {
	expect(getNextShelfSlotUpgrade(4)).toBeNull();
	expect(getNextShelfSlotUpgrade(7)).toBeNull();
});

test("unlocks shelves one per expansion, independently from their slot expansions", () => {
	// The produce crates and the styrofoam cooler come with the sidewalk table; the bread basket comes with
	// the tent and the dairy display with the fair stall.
	expect(getNextShelfUnlockUpgrade(2)).toMatchObject({
		coinCost: 300,
		eraId: "tenda",
		shelfId: "bakery",
		unlockedShelves: 3,
	});
	expect(getNextShelfUnlockUpgrade(3)).toMatchObject({ eraId: "banca", shelfId: "dairy" });
	expect(getNextShelfUnlockUpgrade(8)).toMatchObject({ eraId: "supermercado", shelfId: "icecream" });
	expect(getNextShelfUnlockUpgrade(maximumShelfCount)).toBeNull();
});
