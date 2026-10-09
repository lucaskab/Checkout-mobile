import { expect, test } from "bun:test";
import { shopItems } from "../data/shop-items";
import { getShopEffects } from "./shop-effects";

test("connects permanent shop items to the simulation effects", () => {
	const effects = getShopEffects(["erp-system", "pallet", "delivery-drone", "premium-floor", "extra-checkout", "smart-conveyor"]);

	expect(effects.supplierCostMultiplier).toBeCloseTo(0.85);
	expect(effects.supplierDurationMultiplier).toBeCloseTo(0.65);
	expect(effects.storeReputationBonus).toBe(3);
	expect(effects.offlineRevenueMultiplier).toBeCloseTo(1.25);
	expect(effects.cashierSpeedMultiplier).toBeCloseTo(2.5);
});

test("marketing brings more customers and makes room for them", () => {
	const effects = getShopEffects(["street-banner", "billboard"]);
	expect(effects.customerArrivalMultiplier).toBeCloseTo(1.13);
	expect(effects.customerCapacityMultiplier).toBeCloseTo(1.13);
});

test("the fridge only lifts its own categories", () => {
	const effects = getShopEffects(["refrigerated-fridge"]);
	expect(effects.revenueMultiplier).toBe(1);
	expect(effects.categoryRevenueBonuses.bebidas).toBeCloseTo(0.15);
	expect(effects.categoryRevenueBonuses.hortifruti).toBeUndefined();
});

test("boosters only count while they run, owned or not", () => {
	const now = 1_000_000;
	const shop = { ownedItemIds: ["happy-hour"], activeBoosts: { "flash-sale": now + 60_000 } };
	expect(getShopEffects(shop, now).maxProductsBonus).toBe(2);
	expect(getShopEffects(shop, now).customerArrivalMultiplier).toBe(1);
	expect(getShopEffects(shop, now + 61_000).maxProductsBonus).toBe(0);
});

test("every upgrade has an effect, a price and a description", () => {
	for (const item of shopItems) {
		const builtOnly = item.id === "extra-checkout" || item.id === "self-checkout";
		expect({ id: item.id, effect: Boolean(item.effect) || builtOnly }).toEqual({ id: item.id, effect: true });
		expect({ id: item.id, price: (item.coinPrice ?? item.diamondPrice ?? 0) > 0 }).toEqual({ id: item.id, price: true });
		if (item.isConsumable) expect({ id: item.id, duration: (item.durationMs ?? 0) > 0 }).toEqual({ id: item.id, duration: true });
	}
	expect(new Set(shopItems.map((item) => item.id)).size).toBe(shopItems.length);
});

test("upgrades reach the visit and the checkout line", async () => {
	const { simulateMarketVisit } = await import("./customer-simulation");
	const { createPendingCheckout } = await import("./checkout-counter");
	const product = { availableQuantity: 99, category: "bebidas", marketPrice: 10, name: "Suco", necessity: 100, productId: 1, promotionRate: 0, sellingPrice: 10, shelfId: "a" };
	const base = { products: [product], seed: 42, storeReputation: 80 };
	const plain = simulateMarketVisit(base);
	const cold = simulateMarketVisit({ ...base, categoryRevenueBonuses: { bebidas: 0.15 } });
	expect(cold.totalUnits).toBe(plain.totalUnits);
	expect(cold.revenue).toBeGreaterThan(plain.revenue);
	const input = { archetype: "normal", categories: {}, customerId: "c", customerName: "Ana", experience: 1, items: [{ name: "Suco", productId: 1, quantity: 1, unitPrice: 10 }], mood: "calmo", profit: 5, satisfaction: 80, seed: 1 };
	const normal = createPendingCheckout(input, 0);
	const patient = createPendingCheckout({ ...input, patienceMultiplier: 1.25 }, 0);
	expect(patient.expiresAt - patient.readyAt).toBe(Math.round((normal.expiresAt - normal.readyAt) * 1.25));
});
