import { expect, test } from "bun:test";
import {
	createStoreIncident,
	createStoreIncidentsState,
	FIRST_INCIDENT_DELAY_MS,
	FREEZER_SPOIL_INTERVAL_MS,
	fixStoreIncident,
	freezerSpoilage,
	getIncidentEffects,
	MAX_ACTIVE_INCIDENTS,
	nextStaffFix,
	STAFF_FIX_INTERVAL_MS,
	spawnStoreIncident,
} from "./store-incidents";

const shelves = [
	{ shelfId: "dairy", shelfName: "Prateleira 2", productId: 5, productName: "Leite", category: "laticinios", price: 8, stock: 3 },
	{ shelfId: "bakery", shelfName: "Prateleira 3", productId: 9, productName: "Pão", category: "padaria", price: 4, stock: 3 },
];
const t0 = 9_000_000;

test("mishaps only start a while after opening and never pile up past two", () => {
	let state = createStoreIncidentsState();
	let step = spawnStoreIncident(state, shelves, t0, 3, true);
	expect(step.incident).toBeNull();
	expect(step.state.nextAt).toBe(t0 + FIRST_INCIDENT_DELAY_MS);
	state = step.state;
	for (let i = 0; i < 6; i++) {
		step = spawnStoreIncident(state, shelves, state.nextAt, 3, true);
		state = step.state;
	}
	expect(state.active.length).toBe(MAX_ACTIVE_INCIDENTS);
	expect(spawnStoreIncident(state, shelves, t0, 3, false).state.nextAt).toBeNull();
});

test("each kind of mishap has its own effect on the store", () => {
	const base = createStoreIncidentsState();
	const freezer = createStoreIncident(base, shelves, t0, 3, "geladeira_bebidas");
	expect(freezer.shelfId).toBe("dairy");
	expect(freezer.fixCost).toBeGreaterThan(0);
	const tag = createStoreIncident({ ...base, seed: 2 }, shelves, t0, 3, "etiqueta");
	expect(tag.tagPrice).toBeLessThan(shelves.find((s) => s.shelfId === tag.shelfId).price);
	const spill = createStoreIncident({ ...base, seed: 3 }, shelves, t0, 3, "derramado");
	const effects = getIncidentEffects([freezer, tag, spill]);
	expect(effects.blockedShelfIds).toEqual(["dairy"]);
	expect(effects.priceMultipliers[tag.shelfId]).toBe(0.5);
	expect(effects.reputationPenalty).toBeGreaterThan(10);
	// Coolers only break on their own shelves: drinks/dairy in the fridge, frozen food in the freezer.
	expect(createStoreIncident(base, [shelves[1]], t0, 3, "geladeira_bebidas")).toBeNull();
	expect(createStoreIncident(base, shelves, t0, 3, "freezer_sorvete")).toBeNull();
	const frozen = [{ ...shelves[0], shelfId: "ice", category: "congelados" }];
	expect(createStoreIncident(base, frozen, t0, 3, "freezer_sorvete").shelfId).toBe("ice");
});

test("fixing removes the mishap once", () => {
	const incident = createStoreIncident(createStoreIncidentsState(), shelves, t0, 3, "derramado");
	const state = { ...createStoreIncidentsState(), active: [incident] };
	const fixed = fixStoreIncident(state, incident.id, t0, "player");
	expect(fixed.state.active).toEqual([]);
	expect(fixed.state.fixed).toBe(1);
	expect(fixStoreIncident(fixed.state, incident.id, t0, "player")).toBeNull();
});

test("a broken freezer spoils stock at a steady pace", () => {
	const incident = createStoreIncident(createStoreIncidentsState(), shelves, t0, 3, "geladeira_bebidas");
	let state = { ...createStoreIncidentsState(), active: [incident] };
	let step = freezerSpoilage(state, t0);
	expect(step.shelfIds).toEqual([]);
	state = step.state;
	step = freezerSpoilage(state, t0 + FREEZER_SPOIL_INTERVAL_MS);
	expect(step.shelfIds).toEqual(["dairy"]);
});

test("cleaners mop spills but nobody fixes the freezer for free", () => {
	const spill = createStoreIncident(createStoreIncidentsState(), shelves, t0, 3, "derramado");
	const freezer = createStoreIncident({ ...createStoreIncidentsState(), seed: 5 }, shelves, t0, 3, "geladeira_bebidas");
	let state = { ...createStoreIncidentsState(), active: [freezer, spill] };
	expect(nextStaffFix(state, t0, { cleaner: 0, stock_clerk: 1 }).incidentId).toBeNull();
	let step = nextStaffFix(state, t0, { cleaner: 1, stock_clerk: 0 });
	state = step.state;
	step = nextStaffFix(state, t0 + STAFF_FIX_INTERVAL_MS, { cleaner: 1, stock_clerk: 0 });
	expect(step.incidentId).toBe(spill.id);
});

test("mishaps are spaced out and old freezer saves load as the ice cream freezer", async () => {
	const { INCIDENT_INTERVAL_MS, normalizeStoreIncidentsState } = await import("./store-incidents");
	expect(FIRST_INCIDENT_DELAY_MS).toBeGreaterThanOrEqual(60_000);
	expect(INCIDENT_INTERVAL_MS.min).toBeGreaterThanOrEqual(120_000);
	const old = createStoreIncident(createStoreIncidentsState(), shelves, t0, 3, "derramado");
	const loaded = normalizeStoreIncidentsState({ active: [{ ...old, kind: "freezer" }], recent: [] });
	expect(loaded.active[0].kind).toBe("freezer_sorvete");
});

test("both coolers show up over many rolls", () => {
	const all = [
		...shelves,
		{ shelfId: "ice", shelfName: "Freezer", productId: 7, productName: "Sorvete", category: "congelados", price: 12, stock: 3 },
	];
	const seen = new Set();
	for (let seed = 1; seed < 200; seed++)
		seen.add(createStoreIncident({ ...createStoreIncidentsState(), seed }, all, t0, 3).kind);
	expect(seen.has("freezer_sorvete")).toBe(true);
	expect(seen.has("geladeira_bebidas")).toBe(true);
});
