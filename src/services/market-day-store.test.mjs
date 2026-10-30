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
const { createSimulatorCommandHandler } = await import(
	"./simulator-protocol.ts"
);
const { FREE_DAY_CONTRACT_ID } = await import("./market-day.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const { getInventoryCapacity } = await import("../data/inventory-capacity.ts");
// These tests run a shop that is already furnished (the starter pieces are placed).
useGameStore.setState({ interior: { items: [], owned: {} } });
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
// Test files share the store module: leave it as we found it.
afterAll(() => useGameStore.setState(JSON.parse(initial)));

const store = () => useGameStore.getState();
test("choosing a contract opens the market for a five minute day", () => {
	const offer = store().day.offers[0];
	expect(store().startDay(offer.id)).toBe(true);
	expect(store().market.isOpen).toBe(true);
	expect(store().day.phase).toBe("open");
	expect(store().day.contract.id).toBe(offer.id);
	const snapshot = createSimulatorSnapshot(store(), "day", 1);
	expect(snapshot.day.phase).toBe("open");
	expect(snapshot.day.contractTitle).toBe(offer.title);
	expect(store().startDay(offer.id)).toBe(false);
});

test("the old open button still works and starts a free day", () => {
	store().setMarketOpen(true);
	expect(store().day.phase).toBe("open");
	expect(store().day.contract).toBeNull();
});

test("every day the first customer comes a few seconds after opening, not after a long empty wait", () => {
	// A save that already served customers (not the very first opening).
	useGameStore.setState({ market: { ...store().market, customersServed: 40 } });
	const before = Date.now();
	store().setMarketOpen(true);
	const wait = store().market.nextCustomerAt - before;
	expect(wait).toBeGreaterThanOrEqual(2_900);
	expect(wait).toBeLessThanOrEqual(5_500);
});

test("customers are counted in the day", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	for (let index = 0; index < 12; index++) {
		useGameStore.setState({ market: { ...store().market, nextCustomerAt: 1 } });
		expect(store().processNextCustomer()).toBe(true);
	}
	expect(store().day.stats.customers).toBe(12);
	expect(store().day.stats.satisfactionSamples).toBe(12);
	// No customer brings a special request any more (removed, Lucas 29/10): nothing about them reaches Unity.
	expect(store().day.requests).toBeUndefined();
	const snapshot = createSimulatorSnapshot(store(), "day", 1);
	expect(snapshot.day.requests).toBeUndefined();
	expect(snapshot.day.loyalty).toBeUndefined();
	expect(typeof store().resolveSpecialRequest).toBe("undefined");
});

test("at closing time the customers inside finish before the day closes", () => {
	store().startDay(store().day.offers[0].id);
	const inside = { id: "qa-inside", customerId: "c1", customerName: "Ana", items: [], categories: {}, soldByProduct: {}, units: 1, total: 10, profit: 4, experience: 1, satisfaction: 0, mood: "feliz", method: "cartao", cashGiven: 0, createdAt: Date.now(), readyAt: Date.now(), expiresAt: Date.now() + 60_000 };
	useGameStore.setState({ day: { ...store().day, endsAt: Date.now() - 1 }, checkout: { ...store().checkout, queue: [inside] } });
	// doors closed to newcomers, but the day stays open while someone is still inside
	expect(store().processMarketDay()).toBe(false);
	expect(store().day.phase).toBe("open");
	expect(store().market.isOpen).toBe(true);
	// once the last one has left, the day closes
	useGameStore.setState({ checkout: { ...store().checkout, queue: [] } });
	expect(store().processMarketDay()).toBe(true);
	expect(store().day.phase).toBe("results");
});

test("closing time has a safety cap: a forgotten line is rung up and the day ends", () => {
	store().startDay(store().day.offers[0].id);
	const inside = { id: "qa-late", customerId: "c2", customerName: "Bia", items: [], categories: {}, soldByProduct: {}, units: 1, total: 10, profit: 4, experience: 1, satisfaction: 0, mood: "feliz", method: "cartao", cashGiven: 0, createdAt: Date.now(), readyAt: Date.now(), expiresAt: Date.now() + 600_000 };
	useGameStore.setState({ day: { ...store().day, endsAt: Date.now() - 4 * 60_000 }, checkout: { ...store().checkout, queue: [inside] } });
	expect(store().processMarketDay()).toBe(true);
	expect(store().day.phase).toBe("results");
	expect(store().checkout.queue.length).toBe(0);
});

