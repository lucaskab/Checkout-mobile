import type { MarketSimulationProduct } from "@/@types/customer-simulation";
import { TURN_DURATION_MS } from "@/data/economy";
import { simulateMarketVisit } from "@/services/customer-simulation";

// What one day (turn) of the market should bring, from the same rules that run the day: the arrival rhythm
// of customers (getCustomerArrivalDelay) and what each one buys from the shelves as they are now
// (simulateMarketVisit). The day's contracts are sized on it (src/data/day-contracts.ts): the easy one is
// usually done before half of the day, the medium one a little after half, the hard one only on a good day.

export type DayForecast = {
	/** Customers who walk in during a whole day. */
	customers: number;
	/** Customers who leave with something. */
	buyers: number;
	/** Coins paid at the register. */
	revenue: number;
	/** Revenue minus what the goods cost. */
	profit: number;
	units: number;
	unitsByCategory: Record<string, number>;
};

export type DayForecastInput = {
	level: number;
	unlockedProductCount: number;
	/** All arrival multipliers of the store (era, shop items, staff, loyalty), events left out. */
	arrivalMultiplier: number;
	/** Shortest wait between two customers (the size of the market). */
	minArrivalDelayMs: number;
	/** Products on sale with their price and stock, as customers see them. */
	products: MarketSimulationProduct[];
	/** Purchase price of each product, for the profit. */
	purchasePrice: (productId: number) => number;
	budgetMultiplier: number;
	maxProductsBonus: number;
	revenueMultiplier: number;
	/** Extra revenue share by product category (shop upgrades). */
	categoryRevenueBonuses?: Record<string, number>;
	storeReputation: number;
};

/** Customers simulated to know the average basket. */
const SAMPLE_VISITS = 80;

/**
 * Average wait between two customers. getCustomerArrivalDelay draws the base delay × a variation between
 * 0.75 and 1.25 and keeps it between the market's minimum and max(60 s, minimum); the mean is integrated
 * over that variation.
 */
export function getAverageArrivalDelay(
	level: number,
	unlockedProductCount: number,
	arrivalMultiplier: number,
	minimumDelayMs: number,
) {
	const levelBonus = Math.max(level - 1, 0) * 0.08;
	const varietyBonus = Math.min(Math.max(unlockedProductCount - 1, 0), 40) * 0.025;
	const average = 32_000 / ((1 + levelBonus + varietyBonus) * Math.max(0.01, arrivalMultiplier));
	const high = Math.max(60_000, minimumDelayMs);
	const steps = 50;
	let total = 0;
	for (let i = 0; i <= steps; i++) {
		const variation = 0.75 + (0.5 * i) / steps;
		total += Math.min(high, Math.max(minimumDelayMs, average * variation));
	}
	return total / (steps + 1);
}

export function forecastDay(input: DayForecastInput, dayMs = TURN_DURATION_MS): DayForecast {
	const delay = getAverageArrivalDelay(
		input.level,
		input.unlockedProductCount,
		input.arrivalMultiplier,
		input.minArrivalDelayMs,
	);
	const customers = dayMs / delay;
	let buyers = 0;
	let revenue = 0;
	let profit = 0;
	let units = 0;
	const byCategory: Record<string, number> = {};
	if (input.products.length > 0) {
		for (let i = 0; i < SAMPLE_VISITS; i++) {
			const visit = simulateMarketVisit({
				budgetMultiplier: input.budgetMultiplier,
				maxProductsBonus: input.maxProductsBonus,
				// Plenty of stock: the forecast is about what customers want, not about restocking.
				products: input.products.map((product) => ({ ...product, availableQuantity: 99 })),
				revenueMultiplier: input.revenueMultiplier,
				categoryRevenueBonuses: input.categoryRevenueBonuses,
				seed: 7_919 * (i + 1),
				storeReputation: input.storeReputation,
			});
			if (visit.purchases.length > 0) buyers += 1;
			for (const purchase of visit.purchases) {
				const product = input.products.find((item) => item.productId === purchase.productId);
				revenue += purchase.revenue;
				profit += purchase.revenue - input.purchasePrice(purchase.productId) * purchase.quantity;
				units += purchase.quantity;
				if (product) byCategory[product.category] = (byCategory[product.category] ?? 0) + purchase.quantity;
			}
		}
	}
	const perVisit = customers / SAMPLE_VISITS;
	const unitsByCategory: Record<string, number> = {};
	for (const [category, value] of Object.entries(byCategory)) unitsByCategory[category] = value * perVisit;
	return {
		customers,
		buyers: buyers * perVisit,
		revenue: revenue * perVisit,
		profit: Math.max(0, profit * perVisit),
		units: units * perVisit,
		unitsByCategory,
	};
}

/**
 * A rough day for a market nobody looked at yet (the very first day, old saves): the sidewalk table with a
 * few cheap products. Used only until the store can forecast from its own shelves.
 */
export function getFallbackDayForecast(level: number, dayMs = TURN_DURATION_MS): DayForecast {
	const delay = getAverageArrivalDelay(level, 5, 0.8, 40_000);
	const customers = dayMs / delay;
	const buyers = customers * 0.85;
	const ticket = 18 * (1 + Math.max(level - 1, 0) * 0.08);
	return {
		customers,
		buyers,
		revenue: buyers * ticket,
		profit: buyers * ticket * 0.35,
		units: buyers * 1.6,
		unitsByCategory: {},
	};
}
