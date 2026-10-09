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
const { createSimulatorCommandHandler } = await import("./simulator-protocol.ts");
const { getSupplierCartQuote, getOrderLines } = await import("./supplier-cart.ts");
const { getCaseSize } = await import("../data/case-sizes.ts");
const { itemCatalog, itemCategories } = await import("../data/market-products.ts");
const { getMaxBoxesPerOrder } = await import("../data/supplier-capacity.ts");
const { getInventoryBoxCapacity } = await import("../data/inventory-capacity.ts");
// Test files share the store module: leave it as we found it.
useGameStore.setState({ interior: { items: [], owned: {} } });
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));

const store = () => useGameStore.getState();
const product = (id) => itemCatalog.find((item) => item.id === id);
const supplierIds = () =>
	store()
		.market.unlockedProductIds.filter((id) => product(id)?.acquisition === "supplier");
const hours = 60 * 60_000;

// Two supplier products that are unlocked, with an empty stockroom that holds 12 boxes each and plenty of coins.
function roomy(ids = supplierIds().slice(0, 2)) {
	const state = store();
	const inventory = { ...state.inventory };
	const levels = { ...state.inventoryCapacityLevels };
	for (const id of ids) {
		inventory[id] = 0;
		levels[id] = 4;
	}
	useGameStore.setState({ coins: 1_000_000, inventory, inventoryCapacityLevels: levels });
	return ids;
}

function truckOnRoad(productId, id) {
	return {
		createdAt: Date.now(),
		deliveredAt: null,
		deliveryDurationMs: 10 * hours,
		id,
		productId,
		quantity: getCaseSize(product(productId)),
		status: "em-transporte",
		totalCost: 1,
	};
}

test("a cart of two products is one truck: one order with two lines, the sum charged, one slot", () => {
	const [a, b] = roomy();
	expect(b).toBeDefined();
	const before = store();
	const input = { lines: [{ productId: a, boxes: 2 }, { productId: b, boxes: 1 }] };
	const quote = getSupplierCartQuote(before, input);
	expect(quote.reason).toBe(null);

	expect(store().placeSupplierCart(input)).toBe(true);
	const after = store();
	expect(after.logistics.orders.length).toBe(before.logistics.orders.length + 1);
	const order = after.logistics.orders[0];
	const lines = getOrderLines(order);
	expect(lines.map((line) => [line.productId, line.boxes])).toEqual([
		[a, 2],
		[b, 1],
	]);
	expect(order.boxes).toBe(3);
	expect(order.quantity).toBe(2 * getCaseSize(product(a)) + getCaseSize(product(b)));
	// The player pays the sum of the lines, and the truck takes one of the supplier slots.
	const lineCosts = lines.reduce((total, line) => total + line.cost, 0);
	expect(order.totalCost).toBe(lineCosts);
	expect(quote.total).toBe(lineCosts);
	expect(after.coins).toBe(before.coins - lineCosts);
	expect(after.statistics.supplierOrdersPlaced).toBe(before.statistics.supplierOrdersPlaced + 1);
	expect(after.logistics.orders.filter((item) => item.status !== "entregue").length).toBe(1);
});

test("the same product twice in a cart is merged into one line", () => {
	const [a] = roomy();
	expect(store().placeSupplierCart({ lines: [{ productId: a, boxes: 2 }, { productId: a, boxes: 3 }] })).toBe(true);
	const lines = getOrderLines(store().logistics.orders[0]);
	expect(lines.length).toBe(1);
	expect(lines[0].boxes).toBe(5);
});

test("a cart over the truck cap fails, and a truck full to the cap is fine", () => {
	const [a, b] = roomy();
	const cap = getMaxBoxesPerOrder(store().logistics.supplierOrderSlots);
	expect(cap).toBe(10);
	const coins = store().coins;
	expect(store().placeSupplierCart({ lines: [{ productId: a, boxes: 6 }, { productId: b, boxes: 5 }] })).toBe(false);
	expect(store().logistics.orders).toEqual([]);
	expect(store().coins).toBe(coins);
	expect(store().placeSupplierCart({ lines: [{ productId: a, boxes: 6 }, { productId: b, boxes: 4 }] })).toBe(true);
	expect(store().logistics.orders[0].boxes).toBe(10);
});

test("a cart fails when every supplier slot is on the road", () => {
	const [a, b] = roomy();
	const slots = store().logistics.supplierOrderSlots;
	const orders = Array.from({ length: slots }, (_, index) => truckOnRoad(a, `caminhao-${index}`));
	useGameStore.setState({ logistics: { ...store().logistics, orders } });
	const before = store();
	expect(store().placeSupplierCart({ lines: [{ productId: a, boxes: 1 }, { productId: b, boxes: 1 }] })).toBe(false);
	expect(store().logistics.orders.length).toBe(slots);
	expect(store().coins).toBe(before.coins);
	// A truck that has arrived frees its slot.
	useGameStore.setState({
		logistics: { ...store().logistics, orders: orders.map((order) => ({ ...order, createdAt: Date.now() - 20 * hours })) },
	});
	expect(store().placeSupplierCart({ lines: [{ productId: a, boxes: 1 }, { productId: b, boxes: 1 }] })).toBe(true);
});

