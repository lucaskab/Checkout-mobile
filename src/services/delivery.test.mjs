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
const { createSimulatorCommandHandler, simulatorActions } = await import("./simulator-protocol.ts");
const delivery = await import("./delivery.ts");
const { itemCatalog } = await import("../data/market-products.ts");
const { marketEras } = await import("../data/economy.ts");
const { shelfProductSlots } = await import("../data/shelf-slots.ts");

// Test files share the store module: leave it as we found it.
useGameStore.setState({ interior: { items: [], owned: {} } });
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));

const store = () => useGameStore.getState();
const T0 = 1_900_000_000_000;
const find = (id) => store().delivery.orders.find((order) => order.id === id);
const unlockedIds = () => store().market.unlockedProductIds;

// The Delivery app is open: minimercado era, market open, a stockroom with plenty of every product.
function openApp({ open = true, eraId = "minimercado", units = 10 } = {}) {
	const state = store();
	const inventory = Object.fromEntries(unlockedIds().map((id) => [id, units]));
	useGameStore.setState({
		era: { ...state.era, id: eraId },
		market: { ...state.market, isOpen: open },
		inventory: { ...state.inventory, ...inventory },
	});
}
function stockUp(units = 10) {
	const inventory = Object.fromEntries(unlockedIds().map((id) => [id, units]));
	useGameStore.setState({ inventory: { ...store().inventory, ...inventory } });
}
// The shelf price of what an order holds (the shop's rule: the shelf price, else the base price).
function priceOf(productId) {
	const product = itemCatalog.find((item) => item.id === productId);
	const slot = shelfProductSlots.find((item) => store().shelfAssignments[item.id] === productId);
	return (slot ? store().shelfPrices[slot.id] : undefined) ?? product.sellingPrice;
}
const fullPack = (order) => order.items.map((item) => ({ productId: item.productId, quantity: item.quantity }));

// An order from spawn to the door of the store: accepted, packed in full (5 stars), handed over on time.
function perfectDelivery(now) {
	stockUp();
	expect(store().devSpawnDeliveryOffer(now)).toBe(true);
	const offer = store().delivery.orders.at(-1);
	expect(store().acceptDeliveryOrder(offer.id, now)).toBe(true);
	expect(store().packDeliveryOrder(offer.id, { items: fullPack(offer), quality: 1, seconds: 30 }, now + 1_000)).toBe(true);
	const { arriveAt } = find(offer.id).courier;
	store().processDelivery(arriveAt);
	expect(find(offer.id).status).toBe("moto-na-porta");
	expect(store().handOverDelivery(offer.id, arriveAt + 2_000)).toBe(true);
	const { deliverAt } = find(offer.id).courier;
	store().processDelivery(deliverAt);
	return find(offer.id);
}

test("locked before the minimercado: no offers, no accepting, the app is shown as locked", () => {
	openApp({ eraId: "conteiner" });
	expect(store().processDelivery(T0)).toBe(false);
	store().processDelivery(T0 + 10 * 60_000);
	expect(store().delivery.orders).toEqual([]);
	expect(store().devSpawnDeliveryOffer(T0)).toBe(false);
	const snapshot = createSimulatorSnapshot(store(), "locked", 1, T0);
	expect(snapshot.delivery.unlocked).toBe(false);
	expect(snapshot.delivery.unlockEraName).toBe(marketEras.find((era) => era.id === "minimercado").name);
	expect(delivery.isDeliveryUnlocked("conteiner")).toBe(false);
	expect(delivery.isDeliveryUnlocked("minimercado")).toBe(true);
	expect(delivery.isDeliveryUnlocked("rede")).toBe(true);
});

test("offers come in waves only while the market is open", () => {
	openApp({ open: false });
	expect(store().processDelivery(T0)).toBe(false);
	expect(store().delivery.nextOfferAt).toBe(null);

	useGameStore.setState({ market: { ...store().market, isOpen: true } });
	expect(store().processDelivery(T0)).toBe(true);
	const due = store().delivery.nextOfferAt;
	expect(due).toBeGreaterThanOrEqual(T0 + delivery.OFFER_INTERVAL_MS.min);
	expect(due).toBeLessThanOrEqual(T0 + delivery.OFFER_INTERVAL_MS.max);

	store().processDelivery(due - 1);
	expect(store().delivery.orders.length).toBe(0);
	store().processDelivery(due);
	expect(store().delivery.orders.filter((order) => order.status === "oferta").length).toBe(1);

	// Closing the market stops the waves: the offer expires and nothing new comes.
	useGameStore.setState({ market: { ...store().market, isOpen: false } });
	store().processDelivery(due + 200_000);
	expect(store().delivery.orders.map((order) => order.status)).toEqual(["expirado"]);
});

