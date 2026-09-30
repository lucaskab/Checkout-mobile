import type {
	ProductionRecipe,
	ProductionSector,
	ProductionSectorId,
} from "@/@types/production";

export const productionSectors: ProductionSector[] = [
	{
		description:
			"Fornos quentes, fornadas rápidas e o melhor cheiro do mercado.",

		id: "padaria",
		name: "Padaria",
		requiredLevel: 2,
		slotCount: 2,
		subtitle: "Massas & confeitaria",
	},
	{
		description: "Transforme leite fresco em queijos artesanais de alto valor.",

		id: "queijaria",
		name: "Queijaria",
		requiredLevel: 6,
		slotCount: 2,
		subtitle: "Laticínios especiais",
	},
	{
		description:
			"Prepare cortes nobres e combinações premium para os clientes exigentes.",

		id: "acougue",
		name: "Açougue",
		requiredLevel: 10,
		slotCount: 3,
		subtitle: "Cortes & defumados",
	},
	{
		description:
			"Prepare bebidas geladas e combinações exclusivas no refrigerador.",
		id: "bebidas",
		name: "Bebidas",
		requiredLevel: 12,
		slotCount: 2,
		subtitle: "Sucos & bebidas geladas",
	},
	{
		description:
			"Uma bancada gelada para receitas frescas e pratos de alto prestígio.",

		id: "peixaria",
		name: "Peixaria",
		requiredLevel: 16,
		slotCount: 3,
		subtitle: "Pescados & frutos do mar",
	},
	{
		description:
			"Produza sorvetes artesanais e sobremesas para a vitrine fria.",
		id: "sorvetes",
		name: "Sorvetes",
		requiredLevel: 24,
		slotCount: 3,
		subtitle: "Sorvetes & sobremesas",
	},
	{
		description:
			"Uma adega climatizada para vinhos da casa, sangrias e kits de harmonização.",
		id: "adega",
		name: "Adega",
		requiredLevel: 20,
		slotCount: 3,
		subtitle: "Vinhos & harmonizações",
	},
];

