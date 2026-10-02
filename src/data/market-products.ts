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
	{ id: 1, name: "Tomate", category: "hortifruti", unlockEra: "mesinha", unlockLevel: 1, purchasePrice: 12, sellingPrice: 20, rarity: "comum", demand: 74, popularity: 72, preferredCustomers: ["familia", "normal"], xpPerSale: 3 },
	{ id: 47, name: "Alface", category: "hortifruti", unlockEra: "mesinha", unlockLevel: 1, purchasePrice: 6, sellingPrice: 12, rarity: "comum", demand: 62, popularity: 58, preferredCustomers: ["familia", "premium"], xpPerSale: 2 },
	{ id: 46, name: "Banana", category: "hortifruti", unlockEra: "mesinha", unlockLevel: 1, purchasePrice: 8, sellingPrice: 14, rarity: "comum", demand: 80, popularity: 76, preferredCustomers: ["familia", "economico"], xpPerSale: 2 },
	{ id: 21, name: "Água mineral", category: "aguas", unlockEra: "mesinha", unlockLevel: 1, purchasePrice: 4, sellingPrice: 8, rarity: "comum", demand: 90, popularity: 70, preferredCustomers: ["normal", "impulsivo"], xpPerSale: 2 },
	{ id: 14, name: "Refrigerante", category: "refrigerantes", unlockEra: "mesinha", unlockLevel: 1, purchasePrice: 10, sellingPrice: 18, rarity: "comum", demand: 84, popularity: 82, preferredCustomers: ["impulsivo", "familia"], xpPerSale: 3 },
	{ id: 48, name: "Batata", category: "hortifruti", unlockEra: "tenda", unlockLevel: 2, purchasePrice: 8, sellingPrice: 14, rarity: "comum", demand: 76, popularity: 70, preferredCustomers: ["familia", "economico"], xpPerSale: 2 },
	{ id: 3, name: "Cenoura", category: "hortifruti", unlockEra: "tenda", unlockLevel: 2, purchasePrice: 6, sellingPrice: 10, rarity: "comum", demand: 70, popularity: 62, preferredCustomers: ["familia", "economico"], xpPerSale: 2 },
	{ id: 49, name: "Maçã", category: "hortifruti", unlockEra: "tenda", unlockLevel: 2, purchasePrice: 10, sellingPrice: 18, rarity: "comum", demand: 68, popularity: 66, preferredCustomers: ["familia", "premium"], xpPerSale: 3 },
	{ id: 50, name: "Ovos", category: "ovos", unlockEra: "tenda", unlockLevel: 2, purchasePrice: 18, sellingPrice: 30, rarity: "incomum", demand: 84, popularity: 80, preferredCustomers: ["familia", "normal"], xpPerSale: 3 },
	{ id: 13, name: "Suco natural", category: "bebidas", unlockEra: "tenda", unlockLevel: 3, purchasePrice: 10, sellingPrice: 18, rarity: "comum", demand: 66, popularity: 64, preferredCustomers: ["normal", "impulsivo"], xpPerSale: 3 },
	{ id: 9, name: "Pão francês", category: "padaria", unlockEra: "tenda", unlockLevel: 3, purchasePrice: 6, sellingPrice: 12, rarity: "comum", demand: 96, popularity: 94, preferredCustomers: ["familia", "economico"], xpPerSale: 2 },
	{ id: 62, name: "Uva", category: "hortifruti", unlockEra: "tenda", unlockLevel: 3, purchasePrice: 12, sellingPrice: 22, rarity: "incomum", demand: 56, popularity: 58, preferredCustomers: ["premium", "familia"], xpPerSale: 3 },
	{ id: 5, name: "Leite integral", category: "laticinios", unlockEra: "banca", unlockLevel: 5, purchasePrice: 10, sellingPrice: 16, rarity: "comum", demand: 92, popularity: 90, preferredCustomers: ["familia", "normal"], xpPerSale: 2 },
	{ id: 8, name: "Iogurte", category: "laticinios", unlockEra: "banca", unlockLevel: 5, purchasePrice: 12, sellingPrice: 22, rarity: "incomum", demand: 57, popularity: 58, preferredCustomers: ["normal", "premium"], xpPerSale: 3 },
	{ id: 7, name: "Manteiga", category: "laticinios", unlockEra: "banca", unlockLevel: 5, purchasePrice: 18, sellingPrice: 30, rarity: "incomum", demand: 46, popularity: 48, preferredCustomers: ["familia", "normal"], xpPerSale: 3 },
	{ id: 2, name: "Brócolis", category: "hortifruti", unlockEra: "banca", unlockLevel: 5, purchasePrice: 12, sellingPrice: 20, rarity: "comum", demand: 48, popularity: 45, preferredCustomers: ["premium", "normal"], xpPerSale: 3 },
	{ id: 4, name: "Pimentão", category: "hortifruti", unlockEra: "banca", unlockLevel: 5, purchasePrice: 10, sellingPrice: 18, rarity: "comum", demand: 42, popularity: 40, preferredCustomers: ["normal", "premium"], xpPerSale: 3 },
	{ id: 56, name: "Pão de forma", category: "padaria", unlockEra: "banca", unlockLevel: 5, purchasePrice: 14, sellingPrice: 24, rarity: "incomum", demand: 70, popularity: 68, preferredCustomers: ["familia", "normal"], xpPerSale: 3 },
	{ id: 22, name: "Energético", category: "energeticos", unlockEra: "conteiner", unlockLevel: 6, purchasePrice: 14, sellingPrice: 26, rarity: "incomum", demand: 62, popularity: 60, preferredCustomers: ["impulsivo", "normal"], xpPerSale: 3 },
	{ id: 25, name: "Bolacha recheada", category: "bolachas", unlockEra: "conteiner", unlockLevel: 6, purchasePrice: 8, sellingPrice: 16, rarity: "comum", demand: 76, popularity: 74, preferredCustomers: ["impulsivo", "familia"], xpPerSale: 2 },
	{ id: 23, name: "Bala de gelatina", category: "doces", unlockEra: "conteiner", unlockLevel: 6, purchasePrice: 4, sellingPrice: 10, rarity: "comum", demand: 79, popularity: 70, preferredCustomers: ["impulsivo"], xpPerSale: 2 },
	{ id: 12, name: "Waffle", category: "doces", unlockEra: "conteiner", unlockLevel: 6, purchasePrice: 12, sellingPrice: 22, rarity: "incomum", demand: 54, popularity: 52, preferredCustomers: ["impulsivo", "premium"], xpPerSale: 3 },
	{ id: 6, name: "Queijo prato", category: "queijos", unlockEra: "conteiner", unlockLevel: 7, purchasePrice: 28, sellingPrice: 48, rarity: "incomum", demand: 52, popularity: 54, preferredCustomers: ["familia", "premium"], xpPerSale: 4 },
	{ id: 60, name: "Cerveja", category: "alcoolicos", unlockEra: "spati", unlockLevel: 8, purchasePrice: 8, sellingPrice: 16, rarity: "comum", demand: 86, popularity: 84, preferredCustomers: ["normal", "impulsivo"], xpPerSale: 2 },
	{ id: 55, name: "Café em pó", category: "mercearia", unlockEra: "spati", unlockLevel: 8, purchasePrice: 20, sellingPrice: 34, rarity: "incomum", demand: 82, popularity: 80, preferredCustomers: ["familia", "normal"], xpPerSale: 3 },
	{ id: 51, name: "Arroz", category: "mercearia", unlockEra: "spati", unlockLevel: 8, purchasePrice: 30, sellingPrice: 48, rarity: "incomum", demand: 88, popularity: 86, preferredCustomers: ["familia", "economico"], xpPerSale: 4 },
	{ id: 52, name: "Feijão", category: "mercearia", unlockEra: "spati", unlockLevel: 8, purchasePrice: 12, sellingPrice: 20, rarity: "comum", demand: 84, popularity: 82, preferredCustomers: ["familia", "economico"], xpPerSale: 3 },
	{ id: 53, name: "Açúcar", category: "mercearia", unlockEra: "spati", unlockLevel: 9, purchasePrice: 6, sellingPrice: 12, rarity: "comum", demand: 70, popularity: 66, preferredCustomers: ["familia", "economico"], xpPerSale: 2 },
	{ id: 54, name: "Óleo de soja", category: "mercearia", unlockEra: "spati", unlockLevel: 9, purchasePrice: 10, sellingPrice: 18, rarity: "comum", demand: 72, popularity: 68, preferredCustomers: ["familia", "economico"], xpPerSale: 3 },
	{ id: 26, name: "Macarrão italiano", category: "massas", unlockEra: "spati", unlockLevel: 9, purchasePrice: 8, sellingPrice: 16, rarity: "comum", demand: 65, popularity: 64, preferredCustomers: ["familia", "normal"], xpPerSale: 2 },
	{ id: 43, name: "Farinha de trigo", category: "mercearia", unlockEra: "spati", unlockLevel: 9, purchasePrice: 6, sellingPrice: 12, rarity: "comum", demand: 60, popularity: 56, preferredCustomers: ["familia", "economico"], xpPerSale: 2 },
	{ id: 16, name: "Chá relaxante", category: "mercearia", unlockEra: "spati", unlockLevel: 10, purchasePrice: 10, sellingPrice: 20, rarity: "comum", demand: 38, popularity: 40, preferredCustomers: ["premium", "normal"], xpPerSale: 3 },
	{ id: 15, name: "Café especial", category: "mercearia", unlockEra: "spati", unlockLevel: 10, purchasePrice: 32, sellingPrice: 56, rarity: "raro", demand: 48, popularity: 52, preferredCustomers: ["premium", "normal"], xpPerSale: 4 },
	{ id: 17, name: "Pizza congelada", category: "congelados", unlockEra: "quitanda", unlockLevel: 11, purchasePrice: 28, sellingPrice: 50, rarity: "incomum", demand: 60, popularity: 64, preferredCustomers: ["familia", "impulsivo"], xpPerSale: 4 },
	{ id: 20, name: "Batata frita", category: "congelados", unlockEra: "quitanda", unlockLevel: 11, purchasePrice: 18, sellingPrice: 32, rarity: "incomum", demand: 71, popularity: 68, preferredCustomers: ["familia", "impulsivo"], xpPerSale: 3 },
	{ id: 18, name: "Pastel congelado", category: "congelados", unlockEra: "quitanda", unlockLevel: 11, purchasePrice: 20, sellingPrice: 36, rarity: "incomum", demand: 47, popularity: 50, preferredCustomers: ["familia", "normal"], xpPerSale: 4 },
	{ id: 40, name: "Refeição pronta", category: "congelados", unlockEra: "quitanda", unlockLevel: 11, purchasePrice: 24, sellingPrice: 44, rarity: "incomum", demand: 64, popularity: 62, preferredCustomers: ["impulsivo", "normal"], xpPerSale: 4 },
	{ id: 10, name: "Croissant", category: "padaria", unlockEra: "quitanda", unlockLevel: 12, purchasePrice: 14, sellingPrice: 28, rarity: "incomum", demand: 40, popularity: 46, preferredCustomers: ["premium", "impulsivo"], xpPerSale: 3 },
	{ id: 28, name: "Presunto defumado", category: "frios", unlockEra: "quitanda", unlockLevel: 12, purchasePrice: 24, sellingPrice: 44, rarity: "incomum", demand: 44, popularity: 48, preferredCustomers: ["familia", "normal"], xpPerSale: 4 },
	{ id: 29, name: "Cesta orgânica", category: "organicos", unlockEra: "quitanda", unlockLevel: 12, purchasePrice: 56, sellingPrice: 96, rarity: "raro", demand: 36, popularity: 40, preferredCustomers: ["premium"], xpPerSale: 5 },
	{ id: 24, name: "Chocolate premium", category: "chocolates", unlockEra: "quitanda", unlockLevel: 12, purchasePrice: 26, sellingPrice: 50, rarity: "incomum", demand: 30, popularity: 38, preferredCustomers: ["premium", "impulsivo"], xpPerSale: 4 },
	{ id: 35, name: "Detergente", category: "limpeza", unlockEra: "minimercado", unlockLevel: 15, purchasePrice: 6, sellingPrice: 12, rarity: "comum", demand: 73, popularity: 66, preferredCustomers: ["familia", "economico"], xpPerSale: 2 },
	{ id: 59, name: "Sabão em pó", category: "limpeza", unlockEra: "minimercado", unlockLevel: 15, purchasePrice: 24, sellingPrice: 42, rarity: "incomum", demand: 70, popularity: 64, preferredCustomers: ["familia", "normal"], xpPerSale: 4 },
	{ id: 58, name: "Papel higiênico", category: "higiene", unlockEra: "minimercado", unlockLevel: 15, purchasePrice: 20, sellingPrice: 36, rarity: "incomum", demand: 86, popularity: 80, preferredCustomers: ["familia", "economico"], xpPerSale: 4 },
	{ id: 34, name: "Shampoo", category: "higiene", unlockEra: "minimercado", unlockLevel: 15, purchasePrice: 20, sellingPrice: 38, rarity: "incomum", demand: 59, popularity: 58, preferredCustomers: ["normal", "premium"], xpPerSale: 4 },
	{ id: 37, name: "Fralda", category: "bebes", unlockEra: "minimercado", unlockLevel: 16, purchasePrice: 60, sellingPrice: 104, rarity: "raro", demand: 45, popularity: 50, preferredCustomers: ["familia"], xpPerSale: 6 },
	{ id: 36, name: "Ração premium", category: "pets", unlockEra: "minimercado", unlockLevel: 16, purchasePrice: 52, sellingPrice: 92, rarity: "raro", demand: 39, popularity: 44, preferredCustomers: ["familia", "premium"], xpPerSale: 5 },
	{ id: 38, name: "Pilha portátil", category: "eletronicos", unlockEra: "minimercado", unlockLevel: 16, purchasePrice: 18, sellingPrice: 36, rarity: "incomum", demand: 31, popularity: 36, preferredCustomers: ["impulsivo", "normal"], xpPerSale: 4 },
	{ id: 39, name: "Caderno", category: "papelaria", unlockEra: "minimercado", unlockLevel: 16, purchasePrice: 10, sellingPrice: 22, rarity: "incomum", demand: 40, popularity: 40, preferredCustomers: ["familia"], xpPerSale: 3 },
	{ id: 19, name: "Lasanha premium", category: "congelados", unlockEra: "minimercado", unlockLevel: 17, purchasePrice: 44, sellingPrice: 80, rarity: "raro", demand: 37, popularity: 40, preferredCustomers: ["premium", "familia"], xpPerSale: 5 },
	{ id: 30, name: "Granola premium", category: "mercearia", unlockEra: "minimercado", unlockLevel: 17, purchasePrice: 32, sellingPrice: 60, rarity: "raro", demand: 28, popularity: 34, preferredCustomers: ["premium"], xpPerSale: 4 },
	{ id: 41, name: "Panetone", category: "sazonais", unlockEra: "minimercado", unlockLevel: 17, purchasePrice: 40, sellingPrice: 76, rarity: "raro", demand: 34, popularity: 40, preferredCustomers: ["familia", "premium"], xpPerSale: 5 },
	{ id: 32, name: "Trufa gourmet", category: "chocolates", unlockEra: "mercadinho", unlockLevel: 19, purchasePrice: 56, sellingPrice: 110, rarity: "raro", demand: 18, popularity: 30, preferredCustomers: ["premium"], xpPerSale: 6 },
	{ id: 31, name: "Vinho importado", category: "alcoolicos", unlockEra: "mercadinho", unlockLevel: 19, purchasePrice: 90, sellingPrice: 170, rarity: "epico", demand: 24, popularity: 34, preferredCustomers: ["premium"], xpPerSale: 7 },
	{ id: 61, name: "Picolé", category: "sorvetes", unlockEra: "supermercado", unlockLevel: 25, purchasePrice: 6, sellingPrice: 16, rarity: "comum", demand: 78, popularity: 72, preferredCustomers: ["impulsivo", "familia"], xpPerSale: 2 },
	{ id: 57, name: "Frango", category: "carnes", unlockEra: "supermercado", unlockLevel: 25, purchasePrice: 28, sellingPrice: 52, rarity: "raro", demand: 84, popularity: 80, preferredCustomers: ["familia", "economico"], xpPerSale: 4 },
	{ id: 27, name: "Carne nobre", category: "carnes", unlockEra: "supermercado", unlockLevel: 25, purchasePrice: 110, sellingPrice: 190, rarity: "epico", demand: 40, popularity: 46, preferredCustomers: ["premium", "familia"], xpPerSale: 7 },
	{ id: 44, name: "Peixe fresco", category: "peixes", unlockEra: "hipermercado", unlockLevel: 33, purchasePrice: 44, sellingPrice: 80, rarity: "raro", demand: 38, popularity: 42, preferredCustomers: ["premium", "familia"], xpPerSale: 5 },
	{ id: 45, name: "Camarão fresco", category: "peixes", unlockEra: "hipermercado", unlockLevel: 33, purchasePrice: 90, sellingPrice: 160, rarity: "epico", demand: 24, popularity: 32, preferredCustomers: ["premium"], xpPerSale: 7 },
	{ id: 33, name: "Champanhe reserva", category: "alcoolicos", unlockEra: "rede", unlockLevel: 45, purchasePrice: 240, sellingPrice: 480, rarity: "lendario", demand: 8, popularity: 20, preferredCustomers: ["premium"], xpPerSale: 11 },
	{ id: 101, name: "Baguete rústica", category: "padaria", unlockEra: "mercadinho", unlockLevel: 19, purchasePrice: 8, sellingPrice: 19, rarity: "comum", demand: 68, popularity: 70, preferredCustomers: ["familia", "premium"], xpPerSale: 3, acquisition: "production" },
	{ id: 102, name: "Croissant premium", category: "padaria", unlockEra: "mercadinho", unlockLevel: 19, purchasePrice: 14, sellingPrice: 33, rarity: "incomum", demand: 52, popularity: 56, preferredCustomers: ["premium", "impulsivo"], xpPerSale: 3, acquisition: "production" },
	{ id: 103, name: "Bolo de vitrine", category: "doces", unlockEra: "mercadinho", unlockLevel: 20, purchasePrice: 38, sellingPrice: 95, rarity: "raro", demand: 34, popularity: 46, preferredCustomers: ["premium", "familia"], xpPerSale: 5, acquisition: "production" },
	{ id: 104, name: "Queijo minas artesanal", category: "queijos", unlockEra: "supermercado", unlockLevel: 25, purchasePrice: 20, sellingPrice: 45, rarity: "incomum", demand: 60, popularity: 62, preferredCustomers: ["familia", "normal"], xpPerSale: 4, acquisition: "production" },
	{ id: 105, name: "Brie maturado", category: "queijos", unlockEra: "supermercado", unlockLevel: 26, purchasePrice: 29, sellingPrice: 67, rarity: "raro", demand: 40, popularity: 44, preferredCustomers: ["premium"], xpPerSale: 5, acquisition: "production" },
	{ id: 107, name: "Hambúrguer artesanal", category: "carnes", unlockEra: "supermercado", unlockLevel: 26, purchasePrice: 34, sellingPrice: 80, rarity: "raro", demand: 62, popularity: 66, preferredCustomers: ["familia", "impulsivo"], xpPerSale: 5, acquisition: "production" },
	{ id: 113, name: "Suco gelado da casa", category: "bebidas", unlockEra: "supermercado", unlockLevel: 26, purchasePrice: 14, sellingPrice: 34, rarity: "incomum", demand: 67, popularity: 66, preferredCustomers: ["impulsivo", "familia"], xpPerSale: 3, acquisition: "production" },
	{ id: 114, name: "Chá gelado artesanal", category: "bebidas", unlockEra: "supermercado", unlockLevel: 26, purchasePrice: 8, sellingPrice: 22, rarity: "incomum", demand: 48, popularity: 50, preferredCustomers: ["premium", "impulsivo"], xpPerSale: 3, acquisition: "production" },
	{ id: 106, name: "Tábua de queijos", category: "queijos", unlockEra: "hipermercado", unlockLevel: 33, purchasePrice: 80, sellingPrice: 229, rarity: "epico", demand: 22, popularity: 34, preferredCustomers: ["premium"], xpPerSale: 8, acquisition: "production" },
	{ id: 108, name: "Corte dry-aged", category: "carnes", unlockEra: "hipermercado", unlockLevel: 33, purchasePrice: 165, sellingPrice: 399, rarity: "lendario", demand: 24, popularity: 34, preferredCustomers: ["premium"], xpPerSale: 10, acquisition: "production" },
	{ id: 109, name: "Kit churrasco premium", category: "carnes", unlockEra: "hipermercado", unlockLevel: 34, purchasePrice: 98, sellingPrice: 241, rarity: "epico", demand: 30, popularity: 40, preferredCustomers: ["familia", "premium"], xpPerSale: 8, acquisition: "production" },
	{ id: 110, name: "Filé de peixe fresco", category: "peixes", unlockEra: "hipermercado", unlockLevel: 34, purchasePrice: 22, sellingPrice: 56, rarity: "raro", demand: 54, popularity: 52, preferredCustomers: ["familia", "premium"], xpPerSale: 4, acquisition: "production" },
	{ id: 111, name: "Sushi especial", category: "peixes", unlockEra: "hipermercado", unlockLevel: 34, purchasePrice: 40, sellingPrice: 97, rarity: "raro", demand: 40, popularity: 48, preferredCustomers: ["premium", "impulsivo"], xpPerSale: 5, acquisition: "production" },
	{ id: 115, name: "Vitamina cremosa", category: "bebidas", unlockEra: "hipermercado", unlockLevel: 34, purchasePrice: 16, sellingPrice: 38, rarity: "incomum", demand: 41, popularity: 48, preferredCustomers: ["familia", "premium"], xpPerSale: 4, acquisition: "production" },
	{ id: 116, name: "Sorvete de creme", category: "sorvetes", unlockEra: "hipermercado", unlockLevel: 35, purchasePrice: 13, sellingPrice: 31, rarity: "incomum", demand: 69, popularity: 70, preferredCustomers: ["familia", "impulsivo"], xpPerSale: 3, acquisition: "production" },
	{ id: 117, name: "Sundae de chocolate", category: "sorvetes", unlockEra: "hipermercado", unlockLevel: 35, purchasePrice: 26, sellingPrice: 78, rarity: "raro", demand: 44, popularity: 52, preferredCustomers: ["impulsivo", "premium"], xpPerSale: 5, acquisition: "production" },
	{ id: 119, name: "Vinho tinto da casa", category: "alcoolicos", unlockEra: "hipermercado", unlockLevel: 35, purchasePrice: 27, sellingPrice: 70, rarity: "raro", demand: 40, popularity: 46, preferredCustomers: ["premium", "normal"], xpPerSale: 5, acquisition: "production" },
	{ id: 112, name: "Barco de frutos do mar", category: "peixes", unlockEra: "rede", unlockLevel: 45, purchasePrice: 114, sellingPrice: 284, rarity: "lendario", demand: 16, popularity: 30, preferredCustomers: ["premium"], xpPerSale: 9, acquisition: "production" },
	{ id: 118, name: "Pote de sorvete família", category: "sorvetes", unlockEra: "rede", unlockLevel: 45, purchasePrice: 49, sellingPrice: 155, rarity: "epico", demand: 40, popularity: 48, preferredCustomers: ["familia"], xpPerSale: 7, acquisition: "production" },
	{ id: 120, name: "Sangria da casa", category: "alcoolicos", unlockEra: "rede", unlockLevel: 45, purchasePrice: 25, sellingPrice: 82, rarity: "raro", demand: 36, popularity: 44, preferredCustomers: ["premium", "impulsivo"], xpPerSale: 5, acquisition: "production" },
	{ id: 121, name: "Kit harmonização", category: "gourmet", unlockEra: "rede", unlockLevel: 46, purchasePrice: 113, sellingPrice: 356, rarity: "lendario", demand: 20, popularity: 32, preferredCustomers: ["premium"], xpPerSale: 10, acquisition: "production" },
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