test("at most three offers wait at a time", () => {
	openApp();
	for (let i = 0; i < 3; i++) expect(store().devSpawnDeliveryOffer(T0 + i)).toBe(true);
	useGameStore.setState({ delivery: { ...store().delivery, nextOfferAt: T0 } });
	store().processDelivery(T0);
	expect(store().delivery.orders.filter((order) => order.status === "oferta").length).toBe(3);
	expect(store().delivery.nextOfferAt).toBeGreaterThan(T0);
});

test("offer items come only from products with stockroom units, never more than the stock", () => {
	const stock = [
		{ productId: 1, units: 0, price: 3 },
		{ productId: 2, units: 1, price: 4 },
		{ productId: 3, units: 9, price: 5 },
		{ productId: 4, units: 2, price: 6 },
	];
	for (let seed = 1; seed <= 40; seed++) {
		const offer = delivery.createDeliveryOffer({
			id: `o${seed}`,
			now: T0,
			random: delivery.createDeliveryRandom(seed),
			stock,
		});
		expect(offer).not.toBe(null);
		expect(offer.items.length).toBeGreaterThanOrEqual(2);
		expect(offer.items.length).toBeLessThanOrEqual(3);
		for (const item of offer.items) {
			const line = stock.find((entry) => entry.productId === item.productId);
			expect(line.units).toBeGreaterThan(0);
			expect(item.quantity).toBeGreaterThanOrEqual(1);
			expect(item.quantity).toBeLessThanOrEqual(line.units);
		}
		expect(offer.itemsValue).toBe(offer.items.reduce((total, item) => total + item.quantity * stock.find((line) => line.productId === item.productId).price, 0));
	}
	// Stock too thin for two lines: no offer.
	expect(delivery.createDeliveryOffer({ id: "x", now: T0, random: delivery.createDeliveryRandom(3), stock: [stock[1], stock[0]] })).toBe(null);
});

test("the store only offers what is in the stockroom right now", () => {
	openApp({ units: 0 });
	const [a, c] = unlockedIds();
	useGameStore.setState({ inventory: { ...store().inventory, [a]: 3, [c]: 1 } });
	expect(store().devSpawnDeliveryOffer(T0)).toBe(true);
	const offer = store().delivery.orders.at(-1);
	expect(offer.items.map((item) => item.productId).sort()).toEqual([a, c].sort());
	expect(offer.items.find((item) => item.productId === c).quantity).toBe(1);

	useGameStore.setState({ inventory: { ...store().inventory, [a]: 0, [c]: 1 } });
	expect(store().devSpawnDeliveryOffer(T0 + 1)).toBe(false);
});

test("an offer expires 90 s after it appears unless accepted", () => {
	openApp();
	store().devSpawnDeliveryOffer(T0);
	const id = store().delivery.orders[0].id;
	store().processDelivery(T0 + 89_999);
	expect(find(id).status).toBe("oferta");
	store().processDelivery(T0 + 90_000);
	expect(find(id).status).toBe("expirado");
	expect(store().acceptDeliveryOrder(id, T0 + 90_001)).toBe(false);
});

test("accepting respects the slots: two at the minimercado, three from the mercadinho", () => {
	openApp();
	for (let i = 0; i < 3; i++) store().devSpawnDeliveryOffer(T0 + i);
	const [first, second, third] = store().delivery.orders.map((order) => order.id);
	expect(store().acceptDeliveryOrder(first, T0)).toBe(true);
	expect(store().acceptDeliveryOrder(second, T0)).toBe(true);
	expect(store().acceptDeliveryOrder(third, T0)).toBe(false);
	expect(find(third).status).toBe("oferta");
	expect(createSimulatorSnapshot(store(), "slots", 1, T0).delivery.active).toBe(2);

	openApp({ eraId: "mercadinho" });
	expect(store().acceptDeliveryOrder(third, T0)).toBe(true);
	expect(delivery.getDeliverySlots("minimercado")).toBe(2);
	expect(delivery.getDeliverySlots("mercadinho")).toBe(3);
	expect(delivery.getDeliverySlots("supermercado")).toBe(4);
});

test("declining an offer ends it and frees nothing else", () => {
	openApp();
	store().devSpawnDeliveryOffer(T0);
	const id = store().delivery.orders[0].id;
	expect(store().declineDeliveryOrder(id)).toBe(true);
	expect(find(id).status).toBe("recusado");
	expect(store().acceptDeliveryOrder(id, T0 + 1)).toBe(false);
	expect(store().declineDeliveryOrder(id)).toBe(false);
});

