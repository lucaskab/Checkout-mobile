import type { MarketEraId } from "@/@types/economy";
import type { ProductionSectorId } from "@/@types/production";

// The market's fixtures and what each one may hold, as in a real market: the produce crates only take
// fruit and vegetables, the drinks cooler only drinks, the chest freezer only ice cream, the frozen-food
// freezer only frozen food, and so on. Each production sector also has its own counter (padaria,
// açougue, peixaria...): the sector makes the goods and sells them right there.
//
// A fixture only exists once the market has room (and power) for it, and its products only open then
// (src/data/market-products.ts unlockEra). The sidewalk table has a few crates and a styrofoam cooler; the
// tent adds a bread basket; the fair stall a refrigerated display (Unity: ERA2_Freezer); the container
// has a real drinks fridge and shelves for sweets (ERA3_Fridge, ERA3_Shelf); the Späti is the first
// shop with a grocery gondola; then the frozen-food freezer (quitanda), the home & hygiene gondola
// (minimercado) and the ice cream chest freezer (supermarket). The same fixture gets a better name as
// the market grows (the styrofoam cooler becomes the drinks fridge with the container).

export type ShelfTypeId =
	| "produce"
	| "dairy"
	| "drinks"
	| "bakery"
	| "snacks"
	| "coffee"
	| "pizza"
	| "home"
	| "icecream";

/** The name a fixture has from expansion `eraId` on. */
export type ShelfStage = { eraId: MarketEraId; name: string };

export type ShelfType = {
	id: ShelfTypeId;
	/** Name of the fixture in its final form. */
	name: string;
	/** Short name (cards, chips). */
	shortName: string;
	/** Product categories it can hold. */
	categories: readonly string[];
	/** Expansion from which it can be bought. */
	eraId: MarketEraId;
	/** Price to buy it (0 = comes with the sidewalk table). */
	coinCost: number;
	/** What it is, in the words of the player (shown when a product does not fit). */
	holds: string;
	/** Names along the expansions (first one = when it arrives; the last one is `name`). */
	stages: ShelfStage[];
};

/** In opening order: the first two come with the sidewalk table, then one by one with the expansions. */
export const shelfTypes: ShelfType[] = [
	{
		id: "produce",
		name: "Banca de hortifrúti",
		shortName: "Hortifrúti",
		categories: ["hortifruti", "organicos", "ovos"],
		eraId: "mesinha",
		coinCost: 0,
		holds: "frutas, verduras, legumes e ovos",
		stages: [
			{ eraId: "mesinha", name: "Caixotes de hortifrúti" },
			{ eraId: "banca", name: "Banca de hortifrúti" },
		],
	},
	{
		id: "drinks",
		name: "Geladeira de bebidas",
		shortName: "Bebidas",
		categories: ["bebidas", "refrigerantes", "aguas", "energeticos", "alcoolicos"],
		eraId: "mesinha",
		coinCost: 0,
		holds: "bebidas: água, sucos, refrigerantes, energéticos, cerveja e vinho",
		stages: [
			{ eraId: "mesinha", name: "Isopor com gelo" },
			{ eraId: "conteiner", name: "Geladeira de bebidas" },
		],
	},
	{
		id: "bakery",
		name: "Prateleira da padaria",
		shortName: "Pães",
		categories: ["padaria", "doces"],
		eraId: "tenda",
		coinCost: 300,
		holds: "pães, bolos e doces",
		stages: [
			{ eraId: "tenda", name: "Cesto de pães" },
			{ eraId: "spati", name: "Prateleira da padaria" },
		],
	},
	{
		id: "dairy",
		name: "Geladeira de laticínios e frios",
		shortName: "Laticínios",
		categories: ["laticinios", "queijos", "frios"],
		eraId: "banca",
		coinCost: 1_500,
		holds: "leite, iogurte, manteiga, queijos e frios",
		stages: [
			{ eraId: "banca", name: "Expositor refrigerado" },
			{ eraId: "spati", name: "Geladeira de laticínios e frios" },
		],
	},
	{
		id: "snacks",
		name: "Gôndola de doces e biscoitos",
		shortName: "Doces",
		categories: ["doces", "chocolates", "bolachas", "sazonais"],
		eraId: "conteiner",
		coinCost: 3_000,
		holds: "doces, chocolates, biscoitos e produtos de época",
		stages: [
			{ eraId: "conteiner", name: "Prateleira de doces" },
			{ eraId: "spati", name: "Gôndola de doces e biscoitos" },
		],
	},
	{
		id: "coffee",
		name: "Gôndola de mercearia",
		shortName: "Mercearia",
		categories: ["mercearia", "massas", "ovos"],
		eraId: "spati",
		coinCost: 6_000,
		holds: "arroz, feijão, café, açúcar, óleo, massas e ovos",
		stages: [{ eraId: "spati", name: "Gôndola de mercearia" }],
	},
	{
		id: "pizza",
		name: "Freezer de congelados",
		shortName: "Congelados",
		categories: ["congelados"],
		eraId: "quitanda",
		coinCost: 12_000,
		holds: "congelados: pizzas, lasanhas, pastéis e pratos prontos",
		stages: [{ eraId: "quitanda", name: "Freezer de congelados" }],
	},
	{
		id: "home",
		name: "Gôndola de casa e higiene",
		shortName: "Casa",
		categories: ["higiene", "limpeza", "pets", "bebes", "papelaria", "eletronicos"],
		eraId: "minimercado",
		coinCost: 20_000,
		holds: "higiene, limpeza, pets, bebês, papelaria e pilhas",
		stages: [{ eraId: "minimercado", name: "Gôndola de casa e higiene" }],
	},
	{
		id: "icecream",
		name: "Freezer horizontal de sorvetes",
		shortName: "Sorvetes",
		categories: ["sorvetes"],
		eraId: "supermercado",
		coinCost: 40_000,
		holds: "sorvetes e picolés",
		stages: [{ eraId: "supermercado", name: "Freezer horizontal de sorvetes" }],
	},
];

