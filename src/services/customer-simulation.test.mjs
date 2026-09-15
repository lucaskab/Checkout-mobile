import { expect, test } from "bun:test";
import { simulateMarketVisit } from "./customer-simulation.ts";

test("stocked shelves receive varied visits while empty shelves are never purchased", () => {
	const products = Array.from({ length: 7 }, (_, i) => ({
		shelfId: `shelf-${i}`,
		productId: i + 1,
		availableQuantity: i === 6 ? 0 : 30,
		category: "hortifruti",
		name: `Product ${i}`,
		marketPrice: 5,
		sellingPrice: 3,
		necessity: 1,
		popularity: 1,
		promotionRate: 0,
		visualAttractiveness: 1,
	}));
	const visited = new Set();
	for (let seed = 1; seed <= 200; seed++) {
		const options = { products, seed, storeReputation: 100 };
		const visit = simulateMarketVisit(options);
		expect(visit).toEqual(simulateMarketVisit(options));
		for (const purchase of visit.purchases) {
			expect(purchase.shelfId).not.toBe("shelf-6");
			visited.add(purchase.shelfId);
		}
	}
	expect(visited.size).toBe(6);
	expect(products[0].shelfId).toBe("shelf-0");
});
