import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";

// Diamonds (Lucas 12/10): every timer can be finished now for diamonds, priced by the time still left; too few
// diamonds leaves a shortfall that opens the diamond store; diamonds come from the store (real money), not from
// playing the day's contracts; a store purchase is credited once, as the catalog prices it for the player now.
globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../stores/game-store.ts");
const { createSimulatorCommandHandler } = await import("./simulator-protocol.ts");
const { getSkipDiamondCost } = await import("../data/diamond-skip.ts");
const { getCaseSize } = await import("../data/case-sizes.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const { currencyPacks, getCurrencyPack, getCurrencyPackCoins } = await import("../data/currency-packs.ts");
const { createDayOffers } = await import("./market-day.ts");

useGameStore.setState({ interior: { items: [], owned: {} } });
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));

const store = () => useGameStore.getState();
const MIN = 60_000;
const HOUR = 60 * MIN;
const gems = (premiumCurrency) =>
	useGameStore.setState({ logistics: { ...store().logistics, premiumCurrency }, diamondShortfall: null });
const diamonds = () => store().logistics.premiumCurrency;

// Each timer of the game, set to run `total` ms with `left` ms still to go, with the action that finishes it now.
const now = () => Date.now();
const timers = {
	"market expansion (era obra)": {
		start: (total, left) =>
			useGameStore.setState({
				era: { ...store().era, construction: { eraId: "tenda", startedAt: now() - (total - left), endsAt: now() + left } },
			}),
		finish: () => store().finishMarketEraNow(),
		running: () => store().era.construction !== null,
	},
	"building wing": {
		start: (total, left) =>
			useGameStore.setState({
				marketExpansionConstruction: { expansionId: "service-wing", startedAt: now() - (total - left), endsAt: now() + left },
			}),
		finish: () => store().finishMarketExpansionNow(),
		running: () => store().marketExpansionConstruction !== null,
	},
	"lot clearing": {
		start: (total, left) =>
			useGameStore.setState({
				lots: { owned: ["A1"], cleared: [], clearing: { lotId: "A1", startedAt: now() - (total - left), endsAt: now() + left } },
			}),
		finish: () => store().finishLotClearingNow(),
		running: () => store().lots.clearing !== null,
	},
	"interior build (shelf, sector, fixture)": {
		start: (total, left) =>
			useGameStore.setState({
				interiorConstructions: [
					{ id: "b1", kind: "shop", targetId: "self-checkout", startedAt: now() - (total - left), endsAt: now() + left, durationMs: total, pending: false },
				],
			}),
		finish: () => store().finishInteriorConstructionNow("b1"),
		running: () => store().interiorConstructions.some((b) => b.id === "b1"),
	},
	"production job": {
		start: (total, left) => {
			const product = itemCatalog[0];
			useGameStore.setState({
				inventory: { ...store().inventory, [product.id]: 0 },
				inventoryCapacityLevels: { ...store().inventoryCapacityLevels, [product.id]: 4 },
				production: {
					...store().production,
					jobs: [
						{ id: "j1", recipeId: "r", sectorId: "padaria", slotIndex: 0, outputProductId: product.id, outputQuantity: 1, startedAt: now() - (total - left), endsAt: now() + left },
					],
				},
			});
		},
		finish: () => store().finishProductionNow("j1"),
		running: () => store().production.jobs.some((j) => j.id === "j1"),
	},
	"supplier truck": {
		start: (total, left) => {
			const product = itemCatalog.find((p) => p.acquisition === "supplier");
			useGameStore.setState({
				inventory: { ...store().inventory, [product.id]: 0 },
				inventoryCapacityLevels: { ...store().inventoryCapacityLevels, [product.id]: 4 },
				logistics: {
					...store().logistics,
					emergencyTokens: 0,
					orders: [
						{ id: "o1", productId: product.id, quantity: getCaseSize(product), status: "em-transporte", totalCost: 1, deliveredAt: null, createdAt: now() - (total - left), deliveryDurationMs: total },
					],
				},
			});
		},
		finish: () => store().deliverOrderInstantly("o1"),
		running: () => store().logistics.orders.find((o) => o.id === "o1")?.status !== "entregue",
	},
};

