import { expect, test } from "bun:test";
import {
	canBuyCapacityTier,
	chooseCarrier,
	carrierPlanWeights,
	drawCarrierPlan,
	fixtureTiers,
	getCheckoutTier,
	getCheckoutVisualTier,
	getColdRoomTier,
	getColdRoomUpgradeCap,
	getDecorTier,
	getEraFixtureTierCap,
	getFixtureTierTemplate,
	getShelfFixtureTier,
	getSectorSlotCount,
	getSectorTierDefinition,
	getSectorTierPrice,
	getTierSlotLimit,
	isChilledCategory,
	normalizeSectorTiers,
	normalizeDecorTiers,
	withCheckoutRegister,
} from "./fixture-tiers.ts";
import { shelfCapacityUpgrades } from "./shelf-capacity.ts";
import { getInventoryBoxCapacity } from "./inventory-capacity.ts";
import { shopItems } from "./shop-items.ts";
import { getInteriorDecor } from "./interior-decor.ts";

test("tiers are the capacity steps of today: prices, diamonds and levels unchanged", () => {
	expect(shelfCapacityUpgrades.map((u) => [u.capacity, u.coinCost, u.diamondCost, u.playerLevel])).toEqual([
		[5, 0, 0, 1],
		[10, 1_200, 6, 4],
		[15, 6_000, 14, 8],
		[20, 22_000, 28, 14],
		[25, 70_000, 48, 22],
	]);
	// every kind has its four models (+ the premium finish for the product fixtures), footprints on the 0.25 m grid
	for (const [kind, list] of Object.entries(fixtureTiers)) {
		expect(list.length).toBeGreaterThanOrEqual(2);
		list.forEach((tier, index) => {
			expect(tier.tier).toBe(index + 1);
			expect(tier.name.length).toBeGreaterThan(3);
			expect(tier.width).toBeGreaterThan(0);
		});
		expect(getFixtureTierTemplate(kind, 5)).toBe(`${kind}_T4`);
	}
	expect(fixtureTiers.shelf.map((t) => [t.width, t.depth])).toEqual([[1, 0.5], [1.5, 0.5], [2, 0.75], [2.5, 1], [2.5, 1]]);
});

test("each shop caps the furniture size: Conveniência/Quitanda T2, Minimercado T3, Mercadinho T4, Supermercado ★", () => {
	expect(getEraFixtureTierCap("mesinha")).toBe(2);
	expect(getEraFixtureTierCap("spati")).toBe(2);
	expect(getEraFixtureTierCap("quitanda")).toBe(2);
	expect(getEraFixtureTierCap("minimercado")).toBe(3);
	expect(getEraFixtureTierCap("mercadinho")).toBe(4);
	expect(getEraFixtureTierCap("supermercado")).toBe(5);
	expect(getEraFixtureTierCap("rede")).toBe(5);
	// what was bought stays bought: a level-4 shelf shows T2 in the Quitanda and the ★ in the supermarket
	expect(getShelfFixtureTier(4, "quitanda")).toBe(2);
	expect(getShelfFixtureTier(4, "supermercado")).toBe(5);
	expect(getShelfFixtureTier(0, "supermercado")).toBe(1);
	// the next step must fit the shop
	expect(canBuyCapacityTier(0, "spati")).toBe(true); // T1 → T2
	expect(canBuyCapacityTier(1, "spati")).toBe(false); // T2 → T3 needs the minimercado
	expect(canBuyCapacityTier(1, "minimercado")).toBe(true);
	expect(canBuyCapacityTier(2, "minimercado")).toBe(false);
	expect(canBuyCapacityTier(3, "supermercado")).toBe(true);
	// product places by size
	expect([1, 2, 3, 4, 5].map(getTierSlotLimit)).toEqual([5, 6, 7, 7, 7]);
});