const eraOrderForNames: MarketEraId[] = [
	"mesinha",
	"tenda",
	"banca",
	"conteiner",
	"spati",
	"quitanda",
	"minimercado",
	"mercadinho",
	"supermercado",
	"hipermercado",
	"rede",
];

/** Name of a shelf in the expansion `eraId` (the styrofoam cooler on the sidewalk, the fridge later). */
export function getShelfStageName(shelf: ShelfType, eraId?: MarketEraId) {
	if (!eraId) return shelf.name;
	const at = eraOrderForNames.indexOf(eraId);
	let name = shelf.stages[0]?.name ?? shelf.name;
	for (const stage of shelf.stages) if (eraOrderForNames.indexOf(stage.eraId) <= at) name = stage.name;
	return name;
}

/** Counter of a production sector: sells what the sector makes (and its kind of goods). */
export type SectorCounter = {
	id: `sector-${ProductionSectorId}`;
	sectorId: ProductionSectorId;
	name: string;
	categories: readonly string[];
	holds: string;
};

export const SECTOR_SHELF_PREFIX = "sector-";

export const sectorCounters: SectorCounter[] = [
	{
		id: "sector-padaria",
		sectorId: "padaria",
		name: "Balcão da padaria",
		categories: ["padaria", "doces"],
		holds: "pães, bolos e doces",
	},
	{
		id: "sector-queijaria",
		sectorId: "queijaria",
		name: "Balcão de frios e queijos",
		categories: ["queijos", "frios", "laticinios"],
		holds: "queijos, frios e laticínios",
	},
	{
		id: "sector-acougue",
		sectorId: "acougue",
		name: "Balcão do açougue",
		categories: ["carnes"],
		holds: "carnes",
	},
	{
		id: "sector-bebidas",
		sectorId: "bebidas",
		name: "Balcão de sucos",
		categories: ["bebidas"],
		holds: "sucos, chás e vitaminas",
	},
	{
		id: "sector-peixaria",
		sectorId: "peixaria",
		name: "Balcão da peixaria",
		categories: ["peixes"],
		holds: "peixes e frutos do mar",
	},
	{
		id: "sector-sorvetes",
		sectorId: "sorvetes",
		name: "Vitrine de sorvetes",
		categories: ["sorvetes"],
		holds: "sorvetes e sobremesas geladas",
	},
	{
		id: "sector-adega",
		sectorId: "adega",
		name: "Adega",
		categories: ["alcoolicos", "gourmet"],
		holds: "vinhos, espumantes e kits gourmet",
	},
];

export function isSectorShelfId(physicalShelfId: string) {
	return physicalShelfId.startsWith(SECTOR_SHELF_PREFIX);
}

export function getSectorCounter(physicalShelfId: string) {
	return sectorCounters.find((counter) => counter.id === physicalShelfId) ?? null;
}

export function getSectorCounterFor(sectorId: string) {
	return sectorCounters.find((counter) => counter.sectorId === sectorId) ?? null;
}

export function getShelfType(physicalShelfId: string) {
	return shelfTypes.find((shelf) => shelf.id === physicalShelfId) ?? null;
}

/** Categories a fixture (shelf or sector counter) accepts; empty for unknown ids. */
export function getShelfCategories(physicalShelfId: string): readonly string[] {
	return getShelfType(physicalShelfId)?.categories ?? getSectorCounter(physicalShelfId)?.categories ?? [];
}

/** Name of a fixture; with `eraId`, the name it has in that expansion (isopor → geladeira...). */
export function getFixtureName(physicalShelfId: string, eraId?: MarketEraId) {
	const shelf = getShelfType(physicalShelfId);
	if (shelf) return getShelfStageName(shelf, eraId);
	return getSectorCounter(physicalShelfId)?.name ?? "Prateleira";
}

/** Fixtures (shelves and counters) where a product of `category` can be sold. */
export function getFixturesForCategory(category: string) {
	return [
		...shelfTypes.filter((shelf) => shelf.categories.includes(category)).map((shelf) => shelf.id as string),
		...sectorCounters.filter((counter) => counter.categories.includes(category)).map((counter) => counter.id as string),
	];
}