test("the day closes on time, shows results and pays rewards once claimed", () => {
	store().startDay(store().day.offers[0].id);
	useGameStore.setState({ day: { ...store().day, endsAt: Date.now() - 1 } });
	expect(store().processMarketDay()).toBe(true);
	expect(store().market.isOpen).toBe(false);
	expect(store().day.phase).toBe("results");
	const result = store().day.result;
	expect(["S", "A", "B", "C", "D"]).toContain(result.grade);
	// Reopening waits until the results are collected.
	store().setMarketOpen(true);
	expect(store().market.isOpen).toBe(false);
	const coins = store().coins;
	expect(store().claimDayResult()).toBe(true);
	expect(store().coins).toBe(coins + result.total.coins);
	expect(store().day.phase).toBe("planning");
	expect(store().day.dayNumber).toBe(2);
	expect(store().claimDayResult()).toBe(false);
});

test("Unity can run a whole day through the command protocol", () => {
	let revision = 1;
	const unsubscribe = useGameStore.subscribe(() => revision++);
	const run = createSimulatorCommandHandler(
		"day",
		() => store(),
		() => revision,
	);
	const command = (id, action, args) => ({
		protocol: 1,
		session: "day",
		id,
		revision,
		action,
		args,
	});
	expect(run(command("start", "startDay", [store().day.offers[1].id])).ok).toBe(
		true,
	);
	expect(run(command("resolve", "resolveSpecialRequest", ["r1", "o1"])).ok).toBe(false);
	expect(run(command("close", "closeDay", [])).ok).toBe(true);
	expect(createSimulatorSnapshot(store(), "day", revision).day.grade).not.toBe(
		"",
	);
	expect(run(command("claim", "claimDayResult", [])).ok).toBe(true);
	expect(store().day.dayNumber).toBe(2);
	unsubscribe();
});

test("payday's ATM queue is made of real customers: they reach Unity tagged with the event and pay like anyone", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	expect(store().devActivateGameEvent("quinto-dia-util")).toBe(true);
	const origins = [];
	for (let index = 0; index < 24; index++) {
		useGameStore.setState({ market: { ...store().market, nextCustomerAt: 1 } });
		if (!store().processNextCustomer()) continue;
		const latest = store().market.recentCustomers[0];
		origins.push(latest.origin ?? null);
		// the snapshot carries the tag to Unity with the customer's real basket
		const sent = createSimulatorSnapshot(store(), "day", index + 1).customers[0];
		expect(sent.id).toBe(latest.id);
		expect(sent.origin).toBe(latest.origin);
	}
	expect(origins.length).toBeGreaterThan(0);
	expect(origins.every((origin) => origin === null || origin === "quinto-dia-util")).toBe(true);
	expect(origins.some((origin) => origin === "quinto-dia-util")).toBe(true);
});

// ---------------------------------------------------------------- checkout counter

function customerWithBasket() {
	store().startDay(FREE_DAY_CONTRACT_ID);
	for (let tries = 0; tries < 30 && store().checkout.queue.length === 0; tries++) {
		useGameStore.setState({ market: { ...store().market, nextCustomerAt: 1 } });
		store().processNextCustomer();
	}
	expect(store().checkout.queue.length).toBeGreaterThan(0);
	return store().checkout.queue[0];
}

test("a customer's money only arrives when the purchase is rung up", () => {
	const coins = store().coins;
	const checkout = customerWithBasket();
	expect(store().coins).toBe(coins);
	const revenue = store().market.totalRevenue;
	expect(store().completeCheckout(checkout.id, checkout.total)).toBe(true);
	expect(store().coins).toBeGreaterThanOrEqual(coins + checkout.total);
	expect(store().market.totalRevenue).toBe(revenue + checkout.total);
	expect(store().day.stats.revenue).toBeGreaterThanOrEqual(checkout.total);
	const record = store().market.recentCustomers.find((c) => c.id === checkout.customerId);
	expect(record?.status ?? "pagou").toBe("pagou");
});