describe("every timer can be finished now with diamonds", () => {
	for (const [name, timer] of Object.entries(timers)) {
		test(`${name}: costs the speed-up price of the time left, which falls as time passes`, () => {
			// A 2-hour wait, just started.
			gems(500);
			timer.start(2 * HOUR, 2 * HOUR);
			expect(timer.finish()).toBe(true);
			expect(500 - diamonds()).toBe(getSkipDiamondCost(2 * HOUR));
			expect(timer.running()).toBe(false);

			// The same wait with 1 hour left costs the 1-hour price.
			gems(500);
			timer.start(2 * HOUR, HOUR);
			expect(timer.finish()).toBe(true);
			expect(500 - diamonds()).toBe(getSkipDiamondCost(HOUR));
			expect(getSkipDiamondCost(HOUR)).toBeLessThan(getSkipDiamondCost(2 * HOUR));
		});

		test(`${name}: too few diamonds keeps it running and asks for the diamond store`, () => {
			gems(3);
			timer.start(2 * HOUR, 2 * HOUR);
			expect(timer.finish()).toBe(false);
			expect(diamonds()).toBe(3);
			expect(timer.running()).toBe(true);
			const cost = getSkipDiamondCost(2 * HOUR);
			expect(store().diamondShortfall).toEqual(expect.objectContaining({ needed: cost, missing: cost - 3 }));
			store().dismissDiamondShortfall();
			expect(store().diamondShortfall).toBe(null);
		});
	}

	test("a truck still comes for an emergency ticket instead of diamonds", () => {
		gems(0);
		timers["supplier truck"].start(2 * HOUR, 2 * HOUR);
		useGameStore.setState({ logistics: { ...store().logistics, emergencyTokens: 1 } });
		expect(store().deliverOrderInstantly("o1")).toBe(true);
		expect(store().logistics.emergencyTokens).toBe(0);
		expect(store().diamondShortfall ?? null).toBe(null);
	});

	test("'Finalizar' a truck is the same time-based price (no flat 2 diamonds after half the trip)", () => {
		gems(500);
		timers["supplier truck"].start(10 * HOUR, 3 * HOUR);
		expect(store().completeOrderFinalStage("o1")).toBe(true);
		expect(500 - diamonds()).toBe(getSkipDiamondCost(3 * HOUR));
	});

	test("the world's 'Acelerar' boards can finish the era obra and the lot clearing (Unity commands)", () => {
		gems(500);
		timers["lot clearing"].start(HOUR, HOUR);
		const handle = createSimulatorCommandHandler("s", () => store(), () => 1);
		const receipt = handle({ kind: "command", protocol: 1, session: "s", revision: 1, id: "c1", action: "finishLotClearingNow", args: [] });
		expect(receipt.ok).toBe(true);
		expect(store().lots.clearing).toBe(null);
	});

	test("other diamond prices (turbo, decor…) also leave the shortfall when short", () => {
		gems(1);
		expect(store().activateLogisticsBoost()).toBe(false);
		expect(store().diamondShortfall).toEqual(expect.objectContaining({ needed: 3, missing: 2 }));
	});
});

describe("diamonds come from the store, not from the day", () => {
	test("no contract pays diamonds (the hard one pays more coins)", () => {
		for (const level of [1, 5, 20, 60]) {
			const offers = createDayOffers(level, 5, {});
			for (const offer of offers) expect(offer.reward.diamonds).toBe(0);
		}
	});
});

