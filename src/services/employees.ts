import type { EmployeeRole, GameEmployeesState } from "@/@types/employee";

export type EmployeeEffects = {
	customerArrivalMultiplier: number;
	restockAmount: number;
	storeReputationBonus: number;
};

export const EMPLOYEE_PAYROLL_INTERVAL_MS = 20 * 60_000;

export function getEmployeeEffects(employees: GameEmployeesState): EmployeeEffects {
	const activeEmployees = employees.employees.filter((employee) => employee.isWorking);
	const cashierEfficiency = getRoleEfficiency(activeEmployees, "cashier");
	const stockEfficiency = getRoleEfficiency(activeEmployees, "stock_clerk");
	const cleanerEfficiency = getRoleEfficiency(activeEmployees, "cleaner");

	return {
		customerArrivalMultiplier: Math.max(0.55, 1 - cashierEfficiency * 0.08),
		restockAmount: stockEfficiency * 2,
		storeReputationBonus: cleanerEfficiency * 5,
	};
}

export function getEmployeePayrollCost(employees: GameEmployeesState) {
	return employees.employees
		.filter((employee) => employee.isWorking)
		.reduce((total, employee) => total + employee.salary, 0);
}

function getRoleEfficiency(
	employees: GameEmployeesState["employees"],
	role: EmployeeRole,
) {
	return employees
		.filter((employee) => employee.role === role)
		.reduce((total, employee) => total + employee.efficiency, 0);
}
