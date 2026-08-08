import { expect, test } from "bun:test";
import { getShopEffects } from "./shop-effects";

test("connects permanent shop items to the simulation effects", () => {
	const effects = getShopEffects([
		"erp-system",
		"delivery-drone",
		"garden",
		"golden-register",
	]);

	expect(effects.supplierCostMultiplier).toBeCloseTo(0.9);
	expect(effects.supplierDurationMultiplier).toBeCloseTo(0.65);
	expect(effects.productionDurationMultiplier).toBeCloseTo(0.9);
	expect(effects.storeReputationBonus).toBe(6);
	expect(effects.offlineRevenueMultiplier).toBeCloseTo(2.5);
});
