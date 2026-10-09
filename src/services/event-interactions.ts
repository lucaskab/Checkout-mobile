import type {
	InspectionRun,
	InspectionStop,
	WindowSaleRequest,
	WindowSalesState,
} from "@/@types/game-event";
import type { StoreIncident, StoreIncidentKind } from "@/@types/store-incident";

// The things the player DOES during an event (Oct 2026):
// - Vigilância sanitária: the inspector walks to three spots of the market; at each one a real mishap shows
//   up (wrong price tag, burnt lamp, wet floor, warm cooler) and the player has a few seconds to fix it.
// - Engarrafamento: drivers stuck in the jam honk and ask for a drink through the window; a click sends the
//   clerk out with the cooler and the bottle is sold on the spot, with a tip.

// ── Vigilância sanitária ─────────────────────────────────────────────────────────────────────────────────
export const INSPECTION_STOPS = 3;
/** Time to fix what the inspector found at a stop. */
export const INSPECTION_FIX_MS = 25_000;
/** The inspector walks in before the first stop. */
const INSPECTION_FIRST_STOP_MS = 8_000;

/** What the inspector can find, in order of preference (coolers only where the market has one). */
export const INSPECTION_KINDS: StoreIncidentKind[] = [
	"etiqueta",
	"lampada",
	"derramado",
	"geladeira_bebidas",
	"freezer_sorvete",
];

export function createInspectionRun(startedAt: number, endsAt: number): InspectionRun {
	// Three stops spread over the visit, each with its full fixing time before the visit ends.
	const last = Math.max(startedAt + INSPECTION_FIRST_STOP_MS, endsAt - INSPECTION_FIX_MS - 2_000);
	const step = (last - startedAt - INSPECTION_FIRST_STOP_MS) / Math.max(1, INSPECTION_STOPS - 1);
	const stops: InspectionStop[] = Array.from({ length: INSPECTION_STOPS }, (_, index) => ({
		at: Math.round(startedAt + INSPECTION_FIRST_STOP_MS + step * index),
		deadline: 0,
		id: `fiscal-${index + 1}`,
		incidentId: null,
		kind: null,
		shelfId: null,
		status: "waiting",
	}));
	return { stops, startedAt };
}

export type InspectionAdvance = {
	run: InspectionRun;
	/** The stop that needs a mishap now (the store creates it with createStoreIncident). */
	needsIncident: InspectionStop | null;
};

/**
 * Moves the visit: an open stop is "fixed" once its mishap is gone (player or staff), "failed" when its time
 * runs out; the next stop opens when the inspector gets there.
 */
export function advanceInspection(
	run: InspectionRun,
	now: number,
	activeIncidents: Pick<StoreIncident, "id">[],
): InspectionAdvance {
	let changed = false;
	const stops = run.stops.map((stop) => {
		if (stop.status !== "open") return stop;
		const stillThere = stop.incidentId !== null && activeIncidents.some((incident) => incident.id === stop.incidentId);
		if (!stillThere) {
			changed = true;
			return { ...stop, status: "fixed" as const };
		}
		if (now >= stop.deadline) {
			changed = true;
			return { ...stop, status: "failed" as const };
		}
		return stop;
	});
	const busy = stops.some((stop) => stop.status === "open");
	const next = busy ? undefined : stops.find((stop) => stop.status === "waiting" && now >= stop.at);
	const nextRun = changed ? { ...run, stops } : run;
	return { run: nextRun, needsIncident: next ?? null };
}

/** The stop opened with the mishap the store created for it (or skipped when nothing could be created). */
export function openInspectionStop(
	run: InspectionRun,
	stopId: string,
	incident: Pick<StoreIncident, "id" | "kind" | "shelfId"> | null,
	now: number,
): InspectionRun {
	return {
		...run,
		stops: run.stops.map((stop) => {
			if (stop.id !== stopId) return stop;
			// No fixture to inspect (empty market): the inspector notes nothing there.
			if (!incident) return { ...stop, status: "fixed" as const, deadline: now };
			return {
				...stop,
				deadline: now + INSPECTION_FIX_MS,
				incidentId: incident.id,
				kind: incident.kind,
				shelfId: incident.shelfId,
				status: "open" as const,
			};
		}),
	};
}

/** Which mishap the inspector looks for next: one he has not found yet, a cooler only if allowed. */
export function pickInspectionKind(run: InspectionRun, hasCooler: boolean, seed: number): StoreIncidentKind[] {
	const used = new Set(run.stops.map((stop) => stop.kind).filter(Boolean));
	const pool = INSPECTION_KINDS.filter(
		(kind) => !used.has(kind) && (hasCooler || (kind !== "geladeira_bebidas" && kind !== "freezer_sorvete")),
	);
	const start = pool.length ? Math.floor(Math.abs(Math.sin(seed * 7.13)) * pool.length) % pool.length : 0;
	return [...pool.slice(start), ...pool.slice(0, start), ...INSPECTION_KINDS.filter((kind) => !pool.includes(kind))];
}

export type InspectionResult = {
	passed: number;
	total: number;
	/** approved (all fixed), warning (one missed), fined (two or more missed). */
	grade: "approved" | "warning" | "fined";
	coins: number;
	reputation: number;
};

