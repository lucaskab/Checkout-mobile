export type EmployeeRole = "cashier" | "stock_clerk" | "cleaner";

export type EmployeeDefinition = {
	efficiency: number;
	hireCost: number;
	id: EmployeeRole;
	level: number;
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

export type GameEmployeesState = {
	employees: GameEmployee[];
	nextHireNumber: number;
	nextPayrollAt: number;
	totalSalariesPaid: number;
};
