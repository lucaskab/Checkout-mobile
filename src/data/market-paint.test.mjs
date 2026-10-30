import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";

// "Cores do mercado" (Lucas 30/10): two colours instead of the brand navy and gold, paid in coins or diamonds,
// the classic look free, saved with the game (and its cloud copy) and sent to Unity in every snapshot.
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
const paint = await import("./market-paint.ts");
const { marketEras } = await import("./economy.ts");
const { ERA_TURN_PROFIT } = await import("./currency-packs.ts");
const { createSimulatorSnapshot } = await import("../services/simulator-snapshot.ts");

const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const store = () => useGameStore.getState();
const money = (coins, diamonds) =>
	useGameStore.setState({ coins, logistics: { ...store().logistics, premiumCurrency: diamonds } });

describe("palettes", () => {
	test("Clássico is first and is the brand navy and gold", () => {
		expect(paint.marketPalettes[0]).toEqual({ id: "classico", name: "Clássico", primary: "1D2B4F", accent: "D3A53D" });
	});

	test("12 to 16 palettes, unique ids and pairs, valid hex", () => {
		const list = paint.marketPalettes;
		expect(list.length).toBeGreaterThanOrEqual(12);
		expect(list.length).toBeLessThanOrEqual(16);
		expect(new Set(list.map((p) => p.id)).size).toBe(list.length);
		expect(new Set(list.map((p) => p.primary + p.accent)).size).toBe(list.length);
		for (const p of list) {
			expect(paint.normalizeHex(p.primary)).toBe(p.primary);
			expect(paint.normalizeHex(p.accent)).toBe(p.accent);
		}
	});

	test("readable: white / cream letters on every main colour, and the accent stands apart", () => {
		for (const p of paint.marketPalettes) {
			expect(paint.getContrastRatio(p.primary, "FFFFFF")).toBeGreaterThanOrEqual(4.5);
			expect(paint.getContrastRatio(p.primary, "F4EFE4")).toBeGreaterThanOrEqual(4);
			expect(paint.getContrastRatio(p.primary, p.accent)).toBeGreaterThanOrEqual(2.2);
		}
	});

	test("24 swatches for any colour", () => {
		expect(paint.MARKET_PAINT_SWATCHES).toHaveLength(24);
		expect(paint.MARKET_PAINT_SWATCHES.every((hex) => paint.normalizeHex(hex) === hex)).toBe(true);
	});
});

describe("prices", () => {
	test("diamonds fixed, coins ≈ 2.5 five-minute turns of the stage's profit", () => {
		expect(paint.MARKET_PAINT_DIAMONDS).toBe(25);
		for (const era of marketEras) {
			const price = paint.getMarketPaintCoinPrice(era.id);
			const turns5 = price / (ERA_TURN_PROFIT[era.id] / 2);
			expect(price).toBeGreaterThanOrEqual(200);
			if (era.id !== "mesinha") {
				expect(turns5).toBeGreaterThan(2);
				expect(turns5).toBeLessThan(3);
			}
		}
	});

	test("the price grows with the market", () => {
		const prices = marketEras.map((era) => paint.getMarketPaintCoinPrice(era.id));
		for (let i = 1; i < prices.length; i++) expect(prices[i]).toBeGreaterThanOrEqual(prices[i - 1]);
	});
});

