import type { EmployeeDefinition, EmployeeRole } from "@/@types/employee";

export const employeeDefinitions: EmployeeDefinition[] = [
	{
		description: "Acelera o atendimento e reduz a espera na fila.",
		efficiency: 1,
		hireCost: 1_500,
		id: "cashier",
		level: 2,
		name: "Operador de caixa",
		salary: 180,
	},
	{
		description: "Reabastece automaticamente a gôndola mais vazia após cada venda.",
		efficiency: 2,
		hireCost: 3_500,
		id: "stock_clerk",
		level: 4,
		name: "Repositor",
		salary: 240,
	},
	{
		description: "Melhora a reputação e a conversão dos clientes do mercado.",
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
