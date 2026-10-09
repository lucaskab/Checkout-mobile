import { expect, test } from "bun:test";
import {
	INSPECTION_FIX_MS,
	advanceInspection,
	advanceWindowSales,
	createInspectionRun,
	createWindowSales,
	getWindowSalePrice,
	openInspectionStop,
	scoreInspection,
	serveWindowRequest,
} from "@/services/event-interactions";

test("the inspector visits three stops spread over the event, each with time to fix", () => {
	const run = createInspectionRun(0, 150_000);
	expect(run.stops.length).toBe(3);
	expect(run.stops[0].at).toBe(8_000);
	expect(run.stops[2].at + INSPECTION_FIX_MS).toBeLessThanOrEqual(150_000);
});

test("a stop opens, then passes when its mishap is gone or fails when time runs out", () => {
	let run = createInspectionRun(0, 150_000);
	let step = advanceInspection(run, 10_000, []);
	expect(step.needsIncident.id).toBe("fiscal-1");
	run = openInspectionStop(step.run, "fiscal-1", { id: "i1", kind: "lampada", shelfId: "produce" }, 10_000);
	expect(run.stops[0].status).toBe("open");
	// Still broken: no new stop while one is open.
	step = advanceInspection(run, 30_000, [{ id: "i1" }]);
	expect(step.needsIncident).toBe(null);
	// Fixed.
	run = advanceInspection(run, 20_000, []).run;
	expect(run.stops[0].status).toBe("fixed");
	// The next one is left broken until its deadline.
	run = openInspectionStop(run, "fiscal-2", { id: "i2", kind: "etiqueta", shelfId: "drinks" }, 60_000);
	run = advanceInspection(run, 60_000 + INSPECTION_FIX_MS, [{ id: "i2" }]).run;
	expect(run.stops[1].status).toBe("failed");
});

test("all fixed is approved, one missed is a warning, more is a fine", () => {
	const run = createInspectionRun(0, 150_000);
	const withStatus = (...statuses) => ({ ...run, stops: run.stops.map((stop, i) => ({ ...stop, status: statuses[i] })) });
	expect(scoreInspection(withStatus("fixed", "fixed", "fixed"), 1000).grade).toBe("approved");
	expect(scoreInspection(withStatus("fixed", "fixed", "failed"), 1000).grade).toBe("warning");
	const fined = scoreInspection(withStatus("fixed", "failed", "waiting"), 1000);
	expect(fined.grade).toBe("fined");
	expect(fined.coins).toBe(-80);
});

test("drivers ask for drinks, at most two at once, and expire when nobody comes", () => {
	let state = createWindowSales(0);
	state = advanceWindowSales(state, 6_000, [21, 22], 150_000);
	expect(state.requests.length).toBe(1);
	expect([21, 22]).toContain(state.requests[0].productId);
	state = advanceWindowSales({ ...state, nextAt: 0 }, 7_000, [21], 150_000);
	state = advanceWindowSales({ ...state, nextAt: 0 }, 8_000, [21], 150_000);
	expect(state.requests.filter((request) => request.status === "waiting").length).toBe(2);
	const lanes = state.requests.map((request) => `${request.lane}:${request.slot}`);
	expect(new Set(lanes).size).toBe(lanes.length);
	state = advanceWindowSales({ ...state, nextAt: 10_000_000 }, 40_000, [21], 150_000);
	expect(state.requests.every((request) => request.status === "missed")).toBe(true);
	// Nothing to sell, nobody asks.
	expect(advanceWindowSales(createWindowSales(0), 10_000, [], 150_000).requests.length).toBe(0);
});

test("serving pays the shelf price plus a tip and counts toward the goal", () => {
	let state = advanceWindowSales(createWindowSales(0), 6_000, [21], 150_000);
	const served = serveWindowRequest(state, state.requests[0].id, 7_000);
	expect(served.state.served).toBe(1);
	expect(served.reachedGoal).toBe(false);
	expect(serveWindowRequest(served.state, state.requests[0].id, 7_500)).toBe(null);
	expect(getWindowSalePrice(10)).toEqual({ price: 10, tip: 3 });
	state = { ...served.state, served: 5 };
	state = advanceWindowSales({ ...state, nextAt: 0 }, 8_000, [21], 150_000);
	const last = state.requests.find((request) => request.status === "waiting");
	expect(serveWindowRequest(state, last.id, 8_100).reachedGoal).toBe(true);
});
