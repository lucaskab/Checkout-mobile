import { expect, test } from "bun:test";
import {
	getNextShelfSlotUpgrade,
	getNextShelfUnlockUpgrade,
} from "./shelf-capacity.ts";
import { maximumShelfCount } from "./shelf-slots.ts";

test("starts each shelf with four slots and keeps slot expansion local", () => {
	expect(getNextShelfSlotUpgrade(4)).toMatchObject({
		coinCost: 600,
		playerLevel: 3,
		unlockedSlots: 5,
	});
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