/** The verdict when the visit ends; stops still open or not reached count as missed. */
export function scoreInspection(run: InspectionRun, dailyGoal: number): InspectionResult {
	const total = run.stops.length;
	const passed = run.stops.filter((stop) => stop.status === "fixed").length;
	const goal = Math.max(0, dailyGoal);
	if (passed === total)
		return { passed, total, grade: "approved", coins: Math.max(40, Math.round(goal * 0.1)), reputation: 3 };
	if (passed === total - 1) return { passed, total, grade: "warning", coins: 0, reputation: 0 };
	return { passed, total, grade: "fined", coins: -Math.max(20, Math.round(goal * 0.08)), reputation: -2 };
}

// ── Engarrafamento: venda pela janela ────────────────────────────────────────────────────────────────────
/** Lanes and cars per lane of the jam scene in Unity (CheckoutEventTraffic). */
export const WINDOW_LANES = 3;
export const WINDOW_CARS_PER_LANE = 4;
export const WINDOW_REQUEST_MS = 15_000;
const WINDOW_FIRST_REQUEST_MS = 6_000;
const WINDOW_GAP_MIN_MS = 10_000;
const WINDOW_GAP_SPREAD_MS = 8_000;
const WINDOW_MAX_WAITING = 2;
export const WINDOW_SALES_GOAL = 6;
/** Drivers pay the shelf price plus this tip. */
export const WINDOW_TIP_SHARE = 0.3;
/** What drivers ask for. */
export const WINDOW_CATEGORIES = ["aguas", "refrigerantes"];

const random = (seed: number) => {
	const value = Math.sin(seed * 12.9898) * 43_758.5453;
	return value - Math.floor(value);
};

export function createWindowSales(startedAt: number): WindowSalesState {
	return { goal: WINDOW_SALES_GOAL, nextAt: startedAt + WINDOW_FIRST_REQUEST_MS, requests: [], rewardPaid: false, seq: 0, served: 0 };
}

/**
 * Drivers honk now and then (never more than two at once, each in a different car) asking for one of the
 * drinks the market sells; unanswered requests expire.
 */
export function advanceWindowSales(
	state: WindowSalesState,
	now: number,
	productIds: number[],
	endsAt: number,
): WindowSalesState {
	let next = state;
	if (state.requests.some((request) => request.status === "waiting" && now >= request.expiresAt))
		next = {
			...next,
			requests: next.requests.map((request) =>
				request.status === "waiting" && now >= request.expiresAt ? { ...request, status: "missed" as const } : request,
			),
		};
	const waiting = next.requests.filter((request) => request.status === "waiting");
	// No new request that could not be answered before the jam clears.
	if (now < next.nextAt || waiting.length >= WINDOW_MAX_WAITING || productIds.length === 0 || endsAt - now < 8_000)
		return next;
	const seq = next.seq + 1;
	const taken = new Set(waiting.map((request) => `${request.lane}:${request.slot}`));
	const free: [number, number][] = [];
	for (let lane = 0; lane < WINDOW_LANES; lane++)
		for (let slot = 0; slot < WINDOW_CARS_PER_LANE; slot++) if (!taken.has(`${lane}:${slot}`)) free.push([lane, slot]);
	const [lane, slot] = free[Math.floor(random(seq * 3.7 + now / 1000) * free.length)] ?? [0, 0];
	const productId = productIds[Math.floor(random(seq * 5.3) * productIds.length)] ?? productIds[0];
	const request: WindowSaleRequest = {
		createdAt: now,
		expiresAt: Math.min(endsAt, now + WINDOW_REQUEST_MS),
		id: `janela-${seq}`,
		lane,
		productId,
		slot,
		status: "waiting",
	};
	return {
		...next,
		nextAt: now + WINDOW_GAP_MIN_MS + Math.round(random(seq * 9.1) * WINDOW_GAP_SPREAD_MS),
		requests: [...next.requests, request].slice(-12),
		seq,
	};
}

/** The bottle handed through the window: the request is done (the store sells the unit). */
export function serveWindowRequest(state: WindowSalesState, requestId: string, now: number) {
	const request = state.requests.find((item) => item.id === requestId);
	if (!request || request.status !== "waiting" || now >= request.expiresAt) return null;
	const served = state.served + 1;
	const reachedGoal = served >= state.goal && !state.rewardPaid;
	return {
		request,
		reachedGoal,
		state: {
			...state,
			rewardPaid: state.rewardPaid || reachedGoal,
			requests: state.requests.map((item) =>
				item.id === requestId ? { ...item, servedAt: now, status: "served" as const } : item,
			),
			served,
		},
	};
}

/** Price the driver pays: the shelf price with the tip on top. */
export function getWindowSalePrice(unitPrice: number) {
	const price = Math.max(1, Math.round(unitPrice));
	const tip = Math.max(1, Math.round(price * WINDOW_TIP_SHARE));
	return { price, tip };
}

/** Bonus for reaching the goal of the jam. */
export function getWindowSalesBonus(dailyGoal: number) {
	return Math.max(30, Math.round(Math.max(0, dailyGoal) * 0.06));
}
