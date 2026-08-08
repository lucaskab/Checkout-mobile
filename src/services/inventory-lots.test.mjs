import { expect, test } from "bun:test";
import {
	appendInventoryLots,
	discardExpiredInventoryLots,
	reconcileInventoryLots,
	takeInventoryLots,
} from "./inventory-lots";

test("takes inventory in expiry order", () => {
	const result = takeInventoryLots([
		{ expiresAt: 400, quantity: 3 },
		{ expiresAt: 800, quantity: 5 },
	], 4);

	expect(result.takenLots).toEqual([
		{ expiresAt: 400, quantity: 3 },
		{ expiresAt: 800, quantity: 1 },
	]);
	expect(result.remainingLots).toEqual([{ expiresAt: 800, quantity: 4 }]);
});

test("reconciles legacy stock and removes expired lots", () => {
	const lots = reconcileInventoryLots(1, 6, [{ expiresAt: 10, quantity: 2 }], 0);
	const result = discardExpiredInventoryLots(
		appendInventoryLots(lots, [{ expiresAt: 0, quantity: 1 }]),
		1,
	);

	expect(result.expiredQuantity).toBe(1);
	expect(result.remainingLots).toHaveLength(2);
});