describe("store purchases", () => {
	const pouch = getCurrencyPack("diamonds-pouch");
	const coinsSack = getCurrencyPack("coins-sack");
	const starter = getCurrencyPack("bundle-starter");

	test("a pack is credited once per transaction", () => {
		gems(0);
		const coins = store().coins;
		expect(store().grantCurrencyPack(pouch.productId, "tx-1")).toEqual({ packId: "diamonds-pouch", coins: 0, diamonds: 220 });
		expect(diamonds()).toBe(220);
		expect(store().coins).toBe(coins);
		// The App Store delivering the same order again (app restarted before the confirmation).
		expect(store().grantCurrencyPack(pouch.productId, "tx-1")).toBe(null);
		expect(diamonds()).toBe(220);
	});

	test("refuses unknown packs and empty transactions", () => {
		expect(store().grantCurrencyPack("com.checkout.free.money", "tx-2")).toBe(null);
		expect(store().grantCurrencyPack(pouch.productId, "")).toBe(null);
	});

	test("coin packs follow the player's expansion (same effort skipped early and late)", () => {
		const early = getCurrencyPackCoins(coinsSack, "mesinha");
		const late = getCurrencyPackCoins(coinsSack, "rede");
		expect(late).toBeGreaterThan(early * 100);
		useGameStore.setState({ era: { ...store().era, id: "mercadinho" } });
		const coins = store().coins;
		const grant = store().grantCurrencyPack(coinsSack.id, "tx-3");
		expect(grant.coins).toBe(getCurrencyPackCoins(coinsSack, "mercadinho"));
		expect(store().coins).toBe(coins + grant.coins);
	});

	test("the welcome combo is offered once, but a paid order is always credited", () => {
		expect(store().grantCurrencyPack(starter.productId, "tx-4")).not.toBe(null);
		expect(store().currencyPurchases.purchasedPackIds).toContain("bundle-starter");
		// A second one already paid (e.g. two Ask-to-Buy approvals): the player paid, so it is credited.
		const before = diamonds();
		expect(store().grantCurrencyPack(starter.productId, "tx-5")).not.toBe(null);
		expect(diamonds()).toBe(before + starter.diamonds);
	});

	test("buying clears a pending shortfall (the store does not pop up again)", () => {
		gems(0);
		expect(store().finishMarketExpansionNow()).toBe(false);
		timers["building wing"].start(HOUR, HOUR);
		expect(store().finishMarketExpansionNow()).toBe(false);
		expect(store().diamondShortfall).not.toBe(null);
		store().grantCurrencyPack(pouch.productId, "tx-6");
		expect(store().diamondShortfall).toBe(null);
		expect(store().finishMarketExpansionNow()).toBe(true);
	});

	test("the shortfall is never saved", () => {
		gems(0);
		timers["building wing"].start(HOUR, HOUR);
		store().finishMarketExpansionNow();
		const saved = useGameStore.persist.getOptions().partialize(store());
		expect("diamondShortfall" in saved).toBe(false);
	});
});

describe("pack balance", () => {
	const value = (pack) => {
		// Euros of the pack's price, from its catalog price ("€ 9,99").
		return Number(pack.fallbackPrice.replace(/[^\d,]/g, "").replace(",", "."));
	};
	test("bigger diamond packs give more diamonds per euro", () => {
		const packs = currencyPacks.filter((p) => p.category === "diamonds").sort((a, b) => value(a) - value(b));
		for (let i = 1; i < packs.length; i++)
			expect(packs[i].diamonds / value(packs[i])).toBeGreaterThan(packs[i - 1].diamonds / value(packs[i - 1]));
	});

	test("bigger coin packs give more turns per euro", () => {
		const packs = currencyPacks.filter((p) => p.category === "coins").sort((a, b) => value(a) - value(b));
		for (let i = 1; i < packs.length; i++)
			expect(packs[i].coinTurns / value(packs[i])).toBeGreaterThan(packs[i - 1].coinTurns / value(packs[i - 1]));
	});

	test("combos are worth more than their diamonds and coins bought apart", () => {
		const diamondsPerEuro = (euros) => {
			const packs = currencyPacks.filter((p) => p.category === "diamonds");
			const pack = packs.reduce((best, p) => (Math.abs(value(p) - euros) < Math.abs(value(best) - euros) ? p : best));
			return pack.diamonds / value(pack);
		};
		const turnsPerEuro = (euros) => {
			const packs = currencyPacks.filter((p) => p.category === "coins");
			const pack = packs.reduce((best, p) => (Math.abs(value(p) - euros) < Math.abs(value(best) - euros) ? p : best));
			return pack.coinTurns / value(pack);
		};
		for (const combo of currencyPacks.filter((p) => p.category === "bundle")) {
			const euros = value(combo);
			const apart = combo.diamonds / diamondsPerEuro(euros) + combo.coinTurns / turnsPerEuro(euros);
			expect(apart).toBeGreaterThan(euros * 1.15);
		}
	});

	test("a day's wait costs a few euros of diamonds, a minute almost nothing", () => {
		const best = Math.max(...currencyPacks.filter((p) => p.category === "diamonds").map((p) => p.diamonds / value(p)));
		const worst = Math.min(...currencyPacks.filter((p) => p.category === "diamonds").map((p) => p.diamonds / value(p)));
		expect(getSkipDiamondCost(24 * HOUR) / best).toBeGreaterThan(1.5);
		expect(getSkipDiamondCost(24 * HOUR) / worst).toBeLessThan(5);
		expect(getSkipDiamondCost(MIN) / worst).toBeLessThan(0.05);
	});
});
