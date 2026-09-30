import { expect, test } from "bun:test";
import { createStoreIncidentsState, MAX_DIRT, spawnFloorDirt } from "./store-incidents.ts";
import {
	getRestockTripMs,
	getShiftPayroll,
	getStaffBoxKind,
	planStaffTasks,
	RESTOCK_TRIP_MS,
	takeFinishedStaffTasks,
} from "./staff-work.ts";

const clerk = {
	efficiency: 2,
	experience: 0,
	id: "stock_clerk-1",
	isWorking: true,
	level: 1,
	name: "Repositor 1",
	role: "stock_clerk",
	salary: 240,
};
const cleaner = { ...clerk, efficiency: 1, id: "cleaner-2", name: "Auxiliar 1", role: "cleaner", salary: 220 };
const slot = (slotId, stock, extra = {}) => ({
	available: 40,
	capacity: 20,
	category: "mercearia",
	productId: 1,
	productName: "Arroz",
	shelfId: slotId.split(":")[0],
	slotId,
	stock,
	...extra,
});
const base = { incidents: [], isOpen: true, nextTaskNumber: 1, now: 1_000, slots: [], storage: "depot", tasks: [] };

test("a stock clerk makes one trip for the emptiest slot, one box at a time", () => {
	const plan = planStaffTasks({
		...base,
		employees: [clerk],
		slots: [slot("grocery", 12), slot("snacks", 2, { productId: 2, productName: "Chocolate" })],
	});
	expect(plan.started).toHaveLength(1);
	const task = plan.started[0];
	expect(task.kind).toBe("restock");
	expect(task.slotId).toBe("snacks");
	expect(task.units).toBe(12);
	expect(task.endsAt - task.startedAt).toBe(RESTOCK_TRIP_MS.depot);
	// Busy until the trip ends: no second job.
	const again = planStaffTasks({
		...base,
		employees: [clerk],
		nextTaskNumber: plan.nextTaskNumber,
		slots: [slot("grocery", 0)],
		tasks: plan.tasks,
	});
	expect(again.started).toHaveLength(0);
});

test("full slots, empty storage and a closed market mean no trips", () => {
	expect(planStaffTasks({ ...base, employees: [clerk], slots: [slot("grocery", 18)] }).started).toHaveLength(0);
	expect(planStaffTasks({ ...base, employees: [clerk], slots: [slot("grocery", 0, { available: 0 })] }).started).toHaveLength(0);
	const closed = planStaffTasks({ ...base, employees: [clerk], isOpen: false, slots: [slot("grocery", 0)] });
	expect(closed.started).toHaveLength(0);
	expect(closed.tasks).toHaveLength(0);
});

test("the box follows the product and never overfills the slot", () => {
	const plan = planStaffTasks({
		...base,
		employees: [clerk],
		slots: [slot("fish", 3, { capacity: 20, category: "peixes" })],
	});
	expect(plan.started[0].box).toBe("peixe");
	expect(plan.started[0].units).toBe(6);
	expect(getStaffBoxKind("hortifruti")).toBe("hortifruti");
	expect(getStaffBoxKind("refrigerantes")).toBe("bebidas");
	const nearlyFull = planStaffTasks({ ...base, employees: [clerk], slots: [slot("grocery", 15)] });
	expect(nearlyFull.started[0].units).toBe(5);
});

test("cleaners take the oldest mess they can fix; clerks re-tag prices before restocking", () => {
	const incidents = [
		{ createdAt: 20, id: "i-lamp", kind: "lampada", shelfId: "dairy" },
		{ createdAt: 10, id: "i-dirt", kind: "sujeira", shelfId: "grocery" },
		{ createdAt: 5, id: "i-tag", kind: "etiqueta", shelfId: "snacks" },
		{ createdAt: 1, id: "i-freezer", kind: "freezer_sorvete", shelfId: "frozen" },
	];
	const plan = planStaffTasks({ ...base, employees: [clerk, cleaner], incidents, slots: [slot("grocery", 0)] });
	const byEmployee = Object.fromEntries(plan.started.map((task) => [task.employeeId, task]));
	expect(byEmployee["cleaner-2"].incidentId).toBe("i-dirt");
	expect(byEmployee["stock_clerk-1"].incidentId).toBe("i-tag");
	// A mess fixed by the player drops the job.
	const later = planStaffTasks({ ...base, employees: [clerk, cleaner], incidents: [incidents[0]], tasks: plan.tasks, nextTaskNumber: plan.nextTaskNumber });
	expect(later.tasks.some((task) => task.incidentId === "i-dirt")).toBe(false);
	expect(later.started.find((task) => task.employeeId === "cleaner-2").incidentId).toBe("i-lamp");
});

test("paused employees lose their job; finished jobs are handed back in order", () => {
	const plan = planStaffTasks({ ...base, employees: [clerk], slots: [slot("grocery", 0)] });
	const paused = planStaffTasks({ ...base, employees: [{ ...clerk, isWorking: false }], tasks: plan.tasks });
	expect(paused.tasks).toHaveLength(0);
	const { done, tasks } = takeFinishedStaffTasks(plan.tasks, plan.tasks[0].endsAt);
	expect(done).toHaveLength(1);
	expect(tasks).toHaveLength(0);
});

test("trained staff are faster, and the shift payroll counts only who worked", () => {
	expect(getRestockTripMs({ ...clerk, efficiency: 4 }, "warehouse")).toBeLessThan(
		getRestockTripMs(clerk, "warehouse"),
	);
	expect(getShiftPayroll([clerk, cleaner, { ...cleaner, id: "x", isWorking: false }])).toBe(460);
});

test("dirt piles up on its own pace, up to MAX_DIRT spots, only while open", () => {
	const shelves = ["grocery", "snacks", "dairy", "frozen"].map((shelfId, i) => ({
		category: "mercearia",
		price: 5,
		productId: i + 1,
		productName: "P" + i,
		shelfId,
		shelfName: shelfId,
		stock: 5,
	}));
	let state = createStoreIncidentsState();
	expect(spawnFloorDirt(state, shelves, 0, false).state.nextDirtAt).toBeNull();
	state = spawnFloorDirt(state, shelves, 0, true).state;
	for (let t = 1; t < 12; t++) state = spawnFloorDirt(state, shelves, t * 300_000, true).state;
	const dirt = state.active.filter((incident) => incident.kind === "sujeira");
	expect(dirt).toHaveLength(MAX_DIRT);
	expect(new Set(dirt.map((incident) => incident.shelfId)).size).toBe(MAX_DIRT);
	// Never on top of a spill.
	const spill = { ...dirt[0], id: "spill", kind: "derramado" };
	let withSpill = { ...createStoreIncidentsState(), active: [spill], nextDirtAt: 0 };
	for (let t = 1; t < 12; t++) withSpill = spawnFloorDirt(withSpill, shelves, t * 300_000, true).state;
	expect(withSpill.active.filter((i) => i.kind === "sujeira" && i.shelfId === spill.shelfId)).toHaveLength(0);
});
