import type {
	StoreIncident,
	StoreIncidentEffects,
	StoreIncidentKind,
	StoreIncidentShelf,
	StoreIncidentsState,
} from "@/@types/store-incident";

// Shared rules for store mishaps (System, mobile simulator and desktop).
// Mishaps are occasional: the first comes a couple of minutes after opening and then one every 3.5–5.5 min
// (about one in a 5-minute day), so they stay a surprise instead of a chore.
export const FIRST_INCIDENT_DELAY_MS = 120_000;
export const INCIDENT_INTERVAL_MS = { min: 210_000, max: 330_000 };
export const MAX_ACTIVE_INCIDENTS = 2;
// Floor dirt: a new spot every 2.5–4.5 min while open, never more than two at once.
export const FIRST_DIRT_DELAY_MS = 100_000;
export const DIRT_INTERVAL_MS = { min: 150_000, max: 270_000 };
export const MAX_DIRT = 2;
export const FREEZER_SPOIL_INTERVAL_MS = 20_000;
// An employee fixes one incident every 25 s per unit of efficiency.
export const STAFF_FIX_INTERVAL_MS = 25_000;
const MAX_RECENT = 10;

// Which shelves each cooler holds: the chest freezer (ice cream and frozen food) and the upright
// fridge (drinks and chilled goods).
export const frozenCategories = ["congelados", "carnes", "peixes"];
export const drinkCategories = [
	"bebidas",
	"refrigerantes",
	"aguas",
	"energeticos",
	"laticinios",
	"frios",
	"queijos",
];
export const chilledCategories = [...frozenCategories, ...drinkCategories];
export const coolerKinds: StoreIncidentKind[] = ["freezer_sorvete", "geladeira_bebidas"];
export function isCoolerIncident(kind: StoreIncidentKind) {
	return kind === "freezer_sorvete" || kind === "geladeira_bebidas";
}
function fitsShelf(kind: StoreIncidentKind, shelf: StoreIncidentShelf) {
	if (kind === "freezer_sorvete") return frozenCategories.includes(shelf.category);
	if (kind === "geladeira_bebidas") return drinkCategories.includes(shelf.category);
	if (kind === "etiqueta") return shelf.price > 1;
	return true;
}

export const incidentReputationPenalty: Record<StoreIncidentKind, number> = {
	derramado: 8,
	sujeira: 3,
	lampada: 5,
	freezer_sorvete: 4,
	geladeira_bebidas: 4,
	etiqueta: 2,
};

// Which employee role fixes which mishap on their own. The coolers need the player (and coins).
export const incidentStaff: Record<StoreIncidentKind, "cleaner" | "stock_clerk" | null> = {
	derramado: "cleaner",
	sujeira: "cleaner",
	lampada: "cleaner",
	etiqueta: "stock_clerk",
	freezer_sorvete: null,
	geladeira_bebidas: null,
};

export const incidentLabels: Record<StoreIncidentKind, { title: string; action: string }> = {
	derramado: { title: "Algo derramado no chão", action: "Limpar" },
	sujeira: { title: "Chão sujo", action: "Varrer" },
	freezer_sorvete: { title: "Freezer de sorvete em curto", action: "Consertar" },
	geladeira_bebidas: { title: "Geladeira de bebidas em curto", action: "Consertar" },
	etiqueta: { title: "Etiqueta com preço errado", action: "Trocar etiqueta" },
	lampada: { title: "Lâmpada queimada", action: "Trocar lâmpada" },
};

type Random = () => number;
function seeded(seed: number): Random {
	let state = (seed * 2246822519) >>> 0;
	return () => {
		state += 0x6d2b79f5;
		let value = state;
		value = Math.imul(value ^ (value >>> 15), value | 1);
		value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
		return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
	};
}

export function createStoreIncidentsState(): StoreIncidentsState {
	return {
		active: [],
		fixed: 0,
		nextAt: null,
		nextDirtAt: null,
		nextStaffFixAt: null,
		recent: [],
		seed: 1,
		spoilAt: null,
	};
}

