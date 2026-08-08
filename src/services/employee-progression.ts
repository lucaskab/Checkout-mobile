import type { GameEmployee } from "@/@types/employee";

export const EMPLOYEE_MAX_LEVEL = 5;

export function getEmployeeExperienceForNextLevel(level: number) {
	return Math.max(1, level) * 12;
}

export function getEmployeeTrainingCost(employee: GameEmployee) {
	return 350 * employee.level;
}

export function grantEmployeeExperience(
	employee: GameEmployee,
	experience: number,
): GameEmployee {
	if (experience <= 0 || employee.level >= EMPLOYEE_MAX_LEVEL) {
		return employee;
	}

	let nextExperience = employee.experience + experience;
	let nextLevel = employee.level;
	let nextEfficiency = employee.efficiency;

	while (
		nextLevel < EMPLOYEE_MAX_LEVEL &&
		nextExperience >= getEmployeeExperienceForNextLevel(nextLevel)
	) {
		nextExperience -= getEmployeeExperienceForNextLevel(nextLevel);
		nextLevel += 1;
		nextEfficiency += 1;
	}

	return {
		...employee,
		efficiency: nextEfficiency,
		experience: nextExperience,
		level: nextLevel,
	};
}

export function trainEmployee(employee: GameEmployee): GameEmployee | null {
	if (employee.level >= EMPLOYEE_MAX_LEVEL) {
		return null;
	}

	return grantEmployeeExperience(
		employee,
		getEmployeeExperienceForNextLevel(employee.level),
	);
}