test("customers left waiting put their items back and leave", () => {
	const checkout = customerWithBasket();
	const stock = { ...store().shelfStock };
	useGameStore.setState({
		checkout: { ...store().checkout, queue: store().checkout.queue.map((c) => ({ ...c, expiresAt: 1 })) },
	});
	const satisfaction = store().market.customerSatisfaction;
	expect(store().processCheckoutCounter()).toBe(true);
	expect(store().checkout.queue).toEqual([]);
	expect(store().day.stats.checkoutsLost).toBeGreaterThan(0);
	expect(store().market.customerSatisfaction).toBeLessThan(satisfaction);
	const item = checkout.items[0];
	expect(store().shelfStock[item.shelfId]).toBeGreaterThanOrEqual((stock[item.shelfId] ?? 0) + item.quantity);
});

test("closing the day rings up everyone still in line", () => {
	const checkout = customerWithBasket();
	const coins = store().coins;
	expect(store().closeDay()).toBe(true);
	expect(store().checkout.queue).toEqual([]);
	expect(store().coins).toBe(coins + checkout.total);
	expect(store().day.result.stats.revenue).toBeGreaterThanOrEqual(checkout.total);
});

test("Unity rings up a basket through the command protocol", () => {
	const checkout = customerWithBasket();
	let revision = 1;
	const unsubscribe = useGameStore.subscribe(() => revision++);
	const run = createSimulatorCommandHandler("caixa", () => store(), () => revision);
	const snapshot = createSimulatorSnapshot(store(), "caixa", revision);
	expect(snapshot.checkouts[0].id).toBe(checkout.id);
	expect(snapshot.checkouts[0].items.length).toBeGreaterThan(0);
	expect(run({ protocol: 1, session: "caixa", id: "pay", revision, action: "completeCheckout", args: [checkout.id, checkout.total] }).ok).toBe(true);
	expect(createSimulatorSnapshot(store(), "caixa", revision).checkoutResults[0].id).toBe(checkout.id);
	unsubscribe();
});

// ---------------------------------------------------------------- store mishaps

const { createStoreIncident } = await import("./store-incidents.ts");
const { getIncidentShelves } = await import("./store-incidents-context.ts");

function withIncident(kind) {
	const state = store();
	const shelves = getIncidentShelves(state).map((shelf) => ({ ...shelf, category: kind === "geladeira_bebidas" ? "bebidas" : kind === "freezer_sorvete" ? "congelados" : shelf.category }));
	const incident = createStoreIncident(state.incidents, shelves, Date.now(), state.market.level, kind);
	expect(incident).not.toBeNull();
	useGameStore.setState({ incidents: { ...state.incidents, active: [incident] } });
	return incident;
}

test("a mishap fixed by the player is counted in the day", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	const incident = withIncident("derramado");
	expect(store().fixIncident(incident.id)).toBe(true);
	expect(store().incidents.active).toEqual([]);
	expect(store().day.stats.incidentsFixed).toBe(1);
	expect(store().fixIncident(incident.id)).toBe(false);
});

test("the cooler repair costs coins and blocks its shelf until fixed", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	const incident = withIncident("freezer_sorvete");
	expect(incident.fixCost).toBeGreaterThan(0);
	useGameStore.setState({ coins: incident.fixCost - 1 });
	expect(store().fixIncident(incident.id)).toBe(false);
	useGameStore.setState({ coins: incident.fixCost + 10 });
	expect(store().fixIncident(incident.id)).toBe(true);
	expect(store().coins).toBe(10);
});

test("Unity sees mishaps in the snapshot and fixes them by command", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	const incident = withIncident("etiqueta");
	let revision = 1;
	const unsubscribe = useGameStore.subscribe(() => revision++);
	const run = createSimulatorCommandHandler("imprevisto", () => store(), () => revision);
	const view = createSimulatorSnapshot(store(), "imprevisto", revision);
	expect(view.incidents[0].id).toBe(incident.id);
	expect(view.incidents[0].price).toBeGreaterThan(view.incidents[0].tagPrice);
	expect(run({ protocol: 1, session: "imprevisto", id: "fix", revision, action: "fixIncident", args: [incident.id] }).ok).toBe(true);
	unsubscribe();
});

// ---------------------------------------------------------------- deliveries at the dock