export function normalizeStoreIncidentsState(
	value: Partial<StoreIncidentsState> | undefined,
): StoreIncidentsState {
	const initial = createStoreIncidentsState();
	if (!value || typeof value !== "object") return initial;
	// Saves from before the two coolers had a single "freezer" kind.
	const kind = (item: { kind: string }) =>
		(item.kind === "freezer" ? "freezer_sorvete" : item.kind) as StoreIncidentKind;
	return {
		...initial,
		...value,
		active: Array.isArray(value.active)
			? value.active.map((item) => ({ ...item, kind: kind(item) }))
			: [],
		recent: Array.isArray(value.recent)
			? value.recent.map((item) => ({ ...item, kind: kind(item) }))
			: [],
	};
}

export function getFreezerRepairCost(level: number) {
	return Math.round((40 + level * 12) / 5) * 5;
}

// Picks a mishap for a shelf that does not have the same one already.
// A spill and dirt both lie on the floor in front of the shelf: never two of them in the same spot.
function isFloorMess(kind: StoreIncidentKind) {
	return kind === "derramado" || kind === "sujeira";
}

export function createStoreIncident(
	state: StoreIncidentsState,
	shelves: StoreIncidentShelf[],
	now: number,
	level: number,
	forceKind?: StoreIncidentKind,
	anyShelf = false, // dev cheat: skip the cooler/price fit
): StoreIncident | null {
	const random = seeded(state.seed);
	const candidates = shelves.filter((shelf) => shelf.productId > 0);
	if (!candidates.length) return null;
	const kinds: StoreIncidentKind[] = forceKind
		? [forceKind]
		: (() => {
				// A random first choice; the rest are fallbacks when no shelf fits it.
				const all: StoreIncidentKind[] = [
					"derramado",
					"etiqueta",
					"lampada",
					"freezer_sorvete",
					"geladeira_bebidas",
				];
				// Spills are the least frequent: the floor already gets dirt of its own.
				const weights = [0.16, 0.22, 0.2, 0.21, 0.21];
				let roll = random();
				let first = 0;
				while (first < weights.length - 1 && roll >= weights[first]) roll -= weights[first++];
				return [all[first], ...all.filter((_, index) => index !== first)];
			})();
	for (const kind of kinds) {
		const pool = candidates.filter(
			(shelf) =>
				!state.active.some(
					(incident) =>
						incident.shelfId === shelf.shelfId &&
						(incident.kind === kind || (isFloorMess(incident.kind) && isFloorMess(kind))),
				) &&
				(anyShelf || fitsShelf(kind, shelf)),
		);
		const shelf = pool[Math.floor(random() * pool.length)];
		if (!shelf) continue;
		return {
			createdAt: now,
			fixCost: isCoolerIncident(kind) ? getFreezerRepairCost(level) : 0,
			id: `imprevisto-${state.seed}`,
			kind,
			productId: shelf.productId,
			productName: shelf.productName,
			shelfId: shelf.shelfId,
			shelfName: shelf.shelfName,
			tagPrice: kind === "etiqueta" ? Math.max(1, Math.round(shelf.price * 0.5)) : 0,
		};
	}
	return null;
}

// Spawns mishaps while the market is open, at a random pace and never more than two at once.
export function spawnStoreIncident(
	state: StoreIncidentsState,
	shelves: StoreIncidentShelf[],
	now: number,
	level: number,
	isOpen: boolean,
): { incident: StoreIncident | null; state: StoreIncidentsState } {
	if (!isOpen)
		return { incident: null, state: state.nextAt === null ? state : { ...state, nextAt: null } };
	if (state.nextAt === null)
		return { incident: null, state: { ...state, nextAt: now + FIRST_INCIDENT_DELAY_MS } };
	if (now < state.nextAt) return { incident: null, state };
	const random = seeded(state.seed + 99);
	const nextAt =
		now +
		INCIDENT_INTERVAL_MS.min +
		random() * (INCIDENT_INTERVAL_MS.max - INCIDENT_INTERVAL_MS.min);
	const incident =
		state.active.filter((item) => item.kind !== "sujeira").length < MAX_ACTIVE_INCIDENTS
			? createStoreIncident(state, shelves, now, level)
			: null;
	return {
		incident,
		state: {
			...state,
			active: incident ? [...state.active, incident] : state.active,
			nextAt,
			seed: state.seed + 1,
		},
	};
}

