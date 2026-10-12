import { readFileSync } from "node:fs";
import { describe, expect, test } from "bun:test";
import { getSkipDiamondCost, SKIP_PRICE_POINTS } from "./diamond-skip";

const MIN = 60_000;
const HOUR = 60 * MIN;
const DAY = 24 * HOUR;

describe("the speed-up price (diamonds to finish a timer now)", () => {
	test("costs nothing when nothing is left, 1 for the last minute", () => {
		expect(getSkipDiamondCost(0)).toBe(0);
		expect(getSkipDiamondCost(-1)).toBe(0);
		expect(getSkipDiamondCost(Number.NaN)).toBe(0);
		expect(getSkipDiamondCost(1)).toBe(1);
		expect(getSkipDiamondCost(MIN)).toBe(1);
	});

	test("follows its reference points: 1 h → 10, 1 day → 150, 1 week → 700", () => {
		expect(getSkipDiamondCost(HOUR)).toBe(10);
		expect(getSkipDiamondCost(DAY)).toBe(150);
		expect(getSkipDiamondCost(7 * DAY)).toBe(700);
		// Beyond a week it keeps the last slope.
		expect(getSkipDiamondCost(14 * DAY)).toBe(1_342);
	});

	test("falls as time passes: a 2-hour wait with 1 hour left costs the 1-hour price (Lucas 12/10)", () => {
		expect(getSkipDiamondCost(2 * HOUR)).toBe(17);
		expect(getSkipDiamondCost(2 * HOUR - HOUR)).toBe(getSkipDiamondCost(HOUR));
		let last = Number.POSITIVE_INFINITY;
		for (let left = 40 * HOUR; left > 0; left -= 37_000) {
			const cost = getSkipDiamondCost(left);
			expect(cost).toBeLessThanOrEqual(last);
			last = cost;
		}
	});

	test("long waits get a bulk discount (cheaper per hour)", () => {
		const perHour = (ms) => getSkipDiamondCost(ms) / (ms / HOUR);
		expect(perHour(DAY)).toBeLessThan(perHour(HOUR));
		expect(perHour(7 * DAY)).toBeLessThan(perHour(DAY));
		// …but skipping is never free: every minute still costs something.
		expect(getSkipDiamondCost(10 * MIN)).toBeGreaterThan(getSkipDiamondCost(MIN));
	});

	test("Unity's world boards use the same points (CheckoutSkipPrice.cs)", () => {
		const cs = readFileSync(
			new URL("../../unity/CheckoutSimulator/Assets/Scripts/Checkout/CheckoutSkipPrice.cs", import.meta.url),
			"utf8",
		);
		const constants = { Minute: MIN, Hour: HOUR, Day: DAY };
		const body = cs.match(/Points=\{(.*?)\};/s)?.[1] ?? "";
		const points = [...body.matchAll(/\{([^{}]+),([^{}]+)\}/g)].map(([, time, diamonds]) => [
			// "7*Day" → 7 × Day
			time
				.trim()
				.split("*")
				.reduce((product, part) => product * (constants[part.trim()] ?? Number(part)), 1),
			Number(diamonds),
		]);
		expect(points).toEqual(SKIP_PRICE_POINTS.map(([time, diamonds]) => [time, diamonds]));
	});
});