test("packing takes the units from the stockroom (clamped) and computes the fill ratio", () => {
	openApp();
	store().devSpawnDeliveryOffer(T0);
	const order = store().delivery.orders[0];
	store().acceptDeliveryOrder(order.id, T0);
	// The stockroom has one unit less than the first line asks for.
	const [first] = order.items;
	const shortBy = Math.max(0, first.quantity - 1);
	useGameStore.setState({ inventory: { ...store().inventory, [first.productId]: shortBy } });
	const before = store().inventory;

	expect(store().packDeliveryOrder(order.id, { items: fullPack(order), quality: 0.5, seconds: 40 }, T0 + 5_000)).toBe(true);
	const packed = find(order.id);
	expect(packed.status).toBe("aguardando-moto");
	expect(packed.packed.find((item) => item.productId === first.productId).quantity).toBe(shortBy);
	expect(store().inventory[first.productId]).toBe(0);
	const others = order.items.slice(1);
	for (const item of others) expect(store().inventory[item.productId]).toBe(before[item.productId] - item.quantity);

	const ordered = order.items.reduce((total, item) => total + item.quantity, 0);
	const taken = packed.packed.reduce((total, item) => total + item.quantity, 0);
	expect(packed.fillRatio).toBeCloseTo(taken / ordered, 10);
	expect(packed.courier.arriveAt).toBeGreaterThanOrEqual(T0 + 5_000 + 15_000);
	expect(packed.courier.arriveAt).toBeLessThanOrEqual(T0 + 5_000 + 35_000);
	expect(packed.stars).toBeGreaterThanOrEqual(1);
	expect(packed.stars).toBeLessThanOrEqual(5);
});

test("a courier at the door waits there: moto-na-porta on arrival, then a-caminho on hand-over", () => {
	openApp();
	store().devSpawnDeliveryOffer(T0 + 300_000);
	const offer = store().delivery.orders.at(-1);
	store().acceptDeliveryOrder(offer.id, T0 + 300_000);
	store().packDeliveryOrder(offer.id, { items: fullPack(offer), quality: 1, seconds: 30 }, T0 + 301_000);
	const { arriveAt } = find(offer.id).courier;
	store().processDelivery(arriveAt - 1);
	expect(find(offer.id).status).toBe("aguardando-moto");
	store().processDelivery(arriveAt);
	expect(find(offer.id).status).toBe("moto-na-porta");
	expect(find(offer.id).courier.doorSince).toBe(arriveAt);

	const handedAt = arriveAt + 5_000;
	expect(store().handOverDelivery(offer.id, handedAt)).toBe(true);
	const moving = find(offer.id);
	expect(moving.status).toBe("a-caminho");
	expect(moving.courier.deliverAt).toBe(handedAt + 40_000 + 25_000 * offer.distanceKm);
	expect(moving.stars).toBe(5);
});

test("a bag nobody hands over leaves with the courier after 60 s, and that costs a star", () => {
	openApp();
	stockUp();
	store().devSpawnDeliveryOffer(T0);
	const offer = store().delivery.orders.at(-1);
	store().acceptDeliveryOrder(offer.id, T0);
	store().packDeliveryOrder(offer.id, { items: fullPack(offer), quality: 1, seconds: 30 }, T0 + 1_000);
	const { arriveAt } = find(offer.id).courier;
	store().processDelivery(arriveAt);
	const doorSince = find(offer.id).courier.doorSince;

	store().processDelivery(doorSince + 59_999);
	expect(find(offer.id).status).toBe("moto-na-porta");
	store().processDelivery(doorSince + 60_000);
	const left = find(offer.id);
	expect(left.status).toBe("a-caminho");
	expect(left.stars).toBe(4);
	expect(left.courier.deliverAt).toBe(doorSince + 60_000 + 40_000 + 25_000 * offer.distanceKm);
});