test("checkout steps: register, conveyor (+ scanner), premium; the minimercado on starts at the register", () => {
	const ids = ["checkout-register", "smart-conveyor", "auto-scanner", "checkout-premium"];
	for (const id of ids) expect(shopItems.find((i) => i.id === id)).toBeTruthy();
	const register = shopItems.find((i) => i.id === "checkout-register");
	expect([register.coinPrice, register.diamondPrice, register.level]).toEqual([3_000, 10, 8]);
	const premium = shopItems.find((i) => i.id === "checkout-premium");
	expect([premium.coinPrice, premium.diamondPrice, premium.level]).toEqual([90_000, 90, 30]);
	expect(getCheckoutTier([], "spati")).toBe(1);
	expect(getCheckoutTier([], "minimercado")).toBe(2);
	expect(getCheckoutTier(["smart-conveyor"], "spati")).toBe(3);
	expect(getCheckoutTier(["checkout-premium"], "mercadinho")).toBe(4);
	// the look follows the shop: a premium checkout in the minimercado shows the conveyor model
	expect(getCheckoutVisualTier(["checkout-premium"], "minimercado")).toBe(3);
	expect(getCheckoutVisualTier(["checkout-premium"], "supermercado")).toBe(4);
	// the register is given (idempotently) from the minimercado on and to owners of the old conveyor/scanner
	expect(withCheckoutRegister([], "quitanda")).toEqual([]);
	expect(withCheckoutRegister([], "minimercado")).toEqual(["checkout-register"]);
	expect(withCheckoutRegister(["auto-scanner"], "spati")).toEqual(["auto-scanner", "checkout-register"]);
	expect(withCheckoutRegister(["checkout-register"], "rede")).toEqual(["checkout-register"]);
});

test("cold room: T1 free, the tier caps the box upgrade of chilled products only, the old item is the T4", () => {
	expect(getColdRoomTier([])).toBe(1);
	expect(getColdRoomTier(["cold-room-2"])).toBe(2);
	expect(getColdRoomTier(["cold-room-2", "cold-room-3"])).toBe(3);
	expect(getColdRoomTier(["cold-storage"])).toBe(4);
	// boxes per chilled product: 3 / 5 / 8 / 12
	expect([1, 2, 3, 4].map((t) => getInventoryBoxCapacity(getColdRoomUpgradeCap(t)))).toEqual([3, 5, 8, 12]);
	for (const c of ["laticinios", "queijos", "frios", "carnes", "peixes", "congelados", "sorvetes"]) expect(isChilledCategory(c)).toBe(true);
	for (const c of ["bebidas", "mercearia", "hortifruti", "padaria"]) expect(isChilledCategory(c)).toBe(false);
	const t4 = shopItems.find((i) => i.id === "cold-storage");
	expect([t4.coinPrice, t4.diamondPrice, t4.requiresExpansionId]).toEqual([300_000, 150, "grand-warehouse"]);
	expect(shopItems.find((i) => i.id === "cold-room-2")).toMatchObject({ coinPrice: 8_000, diamondPrice: 20 });
	expect(shopItems.find((i) => i.id === "cold-room-3")).toMatchObject({ coinPrice: 45_000, diamondPrice: 60 });
});

