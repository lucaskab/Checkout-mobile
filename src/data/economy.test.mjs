import { expect, test } from "bun:test";
import {
	getBuildDurationForCost,
	getContractCoins,
	getItemIncomeMultiplier,
	getItemUpgradeCost,
	MAX_BUILD_MS,
	MIN_BUILD_MS,
	marketEras,
	roundPrice,
	TURN_DURATION_MS,
} from "./economy";
import { DAY_DURATION_MS } from "../services/market-day";

test("a market turn lasts 10 minutes", () => {
	expect(TURN_DURATION_MS).toBe(10 * 60_000);
	expect(DAY_DURATION_MS).toBe(TURN_DURATION_MS);
});

test("eras go from the sidewalk table to the chain, each one pricier, bigger and later", () => {
	expect(marketEras.map((era) => era.id)).toEqual([
		"mesinha",
		"tenda",
		"banca",
		"conteiner",
		"spati",
		"quitanda",
		"minimercado",
		"mercadinho",
		"supermercado",
		"hipermercado",
		"rede",
	]);
	for (let index = 1; index < marketEras.length; index++) {
		const era = marketEras[index];
		const previous = marketEras[index - 1];
		expect(era.index).toBe(index);
		expect(era.coinCost).toBeGreaterThan(previous.coinCost);
		expect(era.targetDay).toBeGreaterThanOrEqual(previous.targetDay);
		expect(era.productSlots).toBeGreaterThanOrEqual(previous.productSlots);
		expect(era.ticketMultiplier).toBeGreaterThanOrEqual(previous.ticketMultiplier);
		expect(era.buildDurationMs).toBeGreaterThanOrEqual(MIN_BUILD_MS);
		expect(era.buildDurationMs).toBeLessThanOrEqual(MAX_BUILD_MS);
	}
	expect(marketEras.find((era) => era.id === "spati")?.nightTurn).toBe(true);
	expect(marketEras.find((era) => era.id === "tenda")?.nightTurn).toBe(false);
});

test("each item level costs 15% more and earns 10% more", () => {
	expect(getItemUpgradeCost(1_000, 0)).toBe(1_000);
	expect(getItemUpgradeCost(1_000, 1)).toBe(1_200); // 1.150 rounded to 2 digits
	expect(getItemUpgradeCost(1_000, 5)).toBe(2_000); // 2.011
	expect(getItemIncomeMultiplier(0)).toBe(1);
	expect(getItemIncomeMultiplier(2)).toBeCloseTo(1.21);
});

test("builds last from 3 minutes to 36 hours depending on the price", () => {
	expect(getBuildDurationForCost(100)).toBe(MIN_BUILD_MS);
	expect(getBuildDurationForCost(2_000_000)).toBe(MAX_BUILD_MS);
	expect(getBuildDurationForCost(60_000)).toBeGreaterThan(getBuildDurationForCost(5_000));
});

test("prices are friendly and contracts grow with the level", () => {
	expect(roundPrice(48_765)).toBe(49_000);
	expect(roundPrice(1_234)).toBe(1_200);
	expect(getContractCoins(10)).toBeGreaterThan(getContractCoins(1));
});
