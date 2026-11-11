import { describe, expect, test } from "bun:test";
import {
	getEarnedTrucks,
	getMaxBoxesPerOrder,
	getNextTruckDiamondPrice,
	getNextTruckUnlock,
	getSupplierTrucks,
	initialSupplierOrderSlots,
	MAX_SUPPLIER_TRUCKS,
	migrateOwnedTrucks,
	normalizeSupplierOrderSlots,
} from "./supplier-capacity";

const player = (level, era, owned = 1) => ({ logistics: { supplierOrderSlots: owned }, market: { level }, era: { id: era } });

// Lucas 11/11: one truck at the start; more with the level, the expansions and diamonds.
describe("supplier trucks", () => {
	test("a new player has one truck that holds 10 boxes", () => {
		expect(initialSupplierOrderSlots).toBe(1);
		expect(getSupplierTrucks(player(1, "mesinha"))).toBe(1);
		expect(getMaxBoxesPerOrder(1)).toBe(10);
		expect(getMaxBoxesPerOrder(5)).toBe(14);
	});

	test("the level and the expansions give free trucks", () => {
		expect(getEarnedTrucks(3, "tenda")).toBe(0);
		expect(getEarnedTrucks(4, "tenda")).toBe(1);
		expect(getEarnedTrucks(4, "banca")).toBe(2);
		expect(getEarnedTrucks(9, "quitanda")).toBe(4);
		expect(getEarnedTrucks(99, "rede")).toBe(8);
		expect(getNextTruckUnlock(player(1, "mesinha"))).toEqual({ kind: "level", level: 4 });
		expect(getNextTruckUnlock(player(4, "mesinha"))).toEqual({ kind: "era", eraId: "banca" });
	});

	test("diamonds buy a few more, up to the maximum", () => {
		expect(getNextTruckDiamondPrice(player(1, "mesinha"))).toBe(15);
		expect(getNextTruckDiamondPrice(player(1, "mesinha", 2))).toBe(30);
		expect(getNextTruckDiamondPrice(player(1, "mesinha", 4))).toBeNull();
		expect(getSupplierTrucks(player(99, "rede", 4))).toBe(MAX_SUPPLIER_TRUCKS);
		expect(getNextTruckDiamondPrice(player(99, "rede", 2))).toBeNull();
	});

	test("old saves keep every truck they had", () => {
		// Level 1 at the tent with the 3 trucks of before: 2 become owned on top of the first.
		const owned = migrateOwnedTrucks(3, 1, "tenda");
		expect(getSupplierTrucks(player(1, "tenda", owned))).toBe(3);
		// Level 10 at the quitanda with 6: the level and the era give 4 now, so 2 stay owned (6 in all).
		const later = migrateOwnedTrucks(6, 10, "quitanda");
		expect(getSupplierTrucks(player(10, "quitanda", later))).toBe(6);
		// A save with more free trucks than it had keeps at least the first one.
		expect(migrateOwnedTrucks(3, 30, "rede")).toBe(1);
	});

	test("normalizes saved values", () => {
		expect(normalizeSupplierOrderSlots(undefined)).toBe(1);
		expect(normalizeSupplierOrderSlots(0)).toBe(1);
		expect(normalizeSupplierOrderSlots(4.8)).toBe(4);
		expect(normalizeSupplierOrderSlots(99)).toBe(MAX_SUPPLIER_TRUCKS);
	});
});
