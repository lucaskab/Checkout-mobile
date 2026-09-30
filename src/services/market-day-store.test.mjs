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
const { createSpecialRequest, addSpecialRequest, FREE_DAY_CONTRACT_ID } =
	await import("./market-day.ts");
const { getDayStoreContext } = await import("./market-day-context.ts");
// These tests run a shop that is already furnished (the starter pieces are placed).
useGameStore.setState({ interior: { items: [], owned: {} } });
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
// Test files share the store module: leave it as we found it.
afterAll(() => useGameStore.setState(JSON.parse(initial)));

const store = () => useGameStore.getState();
const customer = (seed, mood = "calmo") => ({
	archetype: "normal",
	customerId: `cliente-${seed}`,
	customerName: "Ana",
	mood,
	seed,
});
function withRequest(kind, seed = 5, patch = {}) {
	const state = store();
	const request = createSpecialRequest(
		state.day,
		customer(seed),
		getDayStoreContext(state),
		Date.now(),
		{ kind },
	);
	expect(request).not.toBeNull();
	const next = { ...request, ...patch };
	useGameStore.setState({ day: addSpecialRequest(state.day, next) });
	return next;
}

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

test("customers are counted in the day and may bring special requests", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	for (let index = 0; index < 12; index++) {
		useGameStore.setState({ market: { ...store().market, nextCustomerAt: 1 } });
		expect(store().processNextCustomer()).toBe(true);
	}
	expect(store().day.stats.customers).toBe(12);
	expect(store().day.stats.satisfactionSamples).toBe(12);
});

test("helping a customer in time pays a tip and raises satisfaction", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	const request = withRequest("ajuda");
	const before = store();
	const best = request.options.find((option) => option.quality === "best");
	expect(store().resolveSpecialRequest(request.id, best.id)).toBe(true);
	expect(store().coins).toBeGreaterThan(before.coins);
	expect(store().market.customerSatisfaction).toBeGreaterThan(
		before.market.customerSatisfaction,
	);
	expect(store().day.stats.requestsServed).toBe(1);
	expect(store().resolveSpecialRequest(request.id, best.id)).toBe(false);
});

test("a product fetched from storage is sold from the stock room", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	const state = store();
	const context = getDayStoreContext(state);
	const missing = context.unlockedProductIds.find(
		(id) => !context.shelfProductIds.includes(id),
	);
	useGameStore.setState({ inventory: { ...state.inventory, [missing]: 3 } });
	const request = withRequest("produto", 9);
	const stock = request.options.find((option) => option.source === "stock");
	expect(stock).toBeDefined();
	const coins = store().coins;
	expect(store().resolveSpecialRequest(request.id, stock.id)).toBe(true);
	expect(store().inventory[stock.productId]).toBe(2);
	expect(store().coins).toBeGreaterThan(coins);
	expect(store().day.stats.revenue).toBeGreaterThan(0);
});

test("ignored customers leave and the store loses satisfaction", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	withRequest("ajuda", 3, { expiresAt: Date.now() - 1 });
	const satisfaction = store().market.customerSatisfaction;
	expect(store().processMarketDay()).toBe(true);
	expect(store().day.stats.requestsExpired).toBe(1);
	expect(store().market.customerSatisfaction).toBeLessThan(satisfaction);
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
	const request = withRequest("ajuda", 12);
	expect(
		run(
			command("resolve", "resolveSpecialRequest", [
				request.id,
				request.options[0].id,
			]),
		).ok,
	).toBe(true);
	expect(run(command("close", "closeDay", [])).ok).toBe(true);
	expect(createSimulatorSnapshot(store(), "day", revision).day.grade).not.toBe(
		"",
	);
	expect(run(command("claim", "claimDayResult", [])).ok).toBe(true);
	expect(store().day.dayNumber).toBe(2);
	unsubscribe();
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
	expect(view.dock[0].room).toBe(75 - before);
	expect(run({ protocol: 1, session: "doca", id: "box", revision, action: "unloadDelivery", args: [delivery.id, 1] }).ok).toBe(true);
	expect(store().inventory[productId]).toBe(before + 1);
	expect(store().unloadAllDeliveries()).toBe(true);
	expect(store().inventory[productId]).toBe(before + 7);
	expect(store().receiving.dock).toEqual([]);
	unsubscribe();
});