test("a delivery pays goods x fill + fee + tip, and moves the rating and the streak", () => {
	openApp();
	const coinsBefore = store().coins;
	const order = perfectDelivery(T0);
	const itemsValue = order.items.reduce((total, item) => total + item.quantity * priceOf(item.productId), 0);
	expect(order.itemsValue).toBe(Math.round(itemsValue));
	// Five stars: a 20 % tip and no streak bonus yet.
	expect(order.stars).toBe(5);
	expect(order.tip).toBe(Math.round(order.itemsValue * 0.2));
	expect(order.bonus).toBe(0);
	expect(order.paid).toBe(order.itemsValue + order.fee + order.tip);
	expect(store().coins).toBe(coinsBefore + order.paid);
	expect(find(order.id).status).toBe("entregue");
	expect(store().delivery.delivered).toBe(1);
	expect(store().delivery.streak).toBe(1);
	expect(store().delivery.earnings).toBe(order.paid);
	expect(store().delivery.rating).toBeCloseTo(4.62, 2);

	// The second perfect delivery in a row earns the 10 % streak bonus.
	const coinsMiddle = store().coins;
	const second = perfectDelivery(T0 + 600_000);
	const base = second.itemsValue + second.fee + second.tip;
	expect(second.bonus).toBe(Math.round(base * 0.1));
	expect(store().coins).toBe(coinsMiddle + second.paid);
	expect(second.paid).toBe(base + second.bonus);
	expect(store().delivery.streak).toBe(2);
	expect(store().delivery.bestStreak).toBe(2);
	expect(store().delivery.rating).toBeCloseTo(4.64, 2);
});

test("a late hand-over pays less (4 stars: 5 % tip) and ends the streak", () => {
	openApp();
	stockUp();
	store().devSpawnDeliveryOffer(T0);
	const offer = store().delivery.orders.at(-1);
	store().acceptDeliveryOrder(offer.id, T0);
	store().packDeliveryOrder(offer.id, { items: fullPack(offer), quality: 1, seconds: 30 }, T0 + 1_000);
	useGameStore.setState({ delivery: { ...store().delivery, streak: 4, bestStreak: 4 } });
	const { arriveAt } = find(offer.id).courier;
	store().processDelivery(arriveAt);
	const doorSince = find(offer.id).courier.doorSince;
	store().processDelivery(doorSince + 60_000);
	const { deliverAt } = find(offer.id).courier;
	const coinsBefore = store().coins;
	store().processDelivery(deliverAt);
	const paid = find(offer.id);
	expect(paid.status).toBe("entregue");
	expect(paid.stars).toBe(4);
	expect(paid.tip).toBe(Math.round(paid.itemsValue * 0.05));
	expect(paid.bonus).toBe(0);
	expect(store().coins).toBe(coinsBefore + paid.paid);
	expect(store().delivery.streak).toBe(0);
	expect(store().delivery.bestStreak).toBe(4);
});

test("a bag packed after its 4 minutes is cancelled: rating -0.3 and the streak resets", () => {
	openApp();
	stockUp();
	store().devSpawnDeliveryOffer(T0);
	const offer = store().delivery.orders.at(-1);
	store().acceptDeliveryOrder(offer.id, T0);
	useGameStore.setState({ delivery: { ...store().delivery, streak: 3 } });
	const packBy = find(offer.id).packBy;
	expect(packBy).toBe(T0 + 4 * 60_000);

	const packed = store().packDeliveryOrder(offer.id, { items: fullPack(offer), quality: 1, seconds: 30 }, packBy);
	expect(packed).toBe(false);
	expect(find(offer.id).status).toBe("cancelado");
	expect(store().delivery.rating).toBeCloseTo(4.3, 2);
	expect(store().delivery.streak).toBe(0);
	expect(store().delivery.delivered).toBe(0);
});

test("the tick cancels an accepted order that is not packed in time", () => {
	openApp();
	stockUp();
	store().devSpawnDeliveryOffer(T0);
	const offer = store().delivery.orders.at(-1);
	store().acceptDeliveryOrder(offer.id, T0);
	store().processDelivery(T0 + 4 * 60_000 - 1);
	expect(find(offer.id).status).toBe("aceito");
	store().processDelivery(T0 + 4 * 60_000);
	expect(find(offer.id).status).toBe("cancelado");
	expect(store().delivery.rating).toBeCloseTo(4.3, 2);
});

test("a save from before the delivery app loads with no orders and snapshots fine", async () => {
	const old = JSON.parse(JSON.stringify(store()));
	delete old.delivery;
	for (const key of Object.keys(old)) if (typeof old[key] === "function") delete old[key];
	memory.set("checkout.game", JSON.stringify({ state: old, version: 43 }));
	await useGameStore.persist.rehydrate();
	const state = store();
	expect(state.delivery.orders).toEqual([]);
	expect(state.delivery.rating).toBe(4.6);
	expect(state.delivery.nextOfferAt).toBe(null);
	expect(createSimulatorSnapshot(state, "old", 1, T0).delivery.orders).toEqual([]);
	expect(() => store().processDelivery(T0)).not.toThrow();
});

