import { expect, test } from "bun:test";
import {
	addDockDelivery,
	createReceivingState,
	getBoxUnits,
	getRemainingBoxes,
	getWarehouseZone,
	MAX_BOXES,
	nextStaffUnload,
	normalizeReceivingState,
	STAFF_UNLOAD_INTERVAL_MS,
	unloadDock,
} from "./receiving";

const t0 = 5_000_000;
const order = { id: "o1", productId: 5, quantity: 20 };
const milk = { name: "Leite", category: "laticinios" };

test("a delivered order waits at the dock once, in its stockroom zone", () => {
	let state = addDockDelivery(createReceivingState(), order, milk, t0);
	state = addDockDelivery(state, order, milk, t0 + 1);
	expect(state.dock.length).toBe(1);
	expect(state.dock[0].zone).toBe("refrigerados");
	expect(getWarehouseZone("refrigerantes")).toBe("bebidas");
	expect(getWarehouseZone("limpeza")).toBe("mercearia");
});

test("an order comes in a handful of boxes, never more than MAX_BOXES", () => {
	const state = addDockDelivery(createReceivingState(), order, milk, t0);
	expect(getRemainingBoxes(state.dock[0])).toEqual([3, 3, 3, 3, 3, 3, 2]);
	expect(getRemainingBoxes({ ...state.dock[0], quantity: 5 })).toEqual([1, 1, 1, 1, 1]);
	expect(getBoxUnits(500)).toBe(Math.ceil(500 / MAX_BOXES));
});

test("unloading moves what fits and clears the truck when empty", () => {
	let state = addDockDelivery(createReceivingState(), order, milk, t0);
	const id = state.dock[0].id;
	expect(unloadDock(state, id, 6, 0)).toBeNull();
	let step = unloadDock(state, id, 6, 4);
	expect(step.moved).toBe(4);
	state = step.state;
	step = unloadDock(state, id, 100, 100);
	expect(step.moved).toBe(16);
	expect(step.state.dock).toEqual([]);
	expect(step.state.unloadedUnits).toBe(20);
});

test("a stock clerk unloads a box on a steady clock, nobody means it waits", () => {
	let state = addDockDelivery(createReceivingState(), order, milk, t0);
	expect(nextStaffUnload(state, t0, 0).box).toBeNull();
	let step = nextStaffUnload(state, t0, 1);
	expect(step.box).toBeNull();
	state = step.state;
	step = nextStaffUnload(state, t0 + STAFF_UNLOAD_INTERVAL_MS, 1);
	expect(step.box).toEqual({ deliveryId: state.dock[0].id, units: 3 });
	expect(normalizeReceivingState(undefined).dock).toEqual([]);
});
