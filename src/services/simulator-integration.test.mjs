import { beforeEach, expect, mock, test } from "bun:test";

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
const { createSimulatorCommandHandler } = await import(
	"./simulator-protocol.ts"
);
const { gameEvents } = await import("../data/game-events.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const { getInventoryCapacity } = await import("../data/inventory-capacity.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
const snapshot = () =>
	createSimulatorSnapshot(useGameStore.getState(), "integration", 1);
test("System stock and prices reach the Unity projection", () => {
	const s = useGameStore.getState();
	const id = s.shelfAssignments.bakery;
	expect(s.setShelfPrice("bakery", 7)).toBe(true);
	const shelf = snapshot().shelves.find((s) => s.id === "bakery");
	expect(shelf.productId).toBe(id);
	expect(shelf.price).toBe(7);
	expect(shelf.stock).toBe(useGameStore.getState().shelfStock.bakery);
});
test("Unity requests use the real store rules and are reflected in System", () => {
	let revision = 1;
	const unsubscribe = useGameStore.subscribe(() => revision++);
	const run = createSimulatorCommandHandler(
		"integration",
		() => useGameStore.getState(),
		() => revision,
	);
	const cmd = {
		protocol: 1,
		session: "integration",
		id: "open",
		revision,
		action: "setMarketOpen",
		args: [true],
	};
	expect(run(cmd).ok).toBe(true);
	expect(useGameStore.getState().market.isOpen).toBe(true);
	expect(snapshot().isOpen).toBe(true);
	expect(run(cmd).ok).toBe(true);
	expect(useGameStore.getState().statistics.marketOpenings).toBe(1);
	unsubscribe();
});
test("all 20 events project their actual identities and authoritative multipliers", () => {
	for (const event of gameEvents) {
		expect(useGameStore.getState().devActivateGameEvent(event.id)).toBe(true);
		const view = snapshot();
		expect(view.event.id).toBe(event.id);
		expect(view.event.arrivalMultiplier).toBe(
			event.effects.customerArrivalMultiplier ?? 1,
		);
		expect(view.event.productionMultiplier).toBe(
			event.effects.productionDurationMultiplier ?? 1,
		);
	}
});
test("closed market cannot sell just because the renderer requests a snapshot", () => {
	const before = JSON.stringify(useGameStore.getState());
	for (let i = 0; i < 20; i++) snapshot();
	expect(JSON.stringify(useGameStore.getState())).toBe(before);
});
test("new players do not see unlocked high-level production sectors", () => {
	expect(snapshot().sectors.every((s) => !s.unlocked)).toBe(true);
	expect(snapshot().shelves.filter((s) => s.unlocked)).toHaveLength(4);
});
test("System and simulator keep the five-unit capacity and exact supplier order quantity", () => {
	const product = itemCatalog.find((product) => product.id === 1);
	expect(getInventoryCapacity(product)).toBe(5);
	const state = useGameStore.getState();
	useGameStore.setState({ inventory: { ...state.inventory, 1: 0 } });
	expect(
		useGameStore.getState().placeSupplierOrder({ productId: 1, quantity: 3 }),
	).toBe(true);
	expect(useGameStore.getState().logistics.orders[0].quantity).toBe(3);
	expect(snapshot().orders[0].quantity).toBe(3);
	expect(snapshot().orders[0].productCategory).toBe(product.category);
});
test("simulator receives the same level roadmap and reward status as System", () => {
	const view = snapshot();
	expect(view.experience).toBe(useGameStore.getState().market.experience);
	expect(view.experienceToNextLevel).toBeGreaterThan(0);
	expect(view.dailyGoal).toBe(useGameStore.getState().daily.goal);
	expect(view.shelves.find((s) => s.id === "coffee").requiredLevel).toBe(6);
	expect(view.sectors.find((s) => s.id === "padaria").requiredLevel).toBe(2);
	expect(view.expansionStates.find((e) => e.id === "fresh-wing")).toEqual(
		expect.objectContaining({ requiredLevel: 4, unlocked: false }),
	);
});
test("an unaffordable expansion remains locked from either mode", () => {
	expect(useGameStore.getState().unlockMarketExpansion("premium-hall")).toBe(
		false,
	);
	expect(snapshot().expansions).not.toContain("premium-hall");
});

test("production purchases visit their unlocked counter without changing persisted shelf assignments", () => {
	const state = useGameStore.getState();
	const purchase = {
		shelfId: "produce",
		productId: 101,
		quantity: 1,
		revenue: 12,
	};
	useGameStore.setState({
		market: {
			...state.market,
			level: 2,
			recentCustomers: [
				{ id: "counter-test", spent: 12, purchases: [purchase] },
			],
		},
	});
	expect(snapshot().customers[0].purchases[0].shelfId).toBe("sector-padaria");
	expect(
		useGameStore.getState().market.recentCustomers[0].purchases[0].shelfId,
	).toBe("produce");
	useGameStore.setState({
		market: { ...useGameStore.getState().market, level: 1 },
	});
	expect(snapshot().customers[0].purchases[0].shelfId).toBe("produce");
});