test("the snapshot carries the delivery block with each order flattened for Unity", () => {
	openApp();
	store().devSpawnDeliveryOffer(T0);
	const snapshot = createSimulatorSnapshot(store(), "snap", 1, T0);
	expect(Object.keys(snapshot.delivery).sort()).toEqual(
		["active", "bestStreak", "delivered", "orders", "rating", "slots", "streak", "unlockEraName", "unlocked"].sort(),
	);
	expect(snapshot.delivery.unlocked).toBe(true);
	expect(snapshot.delivery.slots).toBe(2);
	expect(snapshot.delivery.active).toBe(0);
	const [order] = snapshot.delivery.orders;
	expect(order.status).toBe("oferta");
	expect(order.customerName).toMatch(/^\S+ [A-Z]\.$/);
	expect(order.expiresAt).toBe(T0 + 90_000);
	expect(order.packBy).toBe(0);
	expect(order.courier).toBe(null);
	expect(order.items.length).toBeGreaterThanOrEqual(2);
	expect(order.items[0].productName.length).toBeGreaterThan(0);
	expect(order.items[0].packed).toBe(0);
});

test("the protocol accepts the delivery commands and rejects malformed packing", () => {
	openApp();
	const now = Date.now();
	store().devSpawnDeliveryOffer(now);
	const offer = store().delivery.orders.at(-1);
	const send = createSimulatorCommandHandler("delivery-session", () => store(), () => 0);
	const command = (id, action, args) => ({ protocol: 1, session: "delivery-session", id, revision: 0, action, args });

	expect(simulatorActions).toEqual(expect.arrayContaining(["acceptDeliveryOrder", "declineDeliveryOrder", "packDeliveryOrder", "handOverDelivery"]));
	expect(simulatorActions).not.toContain("processDelivery");
	expect(simulatorActions).not.toContain("devSpawnDeliveryOffer");

	expect(send(command("p1", "acceptDeliveryOrder", [offer.id])).ok).toBe(true);
	expect(send(command("p2", "packDeliveryOrder", [offer.id, { items: fullPack(offer), quality: 1.5, seconds: 30 }])).reason).toBe("invalid-action");
	expect(send(command("p3", "packDeliveryOrder", [offer.id, { items: fullPack(offer), quality: 0.8, seconds: 30 }])).ok).toBe(true);
	expect(send(command("p4", "handOverDelivery", [offer.id])).reason).toBe("game-rule-rejected");
	expect(send(command("p5", "declineDeliveryOrder", [offer.id])).reason).toBe("game-rule-rejected");
});

test("pure rules: stars, tips, streak bonus and the rating window", () => {
	expect(delivery.getPackStars({ fillRatio: 1, quality: 1, seconds: 30 })).toBe(5);
	expect(delivery.getPackStars({ fillRatio: 1, quality: 1, seconds: 100 })).toBe(4.5);
	expect(delivery.getPackStars({ fillRatio: 0, quality: 0, seconds: 30 })).toBe(1);
	expect(delivery.getTipRate(3.5)).toBe(0);
	expect(delivery.getTipRate(4)).toBe(0.05);
	expect(delivery.getTipRate(4.5)).toBe(0.1);
	expect(delivery.getTipRate(5)).toBe(0.2);
	expect(delivery.getStreakBonusRate(1)).toBeCloseTo(0.1, 10);
	expect(delivery.getStreakBonusRate(9)).toBe(0.5);
	expect(delivery.applyStarsToRating(4.6, 5)).toBe(4.62);
	expect(delivery.applyLateCancelToRating(1.2)).toBe(1);
	expect(delivery.pushRating(Array.from({ length: 20 }, () => 3), 5).length).toBe(20);
	expect(delivery.getDeliveryFee(2.5)).toBe(9);
	expect(delivery.getTripMs(4.5)).toBe(152_500);
});

test("a substitute product fills only the missing units of a packed order", async () => {
	const { clampPackedItems } = await import("./delivery.ts");
	const order = { items: [{ productId: 1, quantity: 2 }, { productId: 2, quantity: 1 }] };
	const stock = (id) => ({ 1: 1, 2: 1, 9: 5 })[id] ?? 0;
	const packed = clampPackedItems(order, [{ productId: 1, quantity: 2 }, { productId: 2, quantity: 1 }, { productId: 9, quantity: 3 }], stock);
	expect(packed).toEqual([{ productId: 1, quantity: 1 }, { productId: 2, quantity: 1 }, { productId: 9, quantity: 1 }]);
});
