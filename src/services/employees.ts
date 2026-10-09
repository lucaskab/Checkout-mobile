import type { EmployeeRole, GameEmployeesState } from "@/@types/employee";
import { TURN_SHARE } from "@/data/economy";

export type EmployeeEffects = {
	customerArrivalMultiplier: number;
	restockAmount: number;
	storeReputationBonus: number;
};

export const EMPLOYEE_PAYROLL_INTERVAL_MS = 20 * 60_000;

export function getEmployeeEffects(employees: GameEmployeesState): EmployeeEffects {
	const activeEmployees = employees.employees.filter((employee) => employee.isWorking);
	const stockEfficiency = getRoleEfficiency(activeEmployees, "stock_clerk");
	const cleanerEfficiency = getRoleEfficiency(activeEmployees, "cleaner");

	return {
		// The cashier rings customers up (processCheckoutCounter); it does not change how many come in.
		customerArrivalMultiplier: 1,
		restockAmount: stockEfficiency * 2,
		storeReputationBonus: cleanerEfficiency * 5,
	};
}

/** Salaries are set per 10-minute turn (BALANCE_TURN_MINUTES): a shorter turn pays its share. */
export function getShiftSalary(salary: number) {
	return Math.max(1, Math.round(salary * TURN_SHARE));
}

export function getEmployeePayrollCost(employees: GameEmployeesState) {
	return employees.employees
		.filter((employee) => employee.isWorking)
		.reduce((total, employee) => total + getShiftSalary(employee.salary), 0);
}

function getRoleEfficiency(
	employees: GameEmployeesState["employees"],
	role: EmployeeRole,
) {
	return employees
		.filter((employee) => employee.role === role)
		.reduce((total, employee) => total + employee.efficiency, 0);
}
