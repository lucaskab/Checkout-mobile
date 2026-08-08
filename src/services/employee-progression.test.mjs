import { expect, test } from "bun:test";
import { grantEmployeeExperience, trainEmployee } from "./employee-progression";

const employee = {
	efficiency: 1,
	experience: 0,
	id: "cashier-1",
	isWorking: true,
	level: 1,
	name: "Caixa 1",
	role: "cashier",
	salary: 180,
};

test("levels an employee after enough work experience", () => {
	const upgraded = grantEmployeeExperience(employee, 12);

	expect(upgraded.level).toBe(2);
	expect(upgraded.efficiency).toBe(2);
	expect(upgraded.experience).toBe(0);
});

test("training advances exactly one employee level", () => {
	const trained = trainEmployee({ ...employee, experience: 3 });

	expect(trained?.level).toBe(2);
	expect(trained?.experience).toBe(3);
});
