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
const { getMissionRewardPlan, describeMissionReward } = await import("./missions.ts");
const { missions } = await import("../data/missions.ts");
const { getInventoryCapacity } = await import("../data/inventory-capacity.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();

// A finished mission whose prize includes products.
const mission = missions.find((m) => (m.reward.items ?? []).length > 0 && m.requiredLevel <= 1 && !m.requiredEra);
const item = mission.reward.items[0];
const product = itemCatalog.find((p) => p.id === item.productId);
const finish = () =>
	useGameStore.setState((s) => ({
		market: {
			...s.market,
			customersServed: 1e9, customersWhoBought: 1e9, unitsSold: 1e9, totalRevenue: 1e12, level: 99,
			soldByProduct: new Proxy({}, { get: () => 1e9 }),
			unlockedProductIds: [...s.market.unlockedProductIds, item.productId],
		},
		inventory: { ...s.inventory, [mission.targetProductId ?? -1]: 1e9 },
	}));

test("a full stockroom never blocks the mission: the products come as coins", () => {
	finish();
	const full = getInventoryCapacity(product, 0);
	useGameStore.setState((s) => ({ inventory: { ...s.inventory, [item.productId]: full } }));
	const coins = game().coins;
	const plan = getMissionRewardPlan(mission, game());
	expect(plan.stored).toEqual([]);
	expect(plan.sold[0]).toMatchObject({ productId: item.productId, quantity: item.quantity, reason: "full" });
	expect(describeMissionReward(mission, game()).join(" ")).toContain("sem espaço no depósito");
	expect(game().claimMission(mission.id)).toBe(true);
	expect(game().coins).toBe(coins + plan.coins);
	expect(game().inventory[item.productId]).toBe(full);
});

test("with room the products go to the stockroom and only the mission coins are paid", () => {
	finish();
	useGameStore.setState((s) => ({ inventory: { ...s.inventory, [item.productId]: 0 } }));
	const coins = game().coins;
	expect(game().claimMission(mission.id)).toBe(true);
	expect(game().coins).toBe(coins + mission.reward.coins);
	expect(game().inventory[item.productId]).toBe(item.quantity);
});
