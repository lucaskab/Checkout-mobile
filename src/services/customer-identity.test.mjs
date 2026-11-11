import { afterAll, beforeEach, expect, mock, test } from "bun:test";

// Customer names match the sex of the body Unity shows (Lucas, 08/11: "Ana" on a man at the checkout).
globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { customerNames, pickCustomerIdentity, sexOfCustomerName } = await import("../data/customer-names.ts");
const { useGameStore } = await import("../stores/game-store.ts");
const { createSimulatorSnapshot } = await import("./simulator-snapshot.ts");
const { FREE_DAY_CONTRACT_ID } = await import("./market-day.ts");
useGameStore.setState({ interior: { items: [], owned: {} } });
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const store = () => useGameStore.getState();

test("every name belongs to one sex only, and the names of the old saves keep theirs", () => {
	const seen = new Map();
	for (const names of Object.values(customerNames))
		for (const sex of ["f", "m"])
			for (const name of names[sex]) {
				expect(seen.get(name) ?? sex).toBe(sex);
				seen.set(name, sex);
				expect(sexOfCustomerName(name)).toBe(sex);
			}
	for (const name of ["Ana", "Paula", "Rita", "Bia", "Nina", "Lara", "Helena", "Clara", "Sofia"]) expect(sexOfCustomerName(name)).toBe("f");
	for (const name of ["Marcos", "Davi", "Lucas", "Caio", "Igor", "Pedro"]) expect(sexOfCustomerName(name)).toBe("m");
	expect(sexOfCustomerName("Cliente teste")).toBeUndefined();
});

test("a new customer gets a name of their own sex, women and men in every archetype", () => {
	for (const archetype of Object.keys(customerNames)) {
		const count = { f: 0, m: 0 };
		for (let seed = 1; seed <= 400; seed++) {
			const { name, sex } = pickCustomerIdentity(archetype, seed);
			expect(customerNames[archetype][sex]).toContain(name);
			count[sex]++;
		}
		expect(count.f).toBeGreaterThan(140);
		expect(count.m).toBeGreaterThan(140);
	}
	expect(pickCustomerIdentity("premium", 77)).toEqual(pickCustomerIdentity("premium", 77));
});

test("the customer, their checkout and Unity's snapshot carry the same name and its sex", () => {
	store().startDay(FREE_DAY_CONTRACT_ID);
	let checked = 0;
	for (let index = 0; index < 30; index++) {
		useGameStore.setState({ market: { ...store().market, nextCustomerAt: 1 } });
		if (!store().processNextCustomer()) continue;
		const latest = store().market.recentCustomers[0];
		expect(["f", "m"]).toContain(latest.sex);
		expect(sexOfCustomerName(latest.name)).toBe(latest.sex);
		const sent = createSimulatorSnapshot(store(), "day", index + 1).customers[0];
		expect(sent.sex).toBe(latest.sex);
		const checkout = store().checkout.queue.find((entry) => entry.customerId === latest.id);
		if (checkout) expect(checkout.customerName).toBe(latest.name);
		checked++;
	}
	expect(checked).toBeGreaterThan(0);
});

test("customers saved before the sex existed reach Unity with the sex of their name", () => {
	const old = [
		{ id: "old-1", item: "", mood: "calmo", name: "Helena", satisfaction: 50, spent: 10, status: "pagou" },
		{ id: "old-2", item: "", mood: "calmo", name: "Caio", satisfaction: 50, spent: 10, status: "pagou" },
	];
	useGameStore.setState({ market: { ...store().market, recentCustomers: old } });
	const sent = createSimulatorSnapshot(store(), "day", 1).customers;
	expect(sent.map((customer) => customer.sex)).toEqual(["f", "m"]);
});
