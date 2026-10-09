import { afterAll, beforeEach, expect, mock, test } from "bun:test";
import { normalizeCelebrations, pushCelebration } from "./celebrations.ts";

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

test("the queue keeps the latest conquests, without repeating one", () => {
	let list = pushCelebration([], "lot", "A1", 1);
	list = pushCelebration(list, "lot", "A1", 2);
	expect(list).toHaveLength(1);
	for (let i = 0; i < 6; i++) list = pushCelebration(list, "shelf", `s${i}`, 10 + i);
	expect(list).toHaveLength(4);
	expect(list.at(-1).targetId).toBe("s5");
	expect(normalizeCelebrations([{ id: "x", kind: "nope", targetId: "a", at: 1 }, ...list])).toHaveLength(4);
	expect(normalizeCelebrations(undefined)).toEqual([]);
});

test("a lot the crew finishes clearing is celebrated until the player closes it", () => {
	useGameStore.setState({ coins: 1_000_000, lots: { owned: ["A1"], cleared: [], clearing: null } });
	expect(game().clearLot("A1")).toBe(true);
	expect(game().celebrations ?? []).toHaveLength(0);
	expect(game().processLotClearing(Number.MAX_SAFE_INTEGER)).toBe(true);
	const [celebration] = game().celebrations;
	expect(celebration).toMatchObject({ kind: "lot", targetId: "A1" });
	game().dismissCelebration(celebration.id);
	expect(game().celebrations).toEqual([]);
});

test("a new expansion and a finished sector are celebrated too", () => {
	useGameStore.setState({ era: { ...game().era, construction: { eraId: "tenda", startedAt: 0, endsAt: 1 } } });
	expect(game().processMarketEraConstruction(Date.now())).toBe(true);
	expect(game().celebrations.at(-1)).toMatchObject({ kind: "era", targetId: "tenda" });
	game().dismissCelebration(game().celebrations[0].id);
	useGameStore.setState({
		interiorConstructions: [{ id: "w1", kind: "sector", targetId: "padaria", startedAt: 0, endsAt: 1 }],
	});
	expect(game().processInteriorConstructions(Date.now())).toBe(true);
	expect(game().celebrations.at(-1)).toMatchObject({ kind: "sector", targetId: "padaria" });
});
