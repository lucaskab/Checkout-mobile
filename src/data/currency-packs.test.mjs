import { describe, expect, test } from "bun:test";
import { currencyPacks } from "./currency-packs";

describe("currencyPacks", () => {
	test("contains five packs for every category (plus the 48 h starter pack)", () => {
		for (const category of ["bundle", "coins", "diamonds"]) {
			expect(
				currencyPacks.filter((pack) => pack.category === category && !pack.limitedTime),
			).toHaveLength(5);
		}
		expect(currencyPacks.filter((pack) => pack.limitedTime).map((pack) => pack.id)).toEqual(["bundle-firstdays"]);
	});

	test("uses unique store product identifiers", () => {
		const productIds = currencyPacks.map((pack) => pack.productId);

		expect(new Set(productIds).size).toBe(productIds.length);
	});

	test("only grants the currencies represented by each category", () => {
		for (const pack of currencyPacks) {
			if (pack.category === "bundle") {
				expect(pack.coins).toBeGreaterThan(0);
				expect(pack.diamonds).toBeGreaterThan(0);
				continue;
			}

			expect(pack.category === "coins" ? pack.diamonds : pack.coins).toBe(0);
		}
	});
});
