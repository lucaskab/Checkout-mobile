import { describe, expect, test } from "bun:test";
import {
	getNextSupplierOrderSlotUpgrade,
	initialSupplierOrderSlots,
	normalizeSupplierOrderSlots,
} from "./supplier-capacity";

describe("supplier order capacity", () => {
	test("starts with three simultaneous supplier orders", () => {
		expect(initialSupplierOrderSlots).toBe(3);
		expect(getNextSupplierOrderSlotUpgrade(initialSupplierOrderSlots)).toEqual({
			coinCost: 800,
			diamondCost: 5,
			playerLevel: 3,
			slots: 4,
		});
	});

	test("returns the next expansion and stops at the configured maximum", () => {
		expect(getNextSupplierOrderSlotUpgrade(4)?.slots).toBe(5);
		expect(getNextSupplierOrderSlotUpgrade(8)).toBeNull();
	});

	test("normalizes persisted capacity values", () => {
		expect(normalizeSupplierOrderSlots(undefined)).toBe(3);
		expect(normalizeSupplierOrderSlots(1)).toBe(3);
		expect(normalizeSupplierOrderSlots(4.8)).toBe(4);
		expect(normalizeSupplierOrderSlots(99)).toBe(8);
	});
});
