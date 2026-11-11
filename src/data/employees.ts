import type { MarketEraId } from "@/@types/economy";
import type { EmployeeDefinition, EmployeeRole } from "@/@types/employee";
import { getMarketEra } from "@/data/economy";

export const employeeDefinitions: EmployeeDefinition[] = [
	{
		description: "Assume um caixa: passa as compras e recebe o pagamento sozinho. Cada caixa precisa do seu operador; sem nenhum, quem atende é você.",
		efficiency: 1,
		hireCost: 1_500,
		id: "cashier",
		level: 9,
		// The first person working with you: from the contêiner on.
		requiredEra: "conteiner",
		name: "Operador de caixa",
		salary: 180,
	},
	{
		description: "Sai pela porta dos fundos, busca uma caixa no depósito e repõe gôndolas e setores, uma viagem por vez.",
		efficiency: 2,
		hireCost: 3_500,
		id: "stock_clerk",
		level: 11,
		requiredEra: "spati",
		name: "Repositor",
		salary: 240,
	},
	{
		description: "Varre a sujeira, seca o que derramou e troca lâmpadas queimadas. Loja limpa: +5 de reputação (+5% de clientes).",
		efficiency: 1,
		hireCost: 5_000,
		id: "cleaner",
		level: 19,
		requiredEra: "mercadinho",
		name: "Auxiliar de limpeza",
		salary: 220,
	},
	{
		// "Ladrão e segurança" (src/services/store-security.ts): catches thieves alone and makes them come less often.
		description: "Fica de olho na porta: pega ladrões sozinho e espanta metade deles.",
		efficiency: 1,
		hireCost: 6_000,
		id: "security",
		level: 15,
		requiredEra: "minimercado",
		name: "Segurança",
		salary: 260,
	},
];

/** Has the market grown enough to hire this role? */
export function isEmployeeEraReached(definition: EmployeeDefinition, eraId: MarketEraId) {
	return getMarketEra(eraId).index >= getMarketEra(definition.requiredEra).index;
}

export function getEmployeeDefinition(role: EmployeeRole) {
	return employeeDefinitions.find((employee) => employee.id === role) ?? null;
}