test("carts: the smallest carrier that holds the plan, else the biggest there is and only what fits", () => {
	const all = ["basket", "cart", "bigCart"];
	expect(chooseCarrier(0, all)).toEqual({ carrier: "hands", extra: 0, missing: 0 });
	expect(chooseCarrier(1, all)).toEqual({ carrier: "basket", extra: 1, missing: 0 });
	expect(chooseCarrier(2, all)).toEqual({ carrier: "cart", extra: 2, missing: 0 });
	expect(chooseCarrier(3, all)).toEqual({ carrier: "bigCart", extra: 3, missing: 0 });
	expect(chooseCarrier(4, all)).toEqual({ carrier: "bigCart", extra: 4, missing: 0 });
	// only baskets: the family takes a basket and leaves three products behind
	expect(chooseCarrier(4, ["basket"])).toEqual({ carrier: "basket", extra: 1, missing: 3 });
	// a small plan with only the big cart bay: the big cart (smallest that covers it)
	expect(chooseCarrier(1, ["bigCart"])).toEqual({ carrier: "bigCart", extra: 1, missing: 0 });
	expect(chooseCarrier(2, [])).toEqual({ carrier: "hands", extra: 0, missing: 2 });
	// plans: weights add up to 1, families plan more than thrifty customers
	for (const weights of Object.values(carrierPlanWeights)) expect(weights.reduce((a, b) => a + b, 0)).toBeCloseTo(1);
	const mean = (archetype) => Array.from({ length: 1000 }, (_, i) => drawCarrierPlan(archetype, (i + 0.5) / 1000)).reduce((a, b) => a + b, 0) / 1000;
	expect(mean("familia")).toBeGreaterThan(mean("economico") + 1);
	expect(drawCarrierPlan("normal", 0.999)).toBe(4);
	// the ceiling stays base +4, like the old +1 +1 +2
	expect(Math.max(...Object.values({ basket: 1, cart: 2, bigCart: 4 }))).toBe(4);
});

test("stations: three decorations with their levels and prices; the cart bays need the mercadinho", () => {
	expect(getInteriorDecor("basket-station")).toMatchObject({ coinPrice: 800, requiredLevel: 2, effect: { carrier: "basket" } });
	expect(getInteriorDecor("cart-corral")).toMatchObject({ coinPrice: 4_000, requiredLevel: 7, effect: { carrier: "cart" }, placeEra: "mercadinho" });
	expect(getInteriorDecor("big-cart-corral")).toMatchObject({ coinPrice: 22_000, requiredLevel: 17, effect: { carrier: "bigCart" }, placeEra: "mercadinho" });
	expect(shopItems.some((i) => i.id === "shopping-basket" || i.id === "large-cart")).toBe(false);
	expect(shopItems.find((i) => i.id === "turbo-cart")?.effect?.basketItems).toBe(2);
});

test("evolving decorations: tiers are clamped and unknown ids dropped", () => {
	expect(getDecorTier(undefined, "atm")).toBe(1);
	expect(getDecorTier({ atm: 9 }, "atm")).toBe(3);
	expect(getDecorTier({ gumball: 3 }, "gumball")).toBe(2);
	expect(normalizeDecorTiers({ atm: 2, gumball: 1, nope: 3, "claw-machine": "x" })).toEqual({ atm: 2 });
});

test("sector steps: prices by shop size, slots, time and price", () => {
	expect(getSectorTierPrice(2, "mercadinho")).toEqual({ coins: 18_000, diamonds: 30 });
	expect(getSectorTierPrice(3, "mercadinho")).toEqual({ coins: 55_000, diamonds: 80 });
	expect(getSectorTierPrice(2, "supermercado").coins).toBe(30_000);
	expect(getSectorTierPrice(3, "supermercado").coins).toBe(90_000);
	expect(getSectorTierPrice(2, "hipermercado").coins).toBe(70_000);
	expect(getSectorTierPrice(3, "rede").coins).toBe(200_000);
	expect(getSectorTierPrice(1, "rede")).toBeNull();
	expect(getSectorTierPrice(4, "rede")).toBeNull();
	expect(getSectorSlotCount(2, {}, "padaria")).toBe(2);
	expect(getSectorSlotCount(2, { padaria: 2 }, "padaria")).toBe(3);
	expect(getSectorSlotCount(3, { padaria: 3 }, "padaria")).toBe(4);
	expect(getSectorTierDefinition(3)).toMatchObject({ width: 4, depth: 3.25, durationMultiplier: 0.8, priceMultiplier: 1.1 });
	expect(getSectorTierDefinition(1)).toMatchObject({ width: 2.5, depth: 2, durationMultiplier: 1, priceMultiplier: 1 });
	expect(normalizeSectorTiers({ padaria: 9, adega: 1, x: 2 }, ["padaria", "adega"])).toEqual({ padaria: 3 });
});
