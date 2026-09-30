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
const { itemCatalog } = await import("../data/market-products.ts");
const { getShelfSlotIds } = await import("../data/shelf-slots.ts");
const { getShelfOrderQuote } = await import("./shelf-order-quote.ts");
const { createSimulatorSnapshot } = await import("./simulator-snapshot.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
function available() {
	const state = useGameStore.getState();
	return itemCatalog.filter(
		(p) => !Object.values(state.shelfAssignments).includes(p.id),
	);
}
function unlock(product) {
	const s = useGameStore.getState();
	s.unlockProduct(product.id);
	useGameStore.setState({ inventory: { ...s.inventory, [product.id]: 5 } });
}
test("four different products share one physical shelf and reject a fifth or a locked shelf", () => {
	const products = available().slice(0, 4);
	for (let i = 0; i < 3; i++) {
		unlock(products[i]);
		expect(
			useGameStore
				.getState()
				.assignProductToShelf(`produce:${i + 1}`, products[i].id),
		).toBe(true);
	}
	unlock(products[3]);
	expect(
		useGameStore.getState().assignProductToShelf("produce:4", products[3].id),
	).toBe(false);
	expect(
		useGameStore.getState().assignProductToShelf("pizza:1", products[3].id),
	).toBe(false);
	expect(
		useGameStore.getState().assignProductToShelf("dairy:1", products[0].id),
	).toBe(false);
	expect(
		getShelfSlotIds("produce").filter(
			(id) => useGameStore.getState().shelfAssignments[id],
		),
	).toHaveLength(4);
});
test("restocking, replacing and removing preserve inventory quantities and expiry lots", () => {
	const [a, b] = available();
	unlock(a);
	unlock(b);
	const actions = useGameStore.getState();
	expect(actions.assignProductToShelf("produce:1", a.id)).toBe(true);
	expect(
		actions.restockShelf({ shelfId: "produce:1", productId: a.id, amount: 3 }),
	).toBe(true);
	const expiry = useGameStore.getState().shelfLots["produce:1"];
	expect(useGameStore.getState().inventory[a.id]).toBe(2);
	expect(actions.assignProductToShelf("produce:1", b.id, true)).toBe(true);
	expect(useGameStore.getState().inventory[a.id]).toBe(5);
	for (const lot of expiry)
		expect(
			useGameStore
				.getState()
				.inventoryLots[a.id].some((l) => l.expiresAt === lot.expiresAt),
		).toBe(true);
	expect(useGameStore.getState().shelfStock["produce:1"]).toBe(0);
	expect(
		actions.restockShelf({ shelfId: "produce:1", productId: b.id, amount: 2 }),
	).toBe(true);
	expect(actions.clearShelf("produce:1")).toBe(true);
	expect(useGameStore.getState().inventory[b.id]).toBe(5);
});
test("failed replacement leaves the current selection and lots intact", () => {
	const [a, b] = available();
	unlock(a);
	unlock(b);
	const actions = useGameStore.getState();
	actions.assignProductToShelf("produce:1", a.id);
	actions.restockShelf({ shelfId: "produce:1", productId: a.id, amount: 3 });
	useGameStore.setState({
		inventory: { ...useGameStore.getState().inventory, [a.id]: 999 },
	});
	const before = JSON.stringify(useGameStore.getState());
	expect(actions.assignProductToShelf("produce:1", b.id, true)).toBe(false);
	expect(JSON.stringify(useGameStore.getState())).toBe(before);
});
test("version 28 migration fills unlocked shelves with four available slots", async () => {
	const old = JSON.parse(initial);
	old.coins = 19387;
	old.market.level = 17;
	old.market.experience = 631;
	old.unlockedShelfSlots = 7;
	const next = await useGameStore.persist.getOptions().migrate(old, 28);
	expect(next.shelfSlotCounts.produce).toBe(4);
	expect(next.shelfSlotCounts.dairy).toBe(4);
	expect(next.unlockedShelfSlots).toBe(8);
	expect(next.shelfAssignments.produce).toBe(old.shelfAssignments.produce);
	expect(next.shelfAssignments["produce:1"]).toBe(null);
});
test("unlocks complete shelves and expands only the selected shelf", () => {
	useGameStore.getState().setMarketLevel(3);
	useGameStore.setState({ coins: 5_000 });

	expect(useGameStore.getState().unlockNextShelf()).toBe(true);
	// The shop comes with produce, dairy and the drinks cooler; the first shelf bought is the bakery one.
	// It waits in the inventory; placed in the shop, the builders need a moment.
	expect(useGameStore.getState().shelfSlotCounts.bakery).toBe(0);
	expect(useGameStore.getState().saveInteriorLayout([{ id: "shelf:bakery", type: "shelf", x: 0, z: 1, rot: 0 }])).toBe(true);
	expect(useGameStore.getState().processInteriorConstructions(Number.MAX_SAFE_INTEGER)).toBe(true);
	let state = useGameStore.getState();
	expect(state.shelfSlotCounts.produce).toBe(4);
	expect(state.shelfSlotCounts.bakery).toBe(4);
	expect(state.unlockedShelfSlots).toBe(16);

	expect(state.expandShelfSlots("produce")).toBe(true);
	state = useGameStore.getState();
	expect(state.shelfSlotCounts.produce).toBe(5);
	expect(state.shelfSlotCounts.dairy).toBe(4);
	expect(state.unlockedShelfSlots).toBe(17);
});
test("capacity upgrades apply to all four spaces and persist new assignments", async () => {
	const [a] = available();
	unlock(a);
	const actions = useGameStore.getState();
	actions.assignProductToShelf("produce:3", a.id);
	useGameStore.setState({ shelfUpgradeLevels: { produce: 1 } });
	expect(
		actions.restockShelf({ shelfId: "produce:3", productId: a.id, amount: 5 }),
	).toBe(true);
	await useGameStore.persist.rehydrate();
	expect(useGameStore.getState().shelfStock["produce:3"]).toBe(5);
	expect(useGameStore.getState().shelfAssignments["produce:3"]).toBe(a.id);
});
test("order quote matches charged price and delivery duration with current modifiers", () => {
	const [product] = available();
	unlock(product);
	useGameStore.setState({
		coins: 100000,
		inventory: { ...useGameStore.getState().inventory, [product.id]: 0 },
	});
	const state = useGameStore.getState();
	const quote = getShelfOrderQuote(state, product.id, 2);
	expect(quote.reason).toBe(null);
	expect(state.placeSupplierOrder({ productId: product.id, quantity: 2 })).toBe(
		true,
	);
	const after = useGameStore.getState();
	expect(after.coins).toBe(state.coins - quote.total);
	expect(after.logistics.orders[0].deliveryDurationMs).toBe(quote.duration);
	expect(getShelfOrderQuote(after, product.id, 2).incoming).toBe(2);
	expect(getShelfOrderQuote(after, product.id, 999).reason).not.toBe(null);
});
test("Unity receives seven physical shelves and customer destinations use the parent shelf", () => {
	const state = useGameStore.getState();
	useGameStore.setState({
		market: {
			...state.market,
			recentCustomers: [
				{
					id: "test",
					purchases: [
						{ shelfId: "produce:2", productId: 1, quantity: 1, revenue: 18 },
					],
				},
			],
		},
	});
	const snapshot = createSimulatorSnapshot(useGameStore.getState(), "test", 1);
	expect(snapshot.shelves).toHaveLength(7);
	expect(snapshot.customers[0].purchases[0].shelfId).toBe("produce");
});
test("logistics turbo only charges diamonds when it can be activated", () => {
	const state = useGameStore.getState();
	useGameStore.setState({
		logistics: { ...state.logistics, premiumCurrency: 2 },
	});
	expect(useGameStore.getState().activateLogisticsBoost()).toBe(false);
	expect(useGameStore.getState().logistics.premiumCurrency).toBe(2);
	useGameStore.setState({
		logistics: { ...useGameStore.getState().logistics, premiumCurrency: 3 },
	});
	const before = Date.now();
	expect(useGameStore.getState().activateLogisticsBoost()).toBe(true);
	const logistics = useGameStore.getState().logistics;
	expect(logistics.premiumCurrency).toBe(0);
	expect(logistics.logisticsBoostExpiresAt).toBeGreaterThanOrEqual(
		before + 15 * 60_000,
	);
});
