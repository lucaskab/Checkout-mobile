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
const { createSimulatorSnapshot } = await import("./simulator-snapshot.ts");
const { FREE_DAY_CONTRACT_ID } = await import("./market-day.ts");
const { getWaitingInteriorPieces } = await import("../data/interior-decor.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();

const placed = [
	{ id: "checkout:main", type: "checkout", x: -4, z: -4.6, rot: 90 },
	{ id: "shelf:produce", type: "shelf", x: -6, z: 2, rot: 0 },
	{ id: "shelf:dairy", type: "shelf", x: -2, z: 2, rot: 0 },
	{ id: "shelf:drinks", type: "shelf", x: 2, z: 2, rot: 0 },
];

test("a new shop is empty: the checkout, two shelves and the drinks cooler wait to be placed", () => {
	const waiting = getWaitingInteriorPieces(game().interior).map((item) => item.id);
	expect(waiting.sort()).toEqual(["checkout:main", "shelf:dairy", "shelf:drinks", "shelf:produce"]);
	const view = createSimulatorSnapshot(game(), "start", 1);
	expect(view.interior.items.every((item) => item.stored)).toBe(true);
	expect(view.shelves.filter((s) => s.unlocked).map((s) => s.id)).toEqual(["produce", "dairy", "drinks"]);
	expect(view.shelves.find((s) => s.id === "drinks").name).toBe("Geladeira de bebidas");
});

test("the market only opens once the player has placed the furniture", () => {
	expect(game().startDay(FREE_DAY_CONTRACT_ID)).toBe(false);
	game().setMarketOpen(true);
	expect(game().market.isOpen).toBe(false);
	// Placing only some pieces is not enough.
	expect(game().saveInteriorLayout([placed[0], ...placed.slice(1).map((p) => ({ ...p, stored: true }))])).toBe(true);
	expect(game().startDay(FREE_DAY_CONTRACT_ID)).toBe(false);
	expect(game().saveInteriorLayout(placed)).toBe(true);
	expect(getWaitingInteriorPieces(game().interior)).toHaveLength(0);
	expect(game().startDay(FREE_DAY_CONTRACT_ID)).toBe(true);
	expect(game().market.isOpen).toBe(true);
});

test("a reset brings the empty shop back", () => {
	game().saveInteriorLayout(placed);
	game().resetGame();
	expect(getWaitingInteriorPieces(game().interior)).toHaveLength(4);
});
