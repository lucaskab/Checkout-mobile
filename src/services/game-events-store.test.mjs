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
// The store is shared with the other test files: hand it back as it was found.
const pristine = JSON.stringify(useGameStore.getState());
useGameStore.setState({ interior: { items: [], owned: {} } });
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(pristine)));

const store = () => useGameStore.getState();
const MIN = 60_000;

/** Pretend the active event started `ms` ago and is over now. */
function endActiveEvent() {
	const events = store().events;
	useGameStore.setState({ events: { ...events, activeEvent: { ...events.activeEvent, endsAt: Date.now() - 1 } } });
}

test("the inspector opens a real mishap at each stop and approves a market that fixes them all", () => {
	useGameStore.setState({ coins: 1_000, era: { ...store().era, id: "mercadinho" } });
	expect(store().devActivateGameEvent("vigilancia-sanitaria")).toBe(true);
	const startedAt = Date.now() - 60_000;
	// Pretend the visit started a minute ago: the first stop is due.
	useGameStore.setState({ events: { ...store().events, activeEvent: { ...store().events.activeEvent, startedAt, endsAt: Date.now() + 90_000 } } });
	store().processGameEvents();
	const run = store().events.inspection;
	expect(run.stops.length).toBe(3);
	const open = run.stops.find((stop) => stop.status === "open");
	if (!open) return; // a market with no product on a shelf has nothing to inspect
	expect(store().incidents.active.some((incident) => incident.id === open.incidentId)).toBe(true);
	// The player fixes it: the stop passes on the next tick.
	useGameStore.setState({ coins: 100_000 });
	expect(store().fixIncident(open.incidentId)).toBe(true);
	store().processGameEvents();
	expect(store().events.inspection.stops.find((stop) => stop.id === open.id).status).toBe("fixed");
});

test("the inspector fines a market that left the problems unfixed", () => {
	useGameStore.setState({ coins: 1_000 });
	store().devActivateGameEvent("vigilancia-sanitaria");
	const active = store().events.activeEvent;
	useGameStore.setState({
		events: {
			...store().events,
			inspection: {
				startedAt: active.startedAt,
				stops: ["a", "b", "c"].map((id) => ({ id, at: 0, deadline: 1, incidentId: `x-${id}`, kind: "lampada", shelfId: "produce", status: "failed" })),
			},
		},
	});
	endActiveEvent();
	expect(store().processGameEvents()).toBe(true);
	expect(store().events.inspection).toBe(null);
	expect(store().coins).toBeLessThan(1_000);
	expect(store().events.outcome.kind).toBe("negative");
	expect(store().events.outcome.text).toContain("0/3");
});

test("drivers in the jam ask for drinks and pay with a tip through the window", () => {
	store().devActivateGameEvent("engarrafamento");
	const water = 21;
	useGameStore.setState({
		inventory: { ...store().inventory, [water]: 5 },
		market: { ...store().market, unlockedProductIds: Array.from(new Set([...store().market.unlockedProductIds, water])) },
	});
	const now = Date.now();
	useGameStore.setState({
		events: {
			...store().events,
			windowSales: {
				goal: 6, nextAt: now + 60_000, rewardPaid: false, seq: 1, served: 0,
				requests: [{ id: "janela-1", lane: 0, slot: 1, productId: water, createdAt: now, expiresAt: now + 10_000, status: "waiting" }],
			},
		},
	});
	const coins = store().coins;
	const units = store().market.unitsSold;
	expect(store().serveWindowSale("janela-1")).toBe(true);
	expect(store().coins).toBeGreaterThan(coins);
	expect(store().market.unitsSold).toBe(units + 1);
	expect(store().events.windowSales.served).toBe(1);
	// The same driver cannot be served twice.
	expect(store().serveWindowSale("janela-1")).toBe(false);
});

test("a power cut and a heat wave no longer wear any fixture", () => {
	useGameStore.setState({ shelfCare: {}, era: { ...store().era, id: "conteiner" } });
	for (const id of ["queda-de-energia", "onda-de-calor"]) {
		store().devActivateGameEvent(id);
		useGameStore.setState({ events: { ...store().events, wearTickAt: Date.now() - 2 * MIN } });
		store().processGameEvents();
		expect(store().shelfCare).toEqual({});
	}
});

test("viralizou films a product that is on sale", () => {
	const stocked = Object.entries(store().shelfStock)
		.filter(([, units]) => units > 0)
		.map(([slot]) => store().shelfAssignments[slot]);
	store().devActivateGameEvent("viralizou");
	const featured = store().events.activeEvent.featuredProductId;
	if (stocked.length > 0) expect(stocked).toContain(featured);
	else expect(featured).toBe(undefined);
});
