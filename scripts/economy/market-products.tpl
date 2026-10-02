import type { MarketEraId } from "@/@types/economy";
import type { ItemDefinition, ItemRarity } from "@/@types/item";
import type { StoreShelf } from "@/@types/store";
import { getFixturesForCategory, shelfTypes } from "@/data/shelf-types";

// The whole catalog of the game, from the tomato on the sidewalk table to the champagne of the chain.
//
// How the numbers were chosen (the full reasoning is in the economy report, claude/economia-produtos.md):
// - Prices are coins at about real supermarket prices, so a pack of rice costs more than a tomato and
//   a bottle of champagne a lot more than a beer. Margins follow retail: staples (rice, beans, milk,
//   water) earn little per unit, fruit and vegetables a bit more, impulse buys (sweets, soft drinks)
//   and premium goods the most.
// - Every product opens with an expansion (`unlockEra`) and a level inside it (`unlockLevel`), so each
//   expansion brings the goods its fixtures can hold (src/data/shelf-types.ts): on the sidewalk table only
//   what fits the crates and the styrofoam cooler (tomato, lettuce, banana, water, soda); bread with the
//   tent's basket; milk and dairy with the fair stall's refrigerated display; sweets and energy drinks
//   with the container's fridge and shelves; grocery staples and beer with the Späti; frozen food with
//   the quitanda; home and hygiene with the minimercado; the butcher's and the fishmonger's with the
//   supermarket and the hypermarket; champagne with the chain. A product never opens before a fixture
//   that can hold it.
// - Crafted goods (acquisition "production") cost what their ingredients cost and sell for about 40%
//   more than the ingredients would on their own: the sector pays for itself with time.
// - Experience per sale grows with the square root of the price (a 240-coin champagne gives 19 XP, a
//   4-coin water 4 XP), so leveling keeps pace without expensive goods running away with it.
// The robot player (scripts/economy-robot.ts) plays these numbers and checks each expansion arrives
// on its target day.

export const itemCategories = [
	{ id: "hortifruti", label: "Hortifruti" },
	{ id: "organicos", label: "Orgânicos" },
	{ id: "ovos", label: "Ovos" },
	{ id: "laticinios", label: "Laticínios" },
	{ id: "queijos", label: "Queijos" },
	{ id: "frios", label: "Frios" },
	{ id: "padaria", label: "Padaria" },
	{ id: "doces", label: "Doces" },
	{ id: "chocolates", label: "Chocolates" },
	{ id: "bolachas", label: "Bolachas" },
	{ id: "sazonais", label: "Sazonais" },
	{ id: "bebidas", label: "Bebidas" },
	{ id: "refrigerantes", label: "Refrigerantes" },
	{ id: "aguas", label: "Águas" },
	{ id: "energeticos", label: "Energéticos" },
	{ id: "alcoolicos", label: "Alcoólicos" },
	{ id: "mercearia", label: "Mercearia" },
	{ id: "massas", label: "Massas" },
	{ id: "congelados", label: "Congelados" },
	{ id: "sorvetes", label: "Sorvetes" },
	{ id: "carnes", label: "Carnes" },
	{ id: "peixes", label: "Peixes" },
	{ id: "gourmet", label: "Gourmet" },
	{ id: "higiene", label: "Higiene" },
	{ id: "limpeza", label: "Limpeza" },
	{ id: "pets", label: "Pets" },
	{ id: "bebes", label: "Bebês" },
	{ id: "eletronicos", label: "Eletrônicos" },
	{ id: "papelaria", label: "Papelaria" },
] as const;

type CatalogSeed = Pick<
	ItemDefinition,
	"category" | "id" | "name" | "purchasePrice" | "rarity" | "sellingPrice"
> & {
	acquisition?: ItemDefinition["acquisition"];
	demand?: number;
	popularity?: number;
	preferredCustomers?: ItemDefinition["preferredCustomers"];
	unlockEra: MarketEraId;
	unlockLevel: number;
	xpPerSale?: number;
};

const raritySettings: Record<
	ItemRarity,
	Pick<ItemDefinition, "reputation" | "saleVelocity" | "visualAttractiveness" | "xpPerSale">
> = {
	comum: { reputation: 1, saleVelocity: "rapida", visualAttractiveness: 35, xpPerSale: 4 },
	incomum: { reputation: 2, saleVelocity: "media", visualAttractiveness: 50, xpPerSale: 7 },
	raro: { reputation: 4, saleVelocity: "media", visualAttractiveness: 65, xpPerSale: 12 },
	epico: { reputation: 7, saleVelocity: "lenta", visualAttractiveness: 78, xpPerSale: 20 },
	lendario: { reputation: 12, saleVelocity: "lenta", visualAttractiveness: 88, xpPerSale: 32 },
	luxo: { reputation: 20, saleVelocity: "lenta", visualAttractiveness: 96, xpPerSale: 48 },
	colecionavel: { reputation: 28, saleVelocity: "lenta", visualAttractiveness: 100, xpPerSale: 70 },
};

const maxSupplierDeliveryLevel = 30;
const maxSupplierDeliveryProfit = 120;

