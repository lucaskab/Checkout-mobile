import type {
	MarketExpansionDefinition,
	MarketExpansionId,
} from "@/@types/market-expansion";

export const marketExpansions: MarketExpansionDefinition[] = [
	{
		coinCost: 4_000,
		description: "Abre espaço para hortifruti, ilhas e gôndolas adicionais.",
		id: "fresh-wing",
		name: "Ala de produtos frescos",
		requiredLevel: 4,
	},
	{
		coinCost: 18_000,
		description: "Libera área para caixas rápidos, carrinhos e promoções.",
		id: "service-wing",
		name: "Ala de atendimento",
		requiredLevel: 9,
	},
	{
		coinCost: 65_000,
		description: "Amplia a operação para estoque e logística de maior porte.",
		id: "stock-annex",
		name: "Anexo de estoque",
		requiredLevel: 16,
	},
	{
		coinCost: 240_000,
		description: "Cria a ala premium para equipamentos avançados e decoração.",
		id: "premium-hall",
		name: "Galeria premium",
		requiredLevel: 24,
	},
];

export function getMarketExpansion(id: MarketExpansionId) {
	return marketExpansions.find((expansion) => expansion.id === id) ?? null;
}

export function normalizeMarketExpansionIds(value: unknown): MarketExpansionId[] {
	if (!Array.isArray(value)) {
		return [];
	}

	const validIds = new Set(marketExpansions.map((expansion) => expansion.id));
	return Array.from(new Set(value.filter((id): id is MarketExpansionId => validIds.has(id))));
}