describe("store", () => {
	test("a new game is classic", () => {
		expect(store().marketPaint).toEqual(paint.createMarketPaintState());
	});

	test("apply with coins: pays the stage's price, keeps diamonds, remembers the pair", () => {
		money(100_000, 50);
		const price = paint.getMarketPaintCoinPrice(store().era.id);
		expect(store().applyMarketPaint("#1f4d36", "e3c77a", "coins")).toBe(true);
		expect(store().coins).toBe(100_000 - price);
		expect(store().logistics.premiumCurrency).toBe(50);
		expect(store().marketPaint).toEqual(
			expect.objectContaining({ paletteId: "floresta", primary: "1F4D36", accent: "E3C77A", purchases: 1 }),
		);
		expect(store().marketPaint.recent.map((r) => r.paletteId)).toEqual(["floresta"]);
	});

	test("apply with diamonds: 25 diamonds, coins untouched; a custom pair is 'custom'", () => {
		money(10, 100);
		expect(store().applyMarketPaint("C2185B", "00B8D4", "diamonds")).toBe(true);
		expect(store().logistics.premiumCurrency).toBe(75);
		expect(store().coins).toBe(10);
		expect(store().marketPaint.paletteId).toBe("custom");
	});

	test("not enough coins: refused, nothing changes", () => {
		money(10, 100);
		expect(store().applyMarketPaint("8A1C2B", "D9A93E", "coins")).toBe(false);
		expect(store().marketPaint.primary).toBe("1D2B4F");
		expect(store().coins).toBe(10);
	});

	test("not enough diamonds: refused and the diamond store is asked for", () => {
		money(100_000, 3);
		expect(store().applyMarketPaint("8A1C2B", "D9A93E", "diamonds")).toBe(false);
		expect(store().diamondShortfall).toEqual(expect.objectContaining({ needed: 25, missing: 22 }));
		expect(store().marketPaint.primary).toBe("1D2B4F");
	});

	test("the same colours again or a bad colour: refused for free", () => {
		money(100_000, 100);
		expect(store().applyMarketPaint("1D2B4F", "D3A53D", "coins")).toBe(false);
		expect(store().applyMarketPaint("blue", "D3A53D", "coins")).toBe(false);
		expect(store().coins).toBe(100_000);
	});

	test("back to classic never costs and keeps the paid pair in Recentes", () => {
		money(100_000, 100);
		store().applyMarketPaint("8A1C2B", "D9A93E", "coins");
		const coins = store().coins;
		expect(store().resetMarketPaint()).toBe(true);
		expect(store().coins).toBe(coins);
		expect(store().logistics.premiumCurrency).toBe(100);
		expect(paint.isClassicPaint(store().marketPaint)).toBe(true);
		expect(store().marketPaint.recent.map((r) => r.paletteId)).toEqual(["cereja"]);
		expect(store().resetMarketPaint()).toBe(false);
		// classic through apply is the same free reset
		store().applyMarketPaint("2E3236", "BFC5CC", "coins");
		const after = store().coins;
		expect(store().applyMarketPaint("1d2b4f", "d3a53d", "diamonds")).toBe(true);
		expect(store().coins).toBe(after);
		expect(store().logistics.premiumCurrency).toBe(100);
	});

	test("Recentes: the last 3 applied, newest first, no repeats", () => {
		money(1_000_000, 0);
		for (const id of ["floresta", "cereja", "uva", "cereja", "oceano"]) {
			const p = paint.getMarketPalette(id);
			store().applyMarketPaint(p.primary, p.accent, "coins");
		}
		expect(store().marketPaint.recent.map((r) => r.paletteId)).toEqual(["oceano", "cereja", "uva"]);
	});

	test("snapshot: colours, palettes, recent and prices for Unity", () => {
		money(100_000, 0);
		store().applyMarketPaint("4B2A6B", "C9CED6", "coins");
		const snapshot = createSimulatorSnapshot(store());
		expect(snapshot.paint).toEqual(
			expect.objectContaining({ primary: "4B2A6B", accent: "C9CED6", palette: "uva", diamondPrice: 25 }),
		);
		expect(snapshot.paint.coinPrice).toBe(paint.getMarketPaintCoinPrice(store().era.id));
		expect(snapshot.paint.palettes).toHaveLength(paint.marketPalettes.length);
		expect(snapshot.paint.recent[0]).toEqual({ id: "uva", name: "Uva", primary: "4B2A6B", accent: "C9CED6" });
	});
});

describe("saves", () => {
	test("v46 saves (no field) migrate to the classic look and keep everything else", async () => {
		const state = JSON.parse(initial);
		delete state.marketPaint;
		const migrate = useGameStore.persist.getOptions().migrate;
		const migrated = await migrate({ ...state, coins: 1234 }, 46);
		expect(migrated.marketPaint).toEqual(paint.createMarketPaintState());
		expect(migrated.coins).toBe(1234);
		expect(useGameStore.persist.getOptions().version).toBe(47);
	});

	test("a malformed field falls back to classic; a good one is kept", () => {
		expect(paint.normalizeMarketPaintState({ primary: "zzz", accent: 3 })).toEqual(paint.createMarketPaintState());
		expect(
			paint.normalizeMarketPaintState({
				primary: "#5e4f8c",
				accent: "f3e9c6",
				recent: [{ primary: "8A1C2B", accent: "D9A93E" }, { primary: "x" }, null],
				purchases: 2.7,
			}),
		).toEqual({
			paletteId: "lavanda",
			primary: "5E4F8C",
			accent: "F3E9C6",
			recent: [{ paletteId: "cereja", primary: "8A1C2B", accent: "D9A93E" }],
			purchases: 2,
		});
	});

	test("the colours are saved with the game (and so in the cloud copy)", () => {
		money(100_000, 0);
		store().applyMarketPaint("0F6A6E", "F27D5E", "coins");
		const saved = useGameStore.persist.getOptions().partialize(store());
		expect(saved.marketPaint).toEqual(expect.objectContaining({ primary: "0F6A6E", accent: "F27D5E", paletteId: "oceano" }));
	});
});