/** Delivery time: a few minutes for cheap everyday goods, hours for the expensive late ones. */
function getSupplierTime(unlockLevel: number, profitPerUnit: number) {
	const minMinutes = 3;
	const maxMinutes = 12 * 60;
	const levelProgress = Math.min(1, Math.max(0, (unlockLevel - 1) / (maxSupplierDeliveryLevel - 1)));
	const profitProgress = Math.min(1, Math.max(0, profitPerUnit / maxSupplierDeliveryProfit));
	const deliveryProgress = profitProgress ** 2 * (0.2 + levelProgress * 0.8);
	const minutes = Math.round(minMinutes + deliveryProgress * (maxMinutes - minMinutes));
	const roundedMinutes = minutes < 60 ? minutes : Math.min(maxMinutes, Math.round(minutes / 15) * 15);
	if (roundedMinutes < 60) return `${roundedMinutes}m`;
	const hours = Math.floor(roundedMinutes / 60);
	const remainingMinutes = roundedMinutes % 60;
	return remainingMinutes ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

const perishableCategories = ["hortifruti", "organicos", "laticinios", "padaria", "carnes", "peixes", "frios"];

/** Where a product of `category` goes by default: the first fixture that holds it. */
export function getDefaultShelfId(category: string) {
	return getFixturesForCategory(category)[0];
}

function createItem(seed: CatalogSeed): ItemDefinition {
	const rarity = raritySettings[seed.rarity];
	const demand = seed.demand ?? 50;
	const perishable =
		perishableCategories.includes(seed.category) ||
		(seed.acquisition === "production" && ["bebidas", "queijos"].includes(seed.category));

	return {
		acquisition: seed.acquisition ?? "supplier",
		category: seed.category,
		demand,
		expirationHours: perishable ? 48 : null,
		id: seed.id,
		maxPrice: Math.max(seed.sellingPrice + 1, Math.round(seed.sellingPrice * 1.3)),
		minPrice: Math.max(1, Math.min(seed.sellingPrice - 1, Math.round(seed.sellingPrice * 0.75))),
		name: seed.name,
		popularity: seed.popularity ?? 50,
		preferredCustomers: seed.preferredCustomers ?? ["normal"],
		profitPerUnit: seed.sellingPrice - seed.purchasePrice,
		purchasePrice: seed.purchasePrice,
		rarity: seed.rarity,
		recommendedStock: Math.max(3, Math.round(demand / 8)),
		restockFrequency: demand >= 70 ? "alta" : demand >= 35 ? "media" : "baixa",
		reputation: rarity.reputation,
		saleVelocity: rarity.saleVelocity,
		sellingPrice: seed.sellingPrice,
		shelfId: getDefaultShelfId(seed.category),
		shelfSpace: seed.rarity === "luxo" || seed.rarity === "colecionavel" ? 2 : 1,
		spoilChance: perishable ? 0.04 + (100 - demand) / 2500 : 0,
		supplierQuantity: 1,
		supplierTime: getSupplierTime(seed.unlockLevel, seed.sellingPrice - seed.purchasePrice),
		suggestedPrice: seed.sellingPrice,
		unlockEra: seed.unlockEra,
		unlockLevel: seed.unlockLevel,
		visualAttractiveness: rarity.visualAttractiveness,
		xpPerSale: seed.xpPerSale ?? rarity.xpPerSale,
	};
}

// Generated from the balance sheet (scripts/economy/catalog.py): edit there and regenerate, or edit here
// and keep the sheet in sync. Crafted goods: purchasePrice = ingredients / batch, sellingPrice = 1.4 ×
// what the ingredients sell for / batch (src/data/production-sectors.ts has the recipes).
const catalogSeeds: CatalogSeed[] = [
/*SEEDS*/
];

/** Products retired from the catalog: old saves give them back as coins (see migrateGameState). */
export const retiredProductIds = [11, 42];

export const itemCatalog: ItemDefinition[] = catalogSeeds.map(createItem);

export const marketProducts = itemCatalog.map((product) => ({
	...product,
	shelfId: product.shelfId as string,
	experience: product.xpPerSale,
	marketPrice: product.suggestedPrice,
	necessity: product.demand,
	productId: product.id,
}));

export const productionProducts = itemCatalog.filter((product) => product.acquisition === "production");

/** The fixtures of the store, in the order they open (src/data/shelf-types.ts). */
export const shelves: StoreShelf[] = shelfTypes.map((shelf) => ({ id: shelf.id, name: shelf.name }));

/** Fixtures the player owns on a new game: the produce crates and the styrofoam cooler of the sidewalk table. */
export const starterShelfIds = shelfTypes.filter((shelf) => shelf.coinCost === 0).map((shelf) => shelf.id as string);

/** A new game: tomatoes in the crates and water in the cooler. */
const starterProducts: Record<string, number> = { produce: 1, drinks: 21 };

export const initialShelfAssignments: Record<string, number | null> = Object.fromEntries(
	shelves.map((shelf) => [shelf.id, starterProducts[shelf.id] ?? null]),
);

const eraOrder: MarketEraId[] = [
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

export function getEraOrder(eraId: MarketEraId) {
	const index = eraOrder.indexOf(eraId);
	return index < 0 ? 0 : index;
}

/**
 * Products the player can sell at `level` in the expansion `eraId`. Without an expansion only the level
 * counts (old callers and tests); the game always passes the current expansion.
 */
export function getUnlockedProductIds(level: number, eraId?: MarketEraId) {
	const eraIndex = eraId ? getEraOrder(eraId) : eraOrder.length;
	return itemCatalog
		.filter((product) => product.unlockLevel <= level && getEraOrder(product.unlockEra) <= eraIndex)
		.map((product) => product.id);
}

export type MarketProduct = (typeof marketProducts)[number];
