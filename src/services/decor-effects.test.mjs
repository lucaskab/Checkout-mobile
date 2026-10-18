import { afterAll, beforeEach, expect, mock, test } from "bun:test";

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
const { getDecorEffects, rollDecorPlays } = await import("./decor-effects.ts");
const { sanitizeInteriorItems } = await import("../data/interior-decor.ts");
const { FREE_DAY_CONTRACT_ID } = await import("./market-day.ts");
const { createSimulatorSnapshot } = await import("./simulator-snapshot.ts");
useGameStore.setState({ interior: { items: [], owned: {} } });
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const store = () => useGameStore.getState();
const piece = (id, type, extra = {}) => ({ id, type, x: 0, z: 0, rot: 0, ...extra });

test("melhorias only work while placed: carts add a product, the ATM more money, machines play", () => {
	const none = getDecorEffects({ items: [piece("d1", "cart-corral", { stored: true })], owned: { "cart-corral": 1 } });
	expect(none.basketItems).toBe(0);
	const fx = getDecorEffects({
		items: [piece("d1", "cart-corral"), piece("d2", "cart-corral"), piece("d3", "atm"), piece("d4", "claw-machine"), piece("d5", "gumball"), piece("d6", "plant-small")],
		owned: {},
	});
	// carts and the ATM count once, however many stand
	expect(fx.basketItems).toBe(1);
	expect(fx.budgetMultiplier).toBeCloseTo(1.15);
	expect(fx.machines.map((m) => m.decorId).sort()).toEqual(["claw-machine", "gumball"]);
});

test("coin machines: up to three of each count, coins grow with the market", () => {
	const items = [1, 2, 3, 4].map((n) => piece(`c${n}`, "claw-machine"));
	const fx = getDecorEffects({ items, owned: {} });
	expect(fx.machines[0].itemIds.length).toBe(3);
	const plays = rollDecorPlays(fx, () => 0, 2);
	expect(plays.length).toBe(3);
	expect(plays[0].coins).toBe(12);
	expect(rollDecorPlays(fx, () => 0.99, 2)).toEqual([]);
});

test("the claw machine stands inside or outside; the others only where they belong", () => {
	const owned = { "claw-machine": 2, atm: 1 };
	expect(sanitizeInteriorItems([piece("a", "claw-machine"), piece("b", "claw-machine", { outside: true })], owned)).not.toBeNull();
	expect(sanitizeInteriorItems([piece("c", "atm", { outside: true })], owned)).toBeNull();
});

test("customers play the machines in the market: coins, day revenue and Unity's floating coins", () => {
	useGameStore.setState({
		market: { ...store().market, level: 25 },
		interior: { items: [1, 2, 3].map((n) => piece(`m${n}`, "claw-machine")).concat([1, 2, 3].map((n) => piece(`g${n}`, "gumball"))), owned: { "claw-machine": 3, gumball: 3 } },
	});
	store().startDay(FREE_DAY_CONTRACT_ID);
	const coins = store().coins;
	for (let index = 0; index < 20; index++) {
		useGameStore.setState({ market: { ...store().market, nextCustomerAt: 1 } });
		store().processNextCustomer();
	}
	const earned = Object.values(store().market.decorEarnings ?? {}).reduce((a, b) => a + b, 0);
	expect(earned).toBeGreaterThan(0);
	expect(store().coins).toBe(coins + earned);
	expect(store().day.stats.revenue).toBeGreaterThanOrEqual(earned);
	const snap = createSimulatorSnapshot(store());
	expect(snap.decorPlays.length).toBeGreaterThan(0);
	expect(snap.decorCatalog.find((d) => d.id === "claw-machine")).toMatchObject({ zone: "both", upgrade: true });
});

test("whoever bought the old 'Carrinhos de Compras' upgrade gets a cart corral to place", async () => {
	const old = JSON.parse(initial);
	old.shop.ownedItemIds = ["simple-cart", "shopping-basket"];
	const next = await useGameStore.persist.getOptions().migrate(old, 45);
	expect(next.shop.ownedItemIds).not.toContain("simple-cart");
	expect(next.interior.owned["cart-corral"]).toBe(1);
});
