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
		requiredLevel: __L7__,
		slotCount: 2,
		subtitle: "Pães & confeitaria",
	},
	{
		description: "Transforme leite fresco em queijos artesanais de alto valor.",
		id: "queijaria",
		name: "Queijaria",
		eraId: "supermercado",
		requiredLevel: __L8__,
		slotCount: 2,
		subtitle: "Queijos & frios",
	},
	{
		description: "Prepare cortes nobres e combinações premium para os clientes exigentes.",
		id: "acougue",
		name: "Açougue",
		eraId: "supermercado",
		requiredLevel: __L8__,
		slotCount: 3,
		subtitle: "Cortes & churrasco",
	},
	{
		description: "Prepare sucos, chás gelados e vitaminas no balcão de bebidas.",
		id: "bebidas",
		name: "Bebidas",
		eraId: "supermercado",
		requiredLevel: __L8__,
		slotCount: 2,
		subtitle: "Sucos & bebidas geladas",
	},
	{
		description: "Uma bancada gelada para peixes frescos, sushi e frutos do mar.",
		id: "peixaria",
		name: "Peixaria",
		eraId: "hipermercado",
		requiredLevel: __L9__,
		slotCount: 3,
		subtitle: "Pescados & frutos do mar",
	},
	{
		description: "Produza sorvetes artesanais e sobremesas para a vitrine fria.",
		id: "sorvetes",
		name: "Sorvetes",
		eraId: "hipermercado",
		requiredLevel: __L9__,
		slotCount: 3,
		subtitle: "Sorvetes & sobremesas",
	},
	{
		description: "Uma adega climatizada para vinhos da casa, sangrias e kits de harmonização.",
		id: "adega",
		name: "Adega",
		eraId: "hipermercado",
		requiredLevel: __L9__,
		slotCount: 3,
		subtitle: "Vinhos & harmonizações",
	},
];

// Generated with the catalog (scripts/economy/catalog.py).
export const productionRecipes: ProductionRecipe[] = [
/*RECIPES*/
];

export function getProductionSector(sectorId: string) {
	return productionSectors.find((sector) => sector.id === sectorId);
}

export function getSectorRecipes(sectorId: ProductionSectorId) {
	return productionRecipes.filter((recipe) => recipe.sectorId === sectorId);
}
