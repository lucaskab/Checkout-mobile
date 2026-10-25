import { afterAll, beforeEach, expect, mock, test } from "bun:test";
import { createJSONStorage } from "zustand/middleware";

// Updates must never cost the players their progress (Lucas 24/10): an old save is migrated with everything kept,
// and a save that cannot be loaded is never overwritten by the fresh game that starts in its place.
// The store's storage is swapped through persist.setOptions (other test files may have loaded the store already).
globalThis.__DEV__ = false;
const guard = await import("./save-guard.ts");
mock.module("@/storage/mmkv", () => ({ mmkvStorage: { getItem: () => null, setItem: () => {}, removeItem: () => {} } }));
const { useGameStore } = await import("../stores/game-store.ts");
const memory = new Map();
const raw = {
	getItem: (key) => memory.get(key) ?? null,
	setItem: (key, value) => {
		if (!guard.blocksWrite(key)) memory.set(key, value);
	},
	removeItem: (key) => {
		if (!guard.blocksWrite(key)) memory.delete(key);
	},
};
const original = useGameStore.persist.getOptions().storage;
const initial = JSON.stringify(useGameStore.getState());
const saved = (state) => JSON.parse(JSON.stringify(useGameStore.persist.getOptions().partialize(state)));

beforeEach(() => {
	guard.unlockSave();
	memory.clear();
	useGameStore.persist.setOptions({ storage: createJSONStorage(() => raw) });
	useGameStore.setState(JSON.parse(initial));
});
afterAll(() => {
	guard.unlockSave();
	useGameStore.persist.setOptions({ storage: original });
	useGameStore.setState(JSON.parse(initial));
});

test("a save from an older build loads with the player's level, coins and expansion", async () => {
	const state = JSON.parse(initial);
	state.market = { ...state.market, level: 12 };
	state.era = { ...state.era, id: "spati" };
	state.coins = 54_321;
	for (const version of [40, 41, 42, 43, 44, 45]) {
		memory.set("checkout.game", JSON.stringify({ state: saved(state), version }));
		await useGameStore.persist.rehydrate();
		const now = useGameStore.getState();
		expect(guard.isSaveLocked()).toBe(false);
		expect(now.market.level).toBe(12);
		expect(now.era.id).toBe("spati");
		expect(now.coins).toBe(54_321);
	}
});

test("a save that cannot be loaded is kept on disk instead of being replaced by a new game", async () => {
	memory.set("checkout.game", "{ not json");
	await useGameStore.persist.rehydrate();
	expect(guard.isSaveLocked()).toBe(true);
	useGameStore.setState({ coins: 1 });
	expect(memory.get("checkout.game")).toBe("{ not json");
});