// Dirt customers track in: independent from the mishaps, at its own pace, up to MAX_DIRT spots.
export function spawnFloorDirt(
	state: StoreIncidentsState,
	shelves: StoreIncidentShelf[],
	now: number,
	isOpen: boolean,
): { incident: StoreIncident | null; state: StoreIncidentsState } {
	if (!isOpen)
		return {
			incident: null,
			state: state.nextDirtAt === null ? state : { ...state, nextDirtAt: null },
		};
	if (state.nextDirtAt === null)
		return { incident: null, state: { ...state, nextDirtAt: now + FIRST_DIRT_DELAY_MS } };
	if (now < state.nextDirtAt) return { incident: null, state };
	const random = seeded(state.seed + 577);
	const nextDirtAt =
		now + DIRT_INTERVAL_MS.min + random() * (DIRT_INTERVAL_MS.max - DIRT_INTERVAL_MS.min);
	const dirty = state.active.filter((item) => item.kind === "sujeira").length;
	const incident =
		dirty < MAX_DIRT ? createStoreIncident(state, shelves, now, 1, "sujeira") : null;
	return {
		incident,
		state: {
			...state,
			active: incident ? [...state.active, incident] : state.active,
			nextDirtAt,
			seed: state.seed + 1,
		},
	};
}

export function getIncidentEffects(active: StoreIncident[]): StoreIncidentEffects {
	const priceMultipliers: Record<string, number> = {};
	for (const incident of active)
		if (incident.kind === "etiqueta") priceMultipliers[incident.shelfId] = 0.5;
	return {
		blockedShelfIds: active
			.filter((incident) => isCoolerIncident(incident.kind))
			.map((incident) => incident.shelfId),
		priceMultipliers,
		reputationPenalty: active.reduce(
			(total, incident) => total + incidentReputationPenalty[incident.kind],
			0,
		),
	};
}

export function fixStoreIncident(
	state: StoreIncidentsState,
	incidentId: string,
	now: number,
	by: "player" | "staff",
): { incident: StoreIncident; state: StoreIncidentsState } | null {
	const incident = state.active.find((item) => item.id === incidentId);
	if (!incident) return null;
	return {
		incident,
		state: {
			...state,
			active: state.active.filter((item) => item.id !== incidentId),
			fixed: state.fixed + 1,
			recent: [{ by, fixedAt: now, id: incident.id, kind: incident.kind }, ...state.recent].slice(
				0,
				MAX_RECENT,
			),
		},
	};
}

// Cleaners mop spills and change bulbs; stock clerks re-tag prices. One job at a time.
export function nextStaffFix(
	state: StoreIncidentsState,
	now: number,
	efficiency: { cleaner: number; stock_clerk: number },
): { incidentId: string | null; state: StoreIncidentsState } {
	const doable = state.active
		.filter((incident) => {
			const role = incidentStaff[incident.kind];
			return role !== null && efficiency[role] > 0;
		})
		.sort((a, b) => a.createdAt - b.createdAt);
	const job = doable[0];
	if (!job)
		return {
			incidentId: null,
			state: state.nextStaffFixAt === null ? state : { ...state, nextStaffFixAt: null },
		};
	const role = incidentStaff[job.kind] as "cleaner" | "stock_clerk";
	const interval = STAFF_FIX_INTERVAL_MS / efficiency[role];
	if (state.nextStaffFixAt === null)
		return { incidentId: null, state: { ...state, nextStaffFixAt: now + interval } };
	if (now < state.nextStaffFixAt) return { incidentId: null, state };
	return { incidentId: job.id, state: { ...state, nextStaffFixAt: null } };
}

// A broken cooler spoils one unit of its shelf every FREEZER_SPOIL_INTERVAL_MS.
export function freezerSpoilage(
	state: StoreIncidentsState,
	now: number,
): { shelfIds: string[]; state: StoreIncidentsState } {
	const freezers = state.active.filter((incident) => isCoolerIncident(incident.kind));
	if (!freezers.length)
		return { shelfIds: [], state: state.spoilAt === null ? state : { ...state, spoilAt: null } };
	if (state.spoilAt === null)
		return { shelfIds: [], state: { ...state, spoilAt: now + FREEZER_SPOIL_INTERVAL_MS } };
	if (now < state.spoilAt) return { shelfIds: [], state };
	return {
		shelfIds: freezers.map((incident) => incident.shelfId),
		state: { ...state, spoilAt: now + FREEZER_SPOIL_INTERVAL_MS },
	};
}
