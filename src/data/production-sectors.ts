import type {
	ProductionRecipe,
	ProductionSector,
	ProductionSectorId,
} from "@/@types/production";

const MINUTE = 60_000;

// The market's own kitchens. Each sector makes goods out of products bought from the suppliers and
// sells them at its own counter (src/data/shelf-types.ts sectorCounters), like the bakery, the butcher's
// and the fishmonger's of a real supermarket. They open with the expansions that have room for them:
// the bakery with the mercadinho, cheese, butcher's and juices with the supermarket, fish, ice cream
// and wine with the hypermarket.

export const productionSectors: ProductionSector[] = [
	{
		description: "Fornos quentes, fornadas rápidas e o melhor cheiro do mercado.",
		id: "padaria",
		name: "Padaria",
		eraId: "mercadinho",
		requiredLevel: 19,
		slotCount: 2,
		subtitle: "Pães & confeitaria",
	},
	{
		description: "Transforme leite fresco em queijos artesanais de alto valor.",
		id: "queijaria",
		name: "Queijaria",
		eraId: "supermercado",
		requiredLevel: 25,
		slotCount: 2,
		subtitle: "Queijos & frios",
	},
	{
		description: "Prepare cortes nobres e combinações premium para os clientes exigentes.",
		id: "acougue",
		name: "Açougue",
		eraId: "supermercado",
		requiredLevel: 25,
		slotCount: 3,
		subtitle: "Cortes & churrasco",
	},
	{
		description: "Prepare sucos, chás gelados e vitaminas no balcão de bebidas.",
		id: "bebidas",
		name: "Bebidas",
		eraId: "supermercado",
		requiredLevel: 25,
		slotCount: 2,
		subtitle: "Sucos & bebidas geladas",
	},
	{
		description: "Uma bancada gelada para peixes frescos, sushi e frutos do mar.",
		id: "peixaria",
		name: "Peixaria",
		eraId: "hipermercado",
		requiredLevel: 33,
		slotCount: 3,
		subtitle: "Pescados & frutos do mar",
	},
	{
		description: "Produza sorvetes artesanais e sobremesas para a vitrine fria.",
		id: "sorvetes",
		name: "Sorvetes",
		eraId: "hipermercado",
		requiredLevel: 33,
		slotCount: 3,
		subtitle: "Sorvetes & sobremesas",
	},
	{
		description: "Uma adega climatizada para vinhos da casa, sangrias e kits de harmonização.",
		id: "adega",
		name: "Adega",
		eraId: "hipermercado",
		requiredLevel: 33,
		slotCount: 3,
		subtitle: "Vinhos & harmonizações",
	},
];