test("a cart fails when one line does not fit the stockroom", () => {
	const [a, b] = roomy();
	// The stockroom holds 2 boxes of this product at level 0: 3 boxes do not fit, and the whole cart waits.
	useGameStore.setState({ inventoryCapacityLevels: { ...store().inventoryCapacityLevels, [b]: 0 } });
	const orders = store().logistics.orders;
	expect(store().placeSupplierCart({ lines: [{ productId: a, boxes: 1 }, { productId: b, boxes: 3 }] })).toBe(false);
	expect(store().logistics.orders).toBe(orders);
	expect(store().placeSupplierCart({ lines: [{ productId: a, boxes: 1 }, { productId: b, boxes: 2 }] })).toBe(true);
});

test("a cart fails for products that are not supplier products or not unlocked", () => {
	roomy();
	const crafted = itemCatalog.find((item) => item.acquisition === "production");
	const locked = itemCatalog.find((item) => item.acquisition === "supplier" && !store().market.unlockedProductIds.includes(item.id));
	expect(store().placeSupplierCart({ lines: [{ productId: crafted.id, boxes: 1 }] })).toBe(false);
	if (locked) expect(store().placeSupplierCart({ lines: [{ productId: locked.id, boxes: 1 }] })).toBe(false);
	expect(store().placeSupplierCart({ lines: [] })).toBe(false);
});

test("the freight coupon takes 10% off the whole truck and uses one coupon", () => {
	const [a, b] = roomy();
	useGameStore.setState({ logistics: { ...store().logistics, freightCoupons: 1 } });
	const before = store();
	const input = { lines: [{ productId: a, boxes: 1 }, { productId: b, boxes: 1 }], useFreightCoupon: true };
	const subtotal = getSupplierCartQuote(before, { lines: input.lines }).total;
	expect(store().placeSupplierCart(input)).toBe(true);
	expect(store().logistics.orders[0].totalCost).toBe(Math.ceil(subtotal * 0.9));
	expect(store().logistics.freightCoupons).toBe(0);
});

test("a delivered truck makes one dock delivery per line, all with its order id", () => {
	const [a, b] = roomy();
	expect(store().placeSupplierCart({ lines: [{ productId: a, boxes: 2 }, { productId: b, boxes: 1 }] })).toBe(true);
	const order = store().logistics.orders[0];
	useGameStore.setState({
		logistics: { ...store().logistics, orders: [{ ...order, createdAt: Date.now() - 20 * hours }] },
	});
	expect(store().processSupplierOrders()).toBe(true);
	const deliveries = store().receiving.dock.filter((item) => item.orderId === order.id);
	expect(deliveries.map((item) => item.id).sort()).toEqual([`${order.id}:${a}`, `${order.id}:${b}`].sort());
	const quantities = Object.fromEntries(deliveries.map((item) => [item.productId, item.quantity]));
	expect(quantities[a]).toBe(2 * getCaseSize(product(a)));
	expect(quantities[b]).toBe(getCaseSize(product(b)));
	// A second pass does not add the same trucks again.
	store().processSupplierOrders();
	expect(store().receiving.dock.filter((item) => item.orderId === order.id).length).toBe(2);
});

test("orderLowStock places one truck with every low product, up to the truck cap", () => {
	const low = supplierIds();
	const inventory = { ...store().inventory };
	const levels = { ...store().inventoryCapacityLevels };
	for (const id of low) {
		inventory[id] = 0;
		levels[id] = 0;
	}
	useGameStore.setState({ coins: 1_000_000, inventory, inventoryCapacityLevels: levels });
	const before = store().logistics.orders.length;
	expect(store().orderLowStock()).toBe(true);
	expect(store().logistics.orders.length).toBe(before + 1);
	const order = store().logistics.orders[0];
	// Every low product gets its 2 boxes (the stockroom room at level 0) until the truck holds 10.
	expect(order.boxes).toBe(Math.min(getMaxBoxesPerOrder(store().logistics.supplierOrderSlots), 2 * low.length));
	expect(getOrderLines(order).length).toBeGreaterThan(1);
	expect(getOrderLines(order).every((line) => line.boxes === 2)).toBe(true);
});

