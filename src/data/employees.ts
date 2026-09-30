import type { EmployeeDefinition, EmployeeRole } from "@/@types/employee";

export const employeeDefinitions: EmployeeDefinition[] = [
	{
		description: "Assume o caixa: passa as compras e recebe o pagamento sozinho. Sem ele, quem atende é você.",
		efficiency: 1,
		hireCost: 1_500,
		id: "cashier",
		level: 2,
		name: "Operador de caixa",
		salary: 180,
	},
	{
		description: "Sai pela porta dos fundos, busca uma caixa no depósito e repõe gôndolas e setores, uma viagem por vez.",
		efficiency: 2,
		hireCost: 3_500,
		id: "stock_clerk",
		level: 4,
		name: "Repositor",
		salary: 240,
	},
	{
		description: "Varre a sujeira, seca o que derramou e troca lâmpadas queimadas assim que aparecem.",
		efficiency: 1,
		hireCost: 5_000,
		id: "cleaner",
		level: 6,
		name: "Auxiliar de limpeza",
		salary: 220,
	},
];

export function getEmployeeDefinition(role: EmployeeRole) {
	return employeeDefinitions.find((employee) => employee.id === role) ?? null;
}
