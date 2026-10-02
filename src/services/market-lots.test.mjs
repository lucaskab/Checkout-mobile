import { afterAll, beforeEach, expect, mock, test } from "bun:test";
import {
	checkBuyLot,
	getLotStatus,
	getMissingLots,
	isLotReachable,
	normalizeLotsState,
} from "./market-lots";

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
const { createSimulatorSnapshot } = await import("./simulator-snapshot.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();
const none = { owned: [], cleared: [], clearing: null };

test("A1 comes first, then only lots next to your land", () => {
	expect(isLotReachable(none, "A1")).toBe(true);
	expect(isLotReachable(none, "B1")).toBe(false);
	const one = { owned: ["A1"], cleared: [], clearing: null };
	expect(isLotReachable(one, "B1")).toBe(true);
	expect(isLotReachable(one, "A2")).toBe(true);
	expect(isLotReachable(one, "B2")).toBe(false); // only a corner touches A1
	expect(isLotReachable(one, "C1")).toBe(false);
	expect(getLotStatus(none, "B1")).toBe("bloqueado");
	expect(checkBuyLot(none, 1e9, "Z9").ok).toBe(false);
});

test("the block is a grid of 12 equal lots covering it all", async () => {
	const { MARKET_LOTS } = await import("@/data/market-lots");
	expect(MARKET_LOTS).toHaveLength(12);
	const area = MARKET_LOTS.reduce((sum, lot) => sum + (lot.x1 - lot.x0) * (lot.z1 - lot.z0), 0);
	expect(Math.round(area)).toBe(Math.round(34.5 * 53));
	expect(new Set(MARKET_LOTS.map((lot) => lot.ruin)).size).toBe(12);
	const a1 = MARKET_LOTS.find((lot) => lot.id === "A1");
	expect(a1.x0).toBe(-17.25);
	expect(a1.z0).toBe(-8.5);
});

test("old saves keep the lots their expansion stands on", () => {
	expect(normalizeLotsState(undefined, "supermercado").cleared).toEqual(["A1", "B1", "A2", "B2", "C1", "B3"]);
	expect(normalizeLotsState(undefined, "mesinha").owned).toEqual([]);
	expect(normalizeLotsState({ owned: ["A1"], cleared: ["A1"], clearing: null }, "mesinha").cleared).toEqual(["A1"]);
	expect(getMissingLots(none, "tenda")).toEqual(["A1"]);
	expect(getMissingLots(none, "minimercado")).toEqual(["A1", "B1"]);
});

test("buying, clearing with the crew and finishing with diamonds", () => {
	useGameStore.setState({ coins: 1_000 });
	expect(game().clearLot("A1")).toBe(false);
	expect(game().buyLot("A1")).toBe(true);
	expect(game().coins).toBe(700);
	expect(getLotStatus(game().lots, "A1")).toBe("comprado");
	expect(game().clearLot("A1")).toBe(true);
	expect(getLotStatus(game().lots, "A1")).toBe("limpando");
	const xp = game().market.totalExperience;
	expect(game().finishLotClearingNow()).toBe(true);
	expect(getLotStatus(game().lots, "A1")).toBe("seu");
	expect(game().market.totalExperience).toBeGreaterThan(xp);
	const lot = createSimulatorSnapshot(game(), "t", 1).era.lotRects.find((item) => item.id === "A1");
	expect(lot.status).toBe("seu");
	// Now the tenda can be built.
	expect(game().evolveMarketEra()).toBe(true);
});

test("passing time also finishes the clearing", () => {
	useGameStore.setState({ coins: 1_000 });
	game().buyLot("A1");
	game().clearLot("A1");
	expect(game().devPassTime(1)).toBe(true);
	expect(game().lots.cleared).toContain("A1");
});
