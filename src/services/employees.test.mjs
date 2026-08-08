import { expect, test } from "bun:test";
import { getEmployeeEffects } from "./employees.ts";

test("applies only active employee effects", () => {
	const effects = getEmployeeEffects({
		employees: [
			{
				efficiency: 1,
				id: "cashier-1",
				isWorking: true,
				name: "Operador de caixa 1",
				role: "cashier",
				salary: 180,
			},
			{
				efficiency: 2,
				id: "stock-clerk-2",
				isWorking: true,
				name: "Repositor 1",
				role: "stock_clerk",
				salary: 240,
			},
			{
				efficiency: 1,
				id: "cleaner-3",
				isWorking: false,
				name: "Auxiliar de limpeza 1",
				role: "cleaner",
				salary: 220,
			},
		],
		nextHireNumber: 4,
	});

	expect(effects).toEqual({
		customerArrivalMultiplier: 0.92,
		restockAmount: 4,
		storeReputationBonus: 0,
	});
});