test("a delivered supplier order waits at the dock until it is unloaded", () => {
	const state = store();
	const productId = state.market.unlockedProductIds[0];
	const before = state.inventory[productId] ?? 0;
	const past = Date.now() - 60_000;
	useGameStore.setState({
		inventoryCapacityLevels: { ...state.inventoryCapacityLevels, [productId]: 4 },
		logistics: {
			...state.logistics,
			orders: [
				{ createdAt: past, deliveredAt: null, deliveryDurationMs: 1_000, id: "pedido-teste", productId, quantity: 7, status: "em-transporte", totalCost: 10 },
			],
		},
	});
	store().processSupplierOrders();
	expect(store().inventory[productId] ?? 0).toBe(before);
	const delivery = store().receiving.dock.find((item) => item.orderId === "pedido-teste");
	expect(delivery.quantity).toBe(7);
	let revision = 1;
	const unsubscribe = useGameStore.subscribe(() => revision++);
	const run = createSimulatorCommandHandler("doca", () => store(), () => revision);
	const view = createSimulatorSnapshot(store(), "doca", revision);
	expect(view.dock[0].boxUnits).toBe(1);
	// An order from before supplier boxes: its units are split as before and need units of room.
	const product = itemCatalog.find((item) => item.id === productId);
	expect(view.dock[0].room).toBe(getInventoryCapacity(product, 4) - before);
	expect(run({ protocol: 1, session: "doca", id: "box", revision, action: "unloadDelivery", args: [delivery.id, 1] }).ok).toBe(true);
	expect(store().inventory[productId]).toBe(before + 1);
	expect(store().unloadAllDeliveries()).toBe(true);
	expect(store().inventory[productId]).toBe(before + 7);
	expect(store().receiving.dock).toEqual([]);
	unsubscribe();
});

test("orders are supplier boxes: paid per box, unloaded box by box, shelved unit by unit", () => {
	const state = store();
	const productId = state.market.unlockedProductIds[0];
	const product = itemCatalog.find((item) => item.id === productId);
	useGameStore.setState({ coins: 10_000, inventory: { ...state.inventory, [productId]: 0 }, inventoryCapacityLevels: { ...state.inventoryCapacityLevels, [productId]: 1 } });
	expect(store().placeSupplierOrder({ productId, boxes: 2 })).toBe(true);
	const order = store().logistics.orders[0];
	expect(order.boxes).toBe(2);
	expect(order.quantity).toBe(2 * product.caseSize);
	// Old callers ask for units: they get the boxes that hold them.
	expect(store().placeSupplierOrder({ productId, quantity: 1 })).toBe(true);
	expect(store().logistics.orders[0].quantity).toBe(product.caseSize);
	// 3 boxes ordered, the stockroom holds 3 at this level: a fourth does not fit.
	expect(store().placeSupplierOrder({ productId, boxes: 1 })).toBe(false);
	useGameStore.setState({ logistics: { ...store().logistics, orders: store().logistics.orders.map((item) => ({ ...item, createdAt: Date.now() - 10 * 60 * 60_000 })) } });
	store().processSupplierOrders();
	const dock = createSimulatorSnapshot(store(), "caixas", 1).dock.find((item) => item.productId === productId && item.quantity === 2 * product.caseSize);
	expect(dock.boxUnits).toBe(product.caseSize);
	expect(dock.boxes).toBe(2);
	expect(store().unloadDelivery(dock.id, product.caseSize)).toBe(true);
	expect(store().inventory[productId]).toBe(product.caseSize);
	const view = createSimulatorSnapshot(store(), "caixas", 2);
	expect(view.stockroom.find((item) => item.productId === productId).boxes).toBe(1);
});

test("a v45 save with special requests migrates to v46 keeping the progress (Lucas 29/10)", async () => {
	const old = JSON.parse(initial);
	old.coins = 4321;
	old.market = { ...old.market, level: 7 };
	old.day = {
		...old.day,
		dayNumber: 12,
		loyalty: 63,
		requests: [{ id: "r1", customerId: "c-1", customerName: "Ana", status: "served", expiresAt: 1, tip: 3 }],
		stats: { ...old.day.stats, customers: 5, requestsServed: 2, requestsExpired: 1, loyaltyChange: 5, reputationChange: 2, tips: 3 },
	};
	expect(useGameStore.persist.getOptions().version).toBe(47); // 47: market colours (src/data/market-paint.ts)
	const next = await useGameStore.persist.getOptions().migrate(old, 45);
	expect(next.coins).toBe(4321);
	expect(next.market.level).toBe(7);
	expect(next.day.dayNumber).toBe(12);
	expect(next.day.loyalty).toBe(63);
	expect(next.day.requests).toBeUndefined();
	expect(next.day.stats.customers).toBe(5);
	expect(Object.keys(next.day.stats).filter((key) => /request|loyalty|reputation|tips/i.test(key))).toEqual([]);
});
