import type {
	MarketExpansionDefinition,
	MarketExpansionId,
} from "@/@types/market-expansion";

export const marketExpansions: MarketExpansionDefinition[] = [
	{
		coinCost: 4_000,
		diamondCost: 8,
		description:
			"Aumenta o mercado, constrói o depósito e abre espaço para a queijaria.",
		id: "fresh-wing",
		name: "Ala de produtos frescos",
		requiredLevel: 4,
	},
	{
		coinCost: 18_000,
		diamondCost: 24,
		description:
			"Amplia o salão, adiciona estacionamento e abre espaço para o açougue.",
		id: "service-wing",
		name: "Ala de atendimento",
		requiredLevel: 9,
	},
	{
		coinCost: 65_000,
		diamondCost: 60,
		description:
			"Expande o mercado com peixaria e um pátio de carga para entregas de maior porte.",
		id: "stock-annex",
		name: "Anexo de estoque",
		requiredLevel: 16,
	},
	{
		coinCost: 240_000,
		diamondCost: 140,
		description:
			"Cria o maior salão e uma praça de convivência com jardim e playground para os clientes.",
		id: "premium-hall",
		name: "Galeria premium",
		requiredLevel: 24,
	},
];

export function getMarketExpansion(id: MarketExpansionId) {
	return marketExpansions.find((expansion) => expansion.id === id) ?? null;
}

export function normalizeMarketExpansionIds(
	value: unknown,
): MarketExpansionId[] {
	if (!Array.isArray(value)) {
		return [];
	}

	const validIds = new Set(marketExpansions.map((expansion) => expansion.id));
	return Array.from(
		new Set(value.filter((id): id is MarketExpansionId => validIds.has(id))),
	);
}
