import type { MarketEraId } from "@/@types/economy";
import type { StoreIncidentKind } from "./store-incident";

export type EmployeeRole = "cashier" | "stock_clerk" | "cleaner";

export type EmployeeDefinition = {
	efficiency: number;
	hireCost: number;
	id: EmployeeRole;
	level: number;
	/** Expansion from which this role can be hired (the stall has no room for staff at first). */
	requiredEra: MarketEraId;
	name: string;
	salary: number;
	description: string;
};

export type GameEmployee = {
	efficiency: number;
	experience: number;
	id: string;
	isWorking: boolean;
	level: number;
	name: string;
	role: EmployeeRole;
	salary: number;
};

// What a stock clerk carries from the storage: it decides the box drawn in the simulator.
export type StaffBoxKind =
	| "caixa"
	| "hortifruti"
	| "carne"
	| "peixe"
	| "padaria"
	| "bebidas"
	| "congelados"
	| "frios";

// One job an employee is doing right now. Restock: a trip through the rear door to the storage and
// back with one box for one shelf slot. Incident: walking to a mishap and fixing it (mop, bulb, tag).
// The effect lands when the task ends (endsAt); the simulator animates the trip in between.
export type StaffTask =
	| {
			box: StaffBoxKind;
			employeeId: string;
			endsAt: number;
			id: string;
			kind: "restock";
			productId: number;
			productName: string;
			shelfId: string;
			slotId: string;
			startedAt: number;
			units: number;
	  }
	| {
			employeeId: string;
			endsAt: number;
			id: string;
			incidentId: string;
			incidentKind: StoreIncidentKind;
			kind: "incident";
			shelfId: string;
			startedAt: number;
	  };

// Salaries are paid per shift (turno) when the market closes.
export type EmployeePayroll = {
	amount: number;
	dayNumber: number;
	paid: boolean;
	paidAt: number;
};

export type GameEmployeesState = {
	employees: GameEmployee[];
	lastPayroll: EmployeePayroll | null;
	nextHireNumber: number;
	nextPayrollAt: number;
	nextTaskNumber: number;
	tasks: StaffTask[];
	totalSalariesPaid: number;
};
