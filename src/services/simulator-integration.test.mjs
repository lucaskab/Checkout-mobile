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
const { isShelfSlotUnlocked } = await import("../data/shelf-slots.ts");
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
	expect(snapshot().shelves.filter((s) => s.unlocked)).toHaveLength(1);
});
test("simulator maps every four system slots to one physical shelf", () => {
	const countUnlockedShelves = () =>
		snapshot().shelves.filter((shelf) => shelf.unlocked).length;

	expect(countUnlockedShelves()).toBe(1);
	useGameStore.setState({ unlockedShelfSlots: 5 });
	expect(countUnlockedShelves()).toBe(2);
	expect(isShelfSlotUnlocked("dairy", 5)).toBe(true);
	expect(isShelfSlotUnlocked("dairy:1", 5)).toBe(true);
	useGameStore.setState({ unlockedShelfSlots: 6 });
	expect(countUnlockedShelves()).toBe(2);
	useGameStore.setState({ unlockedShelfSlots: 7 });
	expect(countUnlockedShelves()).toBe(2);
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
	expect(view.shelves.find((s) => s.id === "coffee").requiredLevel).toBe(66);
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

test("an eligible expansion can be unlocked with diamonds", () => {
	const state = useGameStore.getState();
	useGameStore.setState({
		coins: 0,
		logistics: { ...state.logistics, premiumCurrency: 10 },
		market: { ...state.market, level: 4 },
	});

	expect(
		useGameStore.getState().unlockMarketExpansion("fresh-wing", "diamonds"),
	).toBe(true);
	expect(useGameStore.getState().coins).toBe(0);
	expect(useGameStore.getState().logistics.premiumCurrency).toBe(2);
	expect(snapshot().expansions).toContain("fresh-wing");
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

test("level alone never builds simulator expansions", () => {
	const state = useGameStore.getState();
	useGameStore.setState({ market: { ...state.market, level: 30 } });
	const view = snapshot();
	expect(view.layout.stage).toBe(0);
	expect(view.layout.storage).toBe(false);
	expect(view.layout.parking).toBe(false);
	expect(view.layout.sectorIds).toEqual(["padaria"]);
});

test("paid expansions progressively enlarge the simulator and survive snapshot recreation", () => {
	const state = useGameStore.getState();
	useGameStore.setState({
		coins: 500_000,
		market: { ...state.market, level: 30 },
	});
	const ids = ["fresh-wing", "service-wing", "stock-annex", "premium-hall"];
	let previous = snapshot().layout;
	for (const [index, id] of ids.entries()) {
		expect(useGameStore.getState().unlockMarketExpansion(id)).toBe(true);
		const current = snapshot().layout;
		expect(current.stage).toBe(index + 1);
		expect(current.widthScale * current.depthScale).toBeGreaterThan(
			previous.widthScale * previous.depthScale,
		);
		const coins = useGameStore.getState().coins;
		expect(useGameStore.getState().unlockMarketExpansion(id)).toBe(false);
		expect(useGameStore.getState().coins).toBe(coins);
		expect(
			createSimulatorSnapshot(
				JSON.parse(JSON.stringify(useGameStore.getState())),
				"reload",
				0,
			).layout,
		).toEqual(current);
		previous = current;
	}
	expect(previous).toEqual(
		expect.objectContaining({
			storage: true,
			parking: true,
			loadingYard: true,
			premium: true,
		}),
	);
	expect(previous.sectorIds).toEqual([
		"padaria",
		"queijaria",
		"acougue",
		"peixaria",
		"bebidas",
		"sorvetes",
	]);
});

test("independent expansion purchases do not grant other paid areas", () => {
	const state = useGameStore.getState();
	useGameStore.setState({
		coins: 500_000,
		market: { ...state.market, level: 30 },
	});
	expect(useGameStore.getState().unlockMarketExpansion("service-wing")).toBe(
		true,
	);
	expect(snapshot().layout).toEqual(
		expect.objectContaining({
			stage: 1,
			parking: true,
			storage: false,
			loadingYard: false,
			premium: false,
			sectorIds: ["padaria", "acougue", "bebidas"],
		}),
	);
});

test("cold sector production and customer destinations stay shared between System and simulator", () => {
	const state = useGameStore.getState();
	useGameStore.setState({
		coins: 500_000,
		market: { ...state.market, level: 30 },
		inventory: { ...state.inventory, 5: 5, 8: 5, 13: 5, 21: 5, 24: 5 },
	});
	const game = useGameStore.getState();
	let revision = 1;
	const unsubscribe = useGameStore.subscribe(() => revision++);
	const run = createSimulatorCommandHandler(
		"integration",
		() => useGameStore.getState(),
		() => revision,
	);
	expect(
		run({
			protocol: 1,
			session: "integration",
			id: "cold-beverage-production",
			revision,
			action: "startProduction",
			args: [{ sectorId: "bebidas", recipeId: "suco-gelado" }],
		}).ok,
	).toBe(true);
	unsubscribe();
	expect(
		game.startProduction({ sectorId: "sorvetes", recipeId: "sorvete-creme" }),
	).toBe(true);
	expect(snapshot().sectors.find((s) => s.id === "bebidas").jobs).toBe(1);
	expect(snapshot().sectors.find((s) => s.id === "sorvetes").jobs).toBe(1);
	const queued = useGameStore.getState().production;
	useGameStore.setState({
		production: {
			...queued,
			jobs: queued.jobs.map((job) => ({ ...job, endsAt: Date.now() - 1 })),
		},
	});
	expect(useGameStore.getState().processProductionJobs()).toBe(true);
	expect(useGameStore.getState().inventory[113]).toBe(4);
	expect(useGameStore.getState().inventory[116]).toBe(4);
	expect(
		useGameStore.getState().startProduction({
			sectorId: "sorvetes",
			recipeId: "sundae-chocolate",
		}),
	).toBe(true);
	expect(
		useGameStore.getState().startProduction({
			sectorId: "sorvetes",
			recipeId: "pote-sorvete-familia",
		}),
	).toBe(true);
	expect(snapshot().layout.sectorIds).not.toContain("bebidas");
	expect(useGameStore.getState().unlockMarketExpansion("service-wing")).toBe(
		true,
	);
	expect(snapshot().layout.sectorIds).toContain("bebidas");
	expect(snapshot().layout.sectorIds).not.toContain("sorvetes");
	expect(useGameStore.getState().unlockMarketExpansion("premium-hall")).toBe(
		true,
	);
	expect(snapshot().layout.sectorIds).toContain("sorvetes");
	const current = useGameStore.getState();
	useGameStore.setState({
		market: {
			...current.market,
			recentCustomers: [
				{
					id: "cold-sector-customer",
					spent: 40,
					purchases: [
						{ shelfId: "produce", productId: 116, quantity: 1, revenue: 40 },
					],
				},
			],
		},
	});
	expect(snapshot().customers[0].purchases[0].shelfId).toBe("sector-sorvetes");
});

test("unbuilt production counters keep customers at their authoritative shelf", () => {
	const state = useGameStore.getState();
	useGameStore.setState({
		coins: 10_000,
		market: {
			...state.market,
			level: 6,
			recentCustomers: [
				{
					id: "cheese",
					spent: 12,
					purchases: [
						{ shelfId: "produce", productId: 104, quantity: 1, revenue: 12 },
					],
				},
			],
		},
	});
	expect(snapshot().customers[0].purchases[0].shelfId).toBe("produce");
	expect(useGameStore.getState().unlockMarketExpansion("fresh-wing")).toBe(
		true,
	);
	expect(snapshot().customers[0].purchases[0].shelfId).toBe("sector-queijaria");
});
