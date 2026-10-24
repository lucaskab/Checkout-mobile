import { afterAll, beforeEach, expect, mock, test } from "bun:test";

// Updates must never cost the players their progress (Lucas 24/10): an old save is migrated with everything kept,
// and a save that cannot be loaded is never overwritten by the fresh game that starts in its place.
globalThis.__DEV__ = false;
const guard = await import("./save-guard.ts");
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => {
			if (!guard.blocksWrite(key)) memory.set(key, value);
		},
		removeItem: (key) => {
			if (!guard.blocksWrite(key)) memory.delete(key);
		},
	},
}));
const { useGameStore } = await import("../stores/game-store.ts");
const initial = JSON.stringify(useGameStore.getState());
const options = () => useGameStore.persist.getOptions();
function saved(state) {
	const persisted = options().partialize(state);
	return JSON.parse(JSON.stringify(persisted));
}

beforeEach(() => {
	guard.unlockSave();
	memory.clear();
	useGameStore.setState(JSON.parse(initial));
});
afterAll(() => {
	guard.unlockSave();
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
