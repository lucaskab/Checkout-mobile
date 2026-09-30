import type {
	EmployeeRole,
	GameEmployee,
	StaffBoxKind,
	StaffTask,
} from "@/@types/employee";
import type {
	StoreIncident,
	StoreIncidentKind,
} from "@/@types/store-incident";
import { getEmployeeDefinition } from "@/data/employees";
import { incidentStaff } from "./store-incidents";

// Shared rules for what the stock clerks and cleaners do on their own (System, mobile simulator and
// desktop). Nothing happens instantly: every job is a task with a start and an end, the effect lands
// at the end, and the simulator animates the walk in between (through the rear roller door to the
// storage and back, or across the shop to a mess on the floor).

// Where the boxes come from, following the expansions bought: parcels left at the rear doorstep, the
// small depot out back or the central warehouse across the yard.
export type StaffStorageKind = "doorstep" | "depot" | "warehouse";

// One full restock trip: rear door, storage, pick a box, back to the shelf, fill it.
export const RESTOCK_TRIP_MS: Record<StaffStorageKind, number> = {
	doorstep: 26_000,
	depot: 40_000,
	warehouse: 54_000,
};

// Walking to the mess and dealing with it (mop, ladder and bulb, new price tag).
export const INCIDENT_TASK_MS: Record<StoreIncidentKind, number> = {
	derramado: 16_000,
	etiqueta: 11_000,
	freezer_sorvete: 0,
	geladeira_bebidas: 0,
	lampada: 18_000,
	sujeira: 13_000,
};

// Slots below this fill (stock plus boxes already on the way) get a trip.
export const RESTOCK_FILL_TARGET = 0.8;

// Units that fit in one box of each kind, for a stock clerk at the base efficiency.
export const staffBoxUnits: Record<StaffBoxKind, number> = {
	bebidas: 12,
	caixa: 12,
	carne: 8,
	congelados: 10,
	frios: 10,
	hortifruti: 10,
	padaria: 12,
	peixe: 6,
};

export function getStaffBoxKind(category: string): StaffBoxKind {
	switch (category) {
		case "hortifruti":
		case "organicos":
			return "hortifruti";
		case "carnes":
			return "carne";
		case "peixes":
			return "peixe";
		case "padaria":
			return "padaria";
		case "bebidas":
		case "refrigerantes":
		case "aguas":
		case "energeticos":
			return "bebidas";
		case "congelados":
			return "congelados";
		case "laticinios":
		case "frios":
		case "queijos":
			return "frios";
		default:
			return "caixa";
	}
}

// Trained employees walk faster: 12% per efficiency point above the role's starting one.
export function getStaffSpeed(employee: Pick<GameEmployee, "efficiency" | "role">) {
	const base = getEmployeeDefinition(employee.role)?.efficiency ?? 1;
	return Math.min(1.6, Math.max(0.7, 1 + (employee.efficiency - base) * 0.12));
}

export function getRestockTripMs(
	employee: Pick<GameEmployee, "efficiency" | "role">,
	storage: StaffStorageKind,
) {
	return Math.round(RESTOCK_TRIP_MS[storage] / getStaffSpeed(employee));
}

export function getIncidentTaskMs(
	employee: Pick<GameEmployee, "efficiency" | "role">,
	kind: StoreIncidentKind,
) {
	return Math.round(INCIDENT_TASK_MS[kind] / getStaffSpeed(employee));
}

export function getBoxUnits(
	box: StaffBoxKind,
	employee: Pick<GameEmployee, "efficiency" | "role">,
	restockMultiplier = 1,
) {
	const base = getEmployeeDefinition(employee.role)?.efficiency ?? 1;
	const extra = Math.max(0, employee.efficiency - base) * 2;
	return Math.max(1, Math.round((staffBoxUnits[box] + extra) * restockMultiplier));
}

// A shelf slot the stock clerks may refill.
export type RestockCandidate = {
	available: number;
	capacity: number;
	category: string;
	productId: number;
	productName: string;
	shelfId: string;
	slotId: string;
	stock: number;
};

export type StaffPlanInput = {
	employees: GameEmployee[];
	incidents: StoreIncident[];
	isOpen: boolean;
	nextTaskNumber: number;
	now: number;
	restockMultiplier?: number;
	slots: RestockCandidate[];
	storage: StaffStorageKind;
	tasks: StaffTask[];
};

export type StaffPlan = {
	nextTaskNumber: number;
	started: StaffTask[];
	tasks: StaffTask[];
};

const staffRoles: EmployeeRole[] = ["stock_clerk", "cleaner"];

