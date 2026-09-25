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

test("unlocks shelves independently from their slot expansions", () => {
	expect(getNextShelfUnlockUpgrade(1)).toMatchObject({
		coinCost: 600,
		playerLevel: 3,
		unlockedShelves: 2,
	});
	expect(getNextShelfUnlockUpgrade(maximumShelfCount)).toBeNull();
});
