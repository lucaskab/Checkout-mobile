import { expect, test } from "bun:test";
import { ERA_LOTS, LOT_GRID, MARKET_LOTS, PLAZA_LOTS } from "./market-lots";
import { marketEras } from "./economy";

test("the lots cover the block without overlapping", () => {
	let area = 0;
	for (const lot of MARKET_LOTS) {
		expect(lot.x1).toBeGreaterThan(lot.x0);
		expect(lot.z1).toBeGreaterThan(lot.z0);
		expect(lot.x0).toBeGreaterThanOrEqual(LOT_GRID.x0);
		expect(lot.x1).toBeLessThanOrEqual(LOT_GRID.x0 + LOT_GRID.width + 1e-9);
		area += (lot.x1 - lot.x0) * (lot.z1 - lot.z0);
		for (const other of MARKET_LOTS) {
			if (other === lot) continue;
			const overlap =
				Math.min(lot.x1, other.x1) - Math.max(lot.x0, other.x0) > 1e-6 &&
				Math.min(lot.z1, other.z1) - Math.max(lot.z0, other.z0) > 1e-6;
			expect(overlap).toBe(false);
		}
	}
	expect(area).toBeCloseTo(LOT_GRID.width * LOT_GRID.depth, 3);
});

test("each expansion keeps the lots of the one before", () => {
	const ids = new Set(MARKET_LOTS.map((lot) => lot.id));
	for (let index = 1; index < marketEras.length; index++) {
		const lots = ERA_LOTS[marketEras[index].id];
		for (const id of ERA_LOTS[marketEras[index - 1].id]) expect(lots).toContain(id);
		for (const id of lots) {
			expect(ids.has(id)).toBe(true);
			expect(PLAZA_LOTS).not.toContain(id);
		}
	}
	// The lots are all the same size and the hipermercado takes the whole block.
	expect(new Set(MARKET_LOTS.map((lot) => Math.round((lot.x1 - lot.x0) * (lot.z1 - lot.z0)))).size).toBe(1);
	expect(ERA_LOTS.hipermercado).toHaveLength(MARKET_LOTS.length);
});