// Hands a new job to every working stock clerk or cleaner who has none. Jobs of employees who stopped
// working, and fixes the player already did by hand, are dropped. A closed market has no jobs.
export function planStaffTasks(input: StaffPlanInput): StaffPlan {
	if (!input.isOpen)
		return { nextTaskNumber: input.nextTaskNumber, started: [], tasks: [] };
	const working = new Map(
		input.employees
			.filter((employee) => employee.isWorking && staffRoles.includes(employee.role))
			.map((employee) => [employee.id, employee]),
	);
	const activeIncidents = new Set(input.incidents.map((incident) => incident.id));
	const tasks = input.tasks.filter(
		(task) =>
			working.has(task.employeeId) &&
			(task.kind !== "incident" || activeIncidents.has(task.incidentId)),
	);
	const started: StaffTask[] = [];
	let nextTaskNumber = input.nextTaskNumber;
	const busy = new Set(tasks.map((task) => task.employeeId));
	const takenIncidents = new Set(
		tasks.flatMap((task) => (task.kind === "incident" ? [task.incidentId] : [])),
	);
	const pending = new Map<string, number>();
	for (const task of tasks)
		if (task.kind === "restock")
			pending.set(task.slotId, (pending.get(task.slotId) ?? 0) + task.units);
	const incidentsByAge = [...input.incidents].sort((a, b) => a.createdAt - b.createdAt);

	for (const employee of [...working.values()].sort((a, b) => a.id.localeCompare(b.id))) {
		if (busy.has(employee.id)) continue;
		const incident = incidentsByAge.find(
			(item) => incidentStaff[item.kind] === employee.role && !takenIncidents.has(item.id),
		);
		if (incident) {
			const task: StaffTask = {
				employeeId: employee.id,
				endsAt: input.now + getIncidentTaskMs(employee, incident.kind),
				id: `tarefa-${nextTaskNumber}`,
				incidentId: incident.id,
				incidentKind: incident.kind,
				kind: "incident",
				shelfId: incident.shelfId,
				startedAt: input.now,
			};
			nextTaskNumber += 1;
			takenIncidents.add(incident.id);
			tasks.push(task);
			started.push(task);
			continue;
		}
		if (employee.role !== "stock_clerk") continue;
		const slot = input.slots
			.filter((candidate) => {
				const onTheWay = pending.get(candidate.slotId) ?? 0;
				return (
					candidate.productId > 0 &&
					candidate.capacity > 0 &&
					candidate.available > onTheWay &&
					!tasks.some((task) => task.kind === "restock" && task.slotId === candidate.slotId) &&
					(candidate.stock + onTheWay) / candidate.capacity < RESTOCK_FILL_TARGET
				);
			})
			.sort(
				(a, b) =>
					a.stock / a.capacity - b.stock / b.capacity || a.slotId.localeCompare(b.slotId),
			)[0];
		if (!slot) continue;
		const box = getStaffBoxKind(slot.category);
		const units = Math.min(
			getBoxUnits(box, employee, input.restockMultiplier ?? 1),
			slot.capacity - slot.stock,
			slot.available,
		);
		if (units <= 0) continue;
		const task: StaffTask = {
			box,
			employeeId: employee.id,
			endsAt: input.now + getRestockTripMs(employee, input.storage),
			id: `tarefa-${nextTaskNumber}`,
			kind: "restock",
			productId: slot.productId,
			productName: slot.productName,
			shelfId: slot.shelfId,
			slotId: slot.slotId,
			startedAt: input.now,
			units,
		};
		nextTaskNumber += 1;
		pending.set(slot.slotId, (pending.get(slot.slotId) ?? 0) + units);
		tasks.push(task);
		started.push(task);
	}
	return { nextTaskNumber, started, tasks };
}

// Tasks whose time is up, oldest first, and the ones still running.
export function takeFinishedStaffTasks(tasks: StaffTask[], now: number) {
	const done = tasks.filter((task) => task.endsAt <= now).sort((a, b) => a.endsAt - b.endsAt);
	return { done, tasks: tasks.filter((task) => task.endsAt > now) };
}

// Salary of everyone who worked the shift that just closed.
export function getShiftPayroll(employees: GameEmployee[]) {
	return employees
		.filter((employee) => employee.isWorking)
		.reduce((total, employee) => total + employee.salary, 0);
}

export function getStaffStorageKind(layout: {
	storage: boolean;
	storageLarge: boolean;
}): StaffStorageKind {
	return layout.storageLarge ? "warehouse" : layout.storage ? "depot" : "doorstep";
}