test("the snapshot lists the supplier catalog and the truck limits", () => {
	roomy();
	const now = Date.now();
	const view = createSimulatorSnapshot(store(), "catalogo", 1, now);
	const { supplierCatalog, supplierInfo } = view;
	expect(supplierInfo).toEqual({
		slots: store().logistics.supplierOrderSlots,
		active: 0,
		maxBoxes: 10,
		freightCoupons: store().logistics.freightCoupons,
	});
	expect(supplierCatalog.length).toBeGreaterThan(0);
	// Unlocked products come first.
	const firstLocked = supplierCatalog.findIndex((item) => item.locked);
	const lastUnlocked = supplierCatalog.map((item) => item.locked).lastIndexOf(false);
	expect(firstLocked === -1 || lastUnlocked < firstLocked).toBe(true);
	const tomato = supplierCatalog.find((item) => item.productId === 1);
	expect(tomato).toBeDefined();
	expect(tomato.name).toBe("Tomate");
	expect(tomato.categoryLabel).toBe(itemCategories.find((category) => category.id === "hortifruti").label);
	expect(tomato.caseSize).toBe(getCaseSize(product(1)));
	expect(tomato.boxPrice).toBeGreaterThan(0);
	expect(tomato.unitCost).toBeCloseTo(tomato.boxPrice / tomato.caseSize, 1);
	expect(tomato.capacityBoxes).toBe(getInventoryBoxCapacity(store().inventoryCapacityLevels[1] ?? 0));
	expect(tomato.freeBoxes).toBeLessThanOrEqual(tomato.capacityBoxes);
	expect(tomato.incomingBoxes).toBe(0);
	expect(tomato.deliverySeconds).toBeGreaterThan(0);
	for (const item of supplierCatalog) {
		expect(item.salePrice).toBeGreaterThan(0);
		expect(item.stockUnits).toBeGreaterThanOrEqual(0);
		expect(item.deliverySeconds).toBeGreaterThan(0);
	}
});

test("the snapshot shows every line of a truck and the order id of its dock deliveries", () => {
	const [a, b] = roomy();
	store().placeSupplierCart({ lines: [{ productId: a, boxes: 2 }, { productId: b, boxes: 1 }] });
	const view = createSimulatorSnapshot(store(), "carrinho", 1);
	const order = view.orders[0];
	expect(order.boxes).toBe(3);
	expect(order.lines.map((line) => [line.productId, line.boxes])).toEqual([
		[a, 2],
		[b, 1],
	]);
	expect(order.lines[0].productName).toBe(product(a).name);
	// An order saved before carts has no lines: it shows as one line of its product.
	const legacyOrder = {
		id: "antigo",
		productId: a,
		quantity: 5,
		createdAt: Date.now(),
		deliveryDurationMs: hours,
		deliveredAt: null,
		status: "em-transporte",
		totalCost: 1,
	};
	useGameStore.setState({ logistics: { ...store().logistics, orders: [legacyOrder] } });
	const old = createSimulatorSnapshot(store(), "carrinho", 2).orders[0];
	const legacyBoxes = Math.ceil(5 / getCaseSize(product(a)));
	expect(old.lines).toEqual([{ productId: a, productName: product(a).name, boxes: legacyBoxes }]);
	expect(old.boxes).toBe(legacyBoxes);
	expect(view.dock.every((item) => typeof item.orderId === "string")).toBe(true);
});

test("the simulator places a cart as one command", () => {
	const [a, b] = roomy();
	let revision = 1;
	const unsubscribe = useGameStore.subscribe(() => revision++);
	const run = createSimulatorCommandHandler("carrinho", () => store(), () => revision);
	const placed = run({
		protocol: 1,
		session: "carrinho",
		id: "cart-1",
		revision,
		action: "placeSupplierCart",
		args: [{ lines: [{ productId: a, boxes: 1 }, { productId: b, boxes: 2 }] }],
	});
	expect(placed.ok).toBe(true);
	expect(store().logistics.orders.length).toBe(1);
	const invalid = run({
		protocol: 1,
		session: "carrinho",
		id: "cart-2",
		revision,
		action: "placeSupplierCart",
		args: [{ lines: [] }],
	});
	expect(invalid.ok).toBe(false);
	expect(invalid.reason).toBe("invalid-action");
	unsubscribe();
});

test("Chegar já parks a whole cart truck at the dock, one delivery per product, for a ticket", () => {
	const [a, b] = roomy();
	useGameStore.setState({ logistics: { ...store().logistics, emergencyTokens: 1 } });
	expect(store().placeSupplierCart({ lines: [{ productId: a, boxes: 1 }, { productId: b, boxes: 1 }] })).toBe(true);
	const order = store().logistics.orders[0];
	const stockBefore = { a: store().inventory[a] ?? 0, b: store().inventory[b] ?? 0 };
	expect(store().deliverOrderInstantly(order.id)).toBe(true);
	const dock = store().receiving.dock.filter((delivery) => delivery.orderId === order.id);
	expect(dock.map((delivery) => delivery.productId).sort()).toEqual([a, b].sort());
	expect(store().logistics.emergencyTokens).toBe(0);
	expect(store().logistics.orders.find((item) => item.id === order.id).status).toBe("entregue");
	// The goods wait at the dock: nothing jumps into the stockroom before it is unloaded.
	expect(store().inventory[a] ?? 0).toBe(stockBefore.a);
	expect(store().inventory[b] ?? 0).toBe(stockBefore.b);
	for (const delivery of dock) expect(store().unloadDelivery(delivery.id, delivery.quantity)).toBe(true);
	expect(store().inventory[a]).toBe(stockBefore.a + getCaseSize(product(a)));
	expect(store().inventory[b]).toBe(stockBefore.b + getCaseSize(product(b)));
});