export const productionRecipes: ProductionRecipe[] = [
	{
		durationMs: 45_000,
		id: "baguete-rustica",
		ingredients: [
			{ productId: 43, quantity: 2 },
			{ productId: 7, quantity: 1 },
		],
		outputProductId: 101,
		outputQuantity: 4,
		requiredLevel: 2,
		sectorId: "padaria",
	},
	{
		durationMs: 90_000,
		id: "croissant-premium",
		ingredients: [
			{ productId: 43, quantity: 2 },
			{ productId: 7, quantity: 1 },
			{ productId: 5, quantity: 1 },
		],
		outputProductId: 102,
		outputQuantity: 3,
		requiredLevel: 3,
		sectorId: "padaria",
	},
	{
		durationMs: 180_000,
		id: "bolo-de-vitrine",
		ingredients: [
			{ productId: 43, quantity: 2 },
			{ productId: 5, quantity: 2 },
			{ productId: 7, quantity: 1 },
			{ productId: 24, quantity: 1 },
		],
		outputProductId: 103,
		outputQuantity: 2,
		requiredLevel: 6,
		sectorId: "padaria",
	},
	{
		durationMs: 90_000,
		id: "queijo-minas",
		ingredients: [{ productId: 5, quantity: 3 }],
		outputProductId: 104,
		outputQuantity: 3,
		requiredLevel: 6,
		sectorId: "queijaria",
	},
	{
		durationMs: 240_000,
		id: "brie-maturado",
		ingredients: [
			{ productId: 5, quantity: 2 },
			{ productId: 6, quantity: 1 },
		],
		outputProductId: 105,
		outputQuantity: 2,
		requiredLevel: 8,
		sectorId: "queijaria",
	},
	{
		durationMs: 480_000,
		id: "tabua-de-queijos",
		ingredients: [
			{ productId: 6, quantity: 3 },
			{ productId: 31, quantity: 1 },
		],
		outputProductId: 106,
		outputQuantity: 2,
		requiredLevel: 13,
		sectorId: "queijaria",
	},
	{
		durationMs: 120_000,
		id: "hamburguer-artesanal",
		ingredients: [
			{ productId: 27, quantity: 1 },
			{ productId: 1, quantity: 2 },
		],
		outputProductId: 107,
		outputQuantity: 4,
		requiredLevel: 10,
		sectorId: "acougue",
	},
	{
		durationMs: 300_000,
		id: "corte-dry-aged",
		ingredients: [
			{ productId: 27, quantity: 2 },
			{ productId: 28, quantity: 1 },
		],
		outputProductId: 108,
		outputQuantity: 2,
		requiredLevel: 12,
		sectorId: "acougue",
	},
	{
		durationMs: 600_000,
		id: "kit-churrasco",
		ingredients: [
			{ productId: 27, quantity: 3 },
			{ productId: 31, quantity: 1 },
			{ productId: 1, quantity: 2 },
		],
		outputProductId: 109,
		outputQuantity: 3,
		requiredLevel: 16,
		sectorId: "acougue",
	},
	{
		durationMs: 150_000,
		id: "file-de-peixe",
		ingredients: [
			{ productId: 44, quantity: 2 },
			{ productId: 21, quantity: 1 },
		],
		outputProductId: 110,
		outputQuantity: 4,
		requiredLevel: 16,
		sectorId: "peixaria",
	},
	{
		durationMs: 360_000,
		id: "sushi-especial",
		ingredients: [
			{ productId: 44, quantity: 2 },
			{ productId: 3, quantity: 1 },
		],
		outputProductId: 111,
		outputQuantity: 3,
		requiredLevel: 18,
		sectorId: "peixaria",
	},
	{
		durationMs: 720_000,
		id: "barco-de-frutos-do-mar",
		ingredients: [
			{ productId: 44, quantity: 3 },
			{ productId: 45, quantity: 2 },
			{ productId: 31, quantity: 1 },
		],
		outputProductId: 112,
		outputQuantity: 3,
		requiredLevel: 22,
		sectorId: "peixaria",
	},
	{
		durationMs: 90_000,
		id: "suco-gelado",
		ingredients: [
			{ productId: 13, quantity: 2 },
			{ productId: 21, quantity: 1 },
		],
		outputProductId: 113,
		outputQuantity: 4,
		requiredLevel: 12,
		sectorId: "bebidas",
	},
	{
		durationMs: 180_000,
		id: "cha-gelado",
		ingredients: [
			{ productId: 16, quantity: 2 },
			{ productId: 21, quantity: 1 },
		],
		outputProductId: 114,
		outputQuantity: 4,
		requiredLevel: 15,
		sectorId: "bebidas",
	},
	{
		durationMs: 300_000,
		id: "vitamina-cremosa",
		ingredients: [
			{ productId: 5, quantity: 2 },
			{ productId: 8, quantity: 1 },
			{ productId: 13, quantity: 1 },
		],
		outputProductId: 115,
		outputQuantity: 3,
		requiredLevel: 18,
		sectorId: "bebidas",
	},
	{
		durationMs: 180_000,
		id: "sorvete-creme",
		ingredients: [
			{ productId: 5, quantity: 2 },
			{ productId: 8, quantity: 1 },
		],
		outputProductId: 116,
		outputQuantity: 4,
		requiredLevel: 24,
		sectorId: "sorvetes",
	},
	{
		durationMs: 360_000,
		id: "sundae-chocolate",
		ingredients: [
			{ productId: 116, quantity: 2 },
			{ productId: 24, quantity: 1 },
		],
		outputProductId: 117,
		outputQuantity: 3,
		requiredLevel: 26,
		sectorId: "sorvetes",
	},
	{
		durationMs: 600_000,
		id: "pote-sorvete-familia",
		ingredients: [
			{ productId: 116, quantity: 2 },
			{ productId: 113, quantity: 1 },
		],
		outputProductId: 118,
		outputQuantity: 3,
		requiredLevel: 28,
		sectorId: "sorvetes",
	},
	{
		durationMs: 240_000,
		id: "vinho-da-casa",
		ingredients: [{ productId: 13, quantity: 3 }],
		outputProductId: 119,
		outputQuantity: 3,
		requiredLevel: 20,
		sectorId: "adega",
	},
	{
		durationMs: 420_000,
		id: "sangria-da-casa",
		ingredients: [
			{ productId: 119, quantity: 2 },
			{ productId: 13, quantity: 1 },
		],
		outputProductId: 120,
		outputQuantity: 3,
		requiredLevel: 21,
		sectorId: "adega",
	},
	{
		durationMs: 780_000,
		id: "kit-harmonizacao",
		ingredients: [
			{ productId: 31, quantity: 1 },
			{ productId: 6, quantity: 2 },
			{ productId: 32, quantity: 1 },
		],
		outputProductId: 121,
		outputQuantity: 2,
		requiredLevel: 23,
		sectorId: "adega",
	},
];

export function getProductionSector(sectorId: string) {
	return productionSectors.find((sector) => sector.id === sectorId);
}

export function getSectorRecipes(sectorId: ProductionSectorId) {
	return productionRecipes.filter((recipe) => recipe.sectorId === sectorId);
}
