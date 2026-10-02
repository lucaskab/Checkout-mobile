import { afterAll, beforeEach, expect, mock, test } from "bun:test";
import { applyProductLevel, getProductUpgradeCost, normalizeProductLevels } from "./product-levels";

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
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();

test("a product level earns 10% more profit, never more revenue on a loss", () => {
	const sale = { revenue: 30, quantity: 2 };
	expect(applyProductLevel(sale, 10, 0)).toBe(sale);
	expect(applyProductLevel(sale, 10, 1).revenue).toBeCloseTo(31); // margin 10 → 11
	expect(applyProductLevel({ revenue: 10, quantity: 2 }, 10, 3).revenue).toBe(10);
});

test("level prices follow the expansion and stop at the top level", () => {
	expect(getProductUpgradeCost("mesinha", 0)).toBe(40);
	expect(getProductUpgradeCost("mercadinho", 0)).toBeGreaterThan(getProductUpgradeCost("tenda", 0));
	expect(getProductUpgradeCost("mesinha", 10)).toBeNull();
	expect(normalizeProductLevels({ 1: 3, x: 2, 5: -1, 9: 40 })).toEqual({ 1: 3, 9: 10 });
});

test("the store charges the level and keeps it per product", () => {
	useGameStore.setState({ coins: 1_000 });
	expect(game().upgradeProduct(1)).toBe(true);
	expect(game().productLevels[1]).toBe(1);
	expect(game().coins).toBe(960);
	useGameStore.setState({ coins: 10 });
	expect(game().upgradeProduct(1)).toBe(false);
	expect(game().upgradeProduct(999_999)).toBe(false);
});

test("the daily gift is paid once a day", () => {
	const coins = game().coins;
	expect(game().claimDailyLogin()).toBe(true);
	expect(game().coins).toBeGreaterThan(coins);
	expect(game().dailyLogin.streak).toBe(1);
	expect(game().claimDailyLogin()).toBe(false);
});