// Generated with the catalog (scripts/economy/catalog.py).
export const productionRecipes: ProductionRecipe[] = [
	{ id: "baguete-rustica", sectorId: "padaria", outputProductId: 101, outputQuantity: 4, durationMs: 1 * MINUTE, requiredLevel: 19, ingredients: [{ productId: 43, quantity: 2 }, { productId: 7, quantity: 1 }] },
	{ id: "croissant-premium", sectorId: "padaria", outputProductId: 102, outputQuantity: 3, durationMs: 2 * MINUTE, requiredLevel: 19, ingredients: [{ productId: 43, quantity: 2 }, { productId: 7, quantity: 1 }, { productId: 5, quantity: 1 }] },
	{ id: "bolo-de-vitrine", sectorId: "padaria", outputProductId: 103, outputQuantity: 2, durationMs: 4 * MINUTE, requiredLevel: 20, ingredients: [{ productId: 43, quantity: 2 }, { productId: 5, quantity: 2 }, { productId: 50, quantity: 1 }, { productId: 24, quantity: 1 }] },
	{ id: "queijo-minas", sectorId: "queijaria", outputProductId: 104, outputQuantity: 2, durationMs: 3 * MINUTE, requiredLevel: 25, ingredients: [{ productId: 5, quantity: 4 }] },
	{ id: "brie-maturado", sectorId: "queijaria", outputProductId: 105, outputQuantity: 2, durationMs: 6 * MINUTE, requiredLevel: 26, ingredients: [{ productId: 5, quantity: 3 }, { productId: 6, quantity: 1 }] },
	{ id: "tabua-de-queijos", sectorId: "queijaria", outputProductId: 106, outputQuantity: 2, durationMs: 12 * MINUTE, requiredLevel: 33, ingredients: [{ productId: 105, quantity: 1 }, { productId: 104, quantity: 2 }, { productId: 31, quantity: 1 }] },
	{ id: "hamburguer-artesanal", sectorId: "acougue", outputProductId: 107, outputQuantity: 4, durationMs: 3 * MINUTE, requiredLevel: 26, ingredients: [{ productId: 27, quantity: 1 }, { productId: 1, quantity: 2 }] },
	{ id: "corte-dry-aged", sectorId: "acougue", outputProductId: 108, outputQuantity: 2, durationMs: 8 * MINUTE, requiredLevel: 33, ingredients: [{ productId: 27, quantity: 3 }] },
	{ id: "kit-churrasco", sectorId: "acougue", outputProductId: 109, outputQuantity: 3, durationMs: 15 * MINUTE, requiredLevel: 34, ingredients: [{ productId: 27, quantity: 2 }, { productId: 57, quantity: 2 }, { productId: 60, quantity: 2 }] },
	{ id: "file-de-peixe", sectorId: "peixaria", outputProductId: 110, outputQuantity: 4, durationMs: 4 * MINUTE, requiredLevel: 34, ingredients: [{ productId: 44, quantity: 2 }] },
	{ id: "sushi-especial", sectorId: "peixaria", outputProductId: 111, outputQuantity: 3, durationMs: 8 * MINUTE, requiredLevel: 34, ingredients: [{ productId: 44, quantity: 2 }, { productId: 51, quantity: 1 }] },
	{ id: "barco-de-frutos-do-mar", sectorId: "peixaria", outputProductId: 112, outputQuantity: 3, durationMs: 18 * MINUTE, requiredLevel: 45, ingredients: [{ productId: 44, quantity: 3 }, { productId: 45, quantity: 2 }, { productId: 51, quantity: 1 }] },
	{ id: "suco-gelado", sectorId: "bebidas", outputProductId: 113, outputQuantity: 3, durationMs: 2 * MINUTE, requiredLevel: 26, ingredients: [{ productId: 49, quantity: 2 }, { productId: 46, quantity: 2 }, { productId: 21, quantity: 1 }] },
	{ id: "cha-gelado", sectorId: "bebidas", outputProductId: 114, outputQuantity: 3, durationMs: 4 * MINUTE, requiredLevel: 26, ingredients: [{ productId: 16, quantity: 1 }, { productId: 53, quantity: 1 }, { productId: 21, quantity: 2 }] },
	{ id: "vitamina-cremosa", sectorId: "bebidas", outputProductId: 115, outputQuantity: 3, durationMs: 6 * MINUTE, requiredLevel: 34, ingredients: [{ productId: 5, quantity: 2 }, { productId: 8, quantity: 1 }, { productId: 46, quantity: 2 }] },
	{ id: "sorvete-creme", sectorId: "sorvetes", outputProductId: 116, outputQuantity: 3, durationMs: 5 * MINUTE, requiredLevel: 35, ingredients: [{ productId: 5, quantity: 2 }, { productId: 8, quantity: 1 }, { productId: 53, quantity: 1 }] },
	{ id: "sundae-chocolate", sectorId: "sorvetes", outputProductId: 117, outputQuantity: 2, durationMs: 8 * MINUTE, requiredLevel: 35, ingredients: [{ productId: 116, quantity: 2 }, { productId: 24, quantity: 1 }] },
	{ id: "pote-sorvete-familia", sectorId: "sorvetes", outputProductId: 118, outputQuantity: 1, durationMs: 14 * MINUTE, requiredLevel: 45, ingredients: [{ productId: 116, quantity: 3 }, { productId: 49, quantity: 1 }] },
	{ id: "vinho-da-casa", sectorId: "adega", outputProductId: 119, outputQuantity: 2, durationMs: 6 * MINUTE, requiredLevel: 35, ingredients: [{ productId: 62, quantity: 4 }, { productId: 53, quantity: 1 }] },
	{ id: "sangria-da-casa", sectorId: "adega", outputProductId: 120, outputQuantity: 3, durationMs: 10 * MINUTE, requiredLevel: 45, ingredients: [{ productId: 119, quantity: 2 }, { productId: 49, quantity: 1 }, { productId: 14, quantity: 1 }] },
	{ id: "kit-harmonizacao", sectorId: "adega", outputProductId: 121, outputQuantity: 2, durationMs: 20 * MINUTE, requiredLevel: 46, ingredients: [{ productId: 31, quantity: 1 }, { productId: 106, quantity: 1 }, { productId: 32, quantity: 1 }] },
];

export function getProductionSector(sectorId: string) {
	return productionSectors.find((sector) => sector.id === sectorId);
}

export function getSectorRecipes(sectorId: ProductionSectorId) {
	return productionRecipes.filter((recipe) => recipe.sectorId === sectorId);
}
