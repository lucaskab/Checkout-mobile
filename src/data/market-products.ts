import type { ItemDefinition, ItemRarity } from "@/@types/item";
import type { StoreShelf } from "@/@types/store";
import { productionRecipes } from "@/data/production-sectors";

export const itemCategories = [
	{ id: "hortifruti", label: "Hortifruti" },
	{ id: "laticinios", label: "Laticínios" },
	{ id: "padaria", label: "Padaria" },
	{ id: "bebidas", label: "Bebidas" },
	{ id: "refrigerantes", label: "Refrigerantes" },
	{ id: "aguas", label: "Águas" },
	{ id: "energeticos", label: "Energéticos" },
	{ id: "doces", label: "Doces" },
	{ id: "chocolates", label: "Chocolates" },
	{ id: "bolachas", label: "Bolachas" },
	{ id: "massas", label: "Massas" },
	{ id: "congelados", label: "Congelados" },
	{ id: "carnes", label: "Carnes" },
	{ id: "peixes", label: "Peixes" },
	{ id: "frios", label: "Frios" },
	{ id: "queijos", label: "Queijos" },
	{ id: "organicos", label: "Orgânicos" },
	{ id: "premium", label: "Premium" },
	{ id: "importados", label: "Importados" },
	{ id: "gourmet", label: "Gourmet" },
	{ id: "luxo", label: "Luxo" },
	{ id: "higiene", label: "Higiene" },
	{ id: "limpeza", label: "Limpeza" },
	{ id: "pets", label: "Pets" },
	{ id: "bebes", label: "Bebês" },
	{ id: "eletronicos", label: "Eletrônicos" },
	{ id: "papelaria", label: "Papelaria" },
	{ id: "conveniencia", label: "Conveniência" },
	{ id: "sazonais", label: "Sazonais" },
] as const;

type CatalogSeed = Pick<
	ItemDefinition,
	"category" | "id" | "name" | "purchasePrice" | "rarity" | "sellingPrice"
> & {
	acquisition?: ItemDefinition["acquisition"];
	demand?: number;
	popularity?: number;
	preferredCustomers?: ItemDefinition["preferredCustomers"];
	shelfId?: string;
	unlockLevel: number;
	xpPerSale?: number;
};

const raritySettings: Record<
	ItemRarity,
	Pick<
		ItemDefinition,
		"reputation" | "saleVelocity" | "visualAttractiveness" | "xpPerSale"
	>
> = {
	comum: {
		reputation: 1,
		saleVelocity: "rapida",
		visualAttractiveness: 35,
		xpPerSale: 4,
	},
	incomum: {
		reputation: 2,
		saleVelocity: "media",
		visualAttractiveness: 50,
		xpPerSale: 7,
	},
	raro: {
		reputation: 4,
		saleVelocity: "media",
		visualAttractiveness: 65,
		xpPerSale: 12,
	},
	epico: {
		reputation: 7,
		saleVelocity: "lenta",
		visualAttractiveness: 78,
		xpPerSale: 20,
	},
	lendario: {
		reputation: 12,
		saleVelocity: "lenta",
		visualAttractiveness: 88,
		xpPerSale: 32,
	},
	luxo: {
		reputation: 20,
		saleVelocity: "lenta",
		visualAttractiveness: 96,
		xpPerSale: 48,
	},
	colecionavel: {
		reputation: 28,
		saleVelocity: "lenta",
		visualAttractiveness: 100,
		xpPerSale: 70,
	},
};

const maxSupplierDeliveryLevel = 20;
const maxSupplierDeliveryProfit = 350;

function getSupplierTime(unlockLevel: number, profitPerUnit: number) {
	const minMinutes = 3;
	const maxMinutes = 24 * 60;
	const levelProgress = Math.min(
		1,
		Math.max(0, (unlockLevel - 1) / (maxSupplierDeliveryLevel - 1)),
	);
	const profitProgress = Math.min(
		1,
		Math.max(0, profitPerUnit / maxSupplierDeliveryProfit),
	);
	const deliveryProgress = profitProgress ** 2 * (0.2 + levelProgress * 0.8);
	const minutes = Math.round(
		minMinutes + deliveryProgress * (maxMinutes - minMinutes),
	);
	const roundedMinutes =
		minutes < 60
			? minutes
			: Math.min(maxMinutes, Math.round(minutes / 15) * 15);

	if (roundedMinutes < 60) {
		return `${roundedMinutes}m`;
	}

	const hours = Math.floor(roundedMinutes / 60);
	const remainingMinutes = roundedMinutes % 60;
	return remainingMinutes ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

function createItem(seed: CatalogSeed): ItemDefinition {
	const rarity = raritySettings[seed.rarity];
	const perishable =
		["hortifruti", "laticinios", "padaria", "carnes", "frios"].includes(
			seed.category,
		) ||
		(seed.acquisition === "production" &&
			["bebidas", "congelados"].includes(seed.category));

	return {
		acquisition: seed.acquisition ?? "supplier",
		category: seed.category,
		demand: seed.demand ?? 50,
		expirationHours: perishable ? 48 : null,
		id: seed.id,
		maxPrice: Math.round(seed.sellingPrice * 1.3),
		minPrice: Math.round(seed.sellingPrice * 0.75),
		name: seed.name,
		popularity: seed.popularity ?? 50,
		preferredCustomers: seed.preferredCustomers ?? ["normal"],
		profitPerUnit: seed.sellingPrice - seed.purchasePrice,
		purchasePrice: seed.purchasePrice,
		rarity: seed.rarity,
		recommendedStock: Math.max(3, Math.round((seed.demand ?? 50) / 8)),
		restockFrequency:
			(seed.demand ?? 50) >= 70
				? "alta"
				: (seed.demand ?? 50) >= 35
					? "media"
					: "baixa",
		reputation: rarity.reputation,
		saleVelocity: rarity.saleVelocity,
		sellingPrice: seed.sellingPrice,
		shelfId: seed.shelfId,
		shelfSpace:
			seed.rarity === "luxo" || seed.rarity === "colecionavel" ? 2 : 1,
		spoilChance: perishable ? 0.04 + (100 - (seed.demand ?? 50)) / 2500 : 0,
		supplierQuantity: 1,
		supplierTime: getSupplierTime(
			seed.unlockLevel,
			seed.sellingPrice - seed.purchasePrice,
		),
		suggestedPrice: seed.sellingPrice,
		unlockLevel: seed.unlockLevel,
		visualAttractiveness: rarity.visualAttractiveness,
		xpPerSale: seed.xpPerSale ?? rarity.xpPerSale,
	};
}

const catalogSeeds: CatalogSeed[] = [
	{
		id: 1,
		name: "Tomate",

		category: "hortifruti",
		purchasePrice: 12,
		sellingPrice: 18,
		rarity: "comum",
		unlockLevel: 1,
		demand: 74,
		popularity: 72,
		preferredCustomers: ["familia", "normal"],
		shelfId: "produce",
		xpPerSale: 6,
	},
	{
		id: 2,
		name: "Brócolis",

		category: "hortifruti",
		purchasePrice: 16,
		sellingPrice: 24,
		rarity: "incomum",
		unlockLevel: 2,
		demand: 48,
		popularity: 45,
		preferredCustomers: ["premium", "normal"],
	},
	{
		id: 3,
		name: "Cenoura",

		category: "hortifruti",
		purchasePrice: 8,
		sellingPrice: 12,
		rarity: "comum",
		unlockLevel: 2,
		demand: 70,
		popularity: 66,
		preferredCustomers: ["familia", "economico"],
	},
	{
		id: 4,
		name: "Pimentão",

		category: "hortifruti",
		purchasePrice: 13,
		sellingPrice: 20,
		rarity: "incomum",
		unlockLevel: 3,
		demand: 42,
		popularity: 40,
		preferredCustomers: ["normal", "premium"],
	},
	{
		id: 5,
		name: "Leite integral",

		category: "laticinios",
		purchasePrice: 23,
		sellingPrice: 32,
		rarity: "comum",
		unlockLevel: 1,
		demand: 92,
		popularity: 91,
		preferredCustomers: ["familia", "normal"],
		shelfId: "dairy",
		xpPerSale: 10,
	},
	{
		id: 6,
		name: "Queijo prato",

		category: "queijos",
		purchasePrice: 42,
		sellingPrice: 60,
		rarity: "incomum",
		unlockLevel: 3,
		demand: 52,
		popularity: 54,
		preferredCustomers: ["familia", "premium"],
	},
	{
		id: 7,
		name: "Manteiga",

		category: "laticinios",
		purchasePrice: 34,
		sellingPrice: 48,
		rarity: "incomum",
		unlockLevel: 3,
		demand: 46,
		popularity: 48,
		preferredCustomers: ["familia", "normal"],
	},
	{
		id: 8,
		name: "Iogurte",

		category: "laticinios",
		purchasePrice: 28,
		sellingPrice: 38,
		rarity: "incomum",
		unlockLevel: 4,
		demand: 57,
		popularity: 58,
		preferredCustomers: ["normal", "premium"],
	},
	{
		id: 9,
		name: "Pão francês",

		category: "padaria",
		purchasePrice: 5,
		sellingPrice: 8,
		rarity: "comum",
		unlockLevel: 1,
		demand: 96,
		popularity: 94,
		preferredCustomers: ["familia", "economico"],
		shelfId: "bakery",
		xpPerSale: 4,
	},
	{
		id: 10,
		name: "Croissant",

		category: "padaria",
		purchasePrice: 28,
		sellingPrice: 42,
		rarity: "incomum",
		unlockLevel: 4,
		demand: 40,
		popularity: 46,
		preferredCustomers: ["premium", "impulsivo"],
	},
	{
		id: 11,
		name: "Bolo artesanal",

		category: "doces",
		purchasePrice: 72,
		sellingPrice: 120,
		rarity: "raro",
		unlockLevel: 6,
		demand: 25,
		popularity: 38,
		preferredCustomers: ["premium", "familia"],
	},
	{
		id: 12,
		name: "Waffle",

		category: "doces",
		purchasePrice: 18,
		sellingPrice: 28,
		rarity: "incomum",
		unlockLevel: 1,
		demand: 54,
		popularity: 61,
		preferredCustomers: ["impulsivo", "normal"],
		shelfId: "snacks",
	},
	{
		id: 13,
		name: "Suco natural",

		category: "bebidas",
		purchasePrice: 14,
		sellingPrice: 22,
		rarity: "comum",
		unlockLevel: 1,
		demand: 68,
		popularity: 70,
		preferredCustomers: ["normal", "premium"],
		shelfId: "drinks",
		xpPerSale: 6,
	},
	{
		id: 14,
		name: "Refrigerante",

		category: "refrigerantes",
		purchasePrice: 11,
		sellingPrice: 18,
		rarity: "comum",
		unlockLevel: 2,
		demand: 84,
		popularity: 86,
		preferredCustomers: ["impulsivo", "economico"],
	},
	{
		id: 15,
		name: "Café especial",

		category: "bebidas",
		purchasePrice: 20,
		sellingPrice: 30,
		rarity: "incomum",
		unlockLevel: 1,
		demand: 58,
		popularity: 62,
		preferredCustomers: ["premium", "normal"],
		shelfId: "coffee",
		xpPerSale: 8,
	},
	{
		id: 16,
		name: "Chá relaxante",

		category: "bebidas",
		purchasePrice: 13,
		sellingPrice: 20,
		rarity: "comum",
		unlockLevel: 3,
		demand: 38,
		popularity: 42,
		preferredCustomers: ["normal", "premium"],
	},
	{
		id: 17,
		name: "Pizza congelada",

		category: "congelados",
		purchasePrice: 55,
		sellingPrice: 85,
		rarity: "raro",
		unlockLevel: 1,
		demand: 50,
		popularity: 64,
		preferredCustomers: ["familia", "impulsivo"],
		shelfId: "pizza",
		xpPerSale: 18,
	},
	{
		id: 18,
		name: "Pastel congelado",

		category: "congelados",
		purchasePrice: 31,
		sellingPrice: 50,
		rarity: "incomum",
		unlockLevel: 5,
		demand: 47,
		popularity: 53,
		preferredCustomers: ["impulsivo", "familia"],
	},
	{
		id: 19,
		name: "Lasanha premium",

		category: "congelados",
		purchasePrice: 84,
		sellingPrice: 140,
		rarity: "raro",
		unlockLevel: 7,
		demand: 27,
		popularity: 42,
		preferredCustomers: ["premium", "familia"],
	},
	{
		id: 20,
		name: "Batata frita",

		category: "congelados",
		purchasePrice: 22,
		sellingPrice: 35,
		rarity: "comum",
		unlockLevel: 4,
		demand: 71,
		popularity: 77,
		preferredCustomers: ["impulsivo", "economico"],
	},
	{
		id: 21,
		name: "Água mineral",

		category: "aguas",
		purchasePrice: 4,
		sellingPrice: 7,
		rarity: "comum",
		unlockLevel: 2,
		demand: 98,
		popularity: 92,
		preferredCustomers: ["normal", "economico"],
		xpPerSale: 3,
	},
	{
		id: 22,
		name: "Energético",

		category: "energeticos",
		purchasePrice: 19,
		sellingPrice: 32,
		rarity: "incomum",
		unlockLevel: 5,
		demand: 62,
		popularity: 74,
		preferredCustomers: ["impulsivo", "premium"],
	},
	{
		id: 23,
		name: "Bala de gelatina",

		category: "doces",
		purchasePrice: 6,
		sellingPrice: 13,
		rarity: "comum",
		unlockLevel: 2,
		demand: 79,
		popularity: 83,
		preferredCustomers: ["impulsivo", "economico"],
	},
	{
		id: 24,
		name: "Chocolate premium",

		category: "chocolates",
		purchasePrice: 46,
		sellingPrice: 78,
		rarity: "raro",
		unlockLevel: 8,
		demand: 30,
		popularity: 58,
		preferredCustomers: ["premium", "impulsivo"],
	},
	{
		id: 25,
		name: "Bolacha recheada",

		category: "bolachas",
		purchasePrice: 9,
		sellingPrice: 17,
		rarity: "comum",
		unlockLevel: 3,
		demand: 76,
		popularity: 80,
		preferredCustomers: ["impulsivo", "economico"],
	},
	{
		id: 26,
		name: "Macarrão italiano",

		category: "massas",
		purchasePrice: 15,
		sellingPrice: 28,
		rarity: "incomum",
		unlockLevel: 5,
		demand: 65,
		popularity: 61,
		preferredCustomers: ["familia", "normal"],
	},
	{
		id: 27,
		name: "Carne nobre",

		category: "carnes",
		purchasePrice: 110,
		sellingPrice: 185,
		rarity: "epico",
		unlockLevel: 10,
		demand: 22,
		popularity: 48,
		preferredCustomers: ["premium"],
	},
	{
		id: 28,
		name: "Presunto defumado",

		category: "frios",
		purchasePrice: 38,
		sellingPrice: 64,
		rarity: "raro",
		unlockLevel: 7,
		demand: 44,
		popularity: 55,
		preferredCustomers: ["familia", "premium"],
	},
	{
		id: 29,
		name: "Cesta orgânica",

		category: "organicos",
		purchasePrice: 76,
		sellingPrice: 125,
		rarity: "raro",
		unlockLevel: 9,
		demand: 36,
		popularity: 66,
		preferredCustomers: ["premium", "normal"],
	},
	{
		id: 30,
		name: "Granola premium",

		category: "premium",
		purchasePrice: 58,
		sellingPrice: 96,
		rarity: "epico",
		unlockLevel: 11,
		demand: 28,
		popularity: 57,
		preferredCustomers: ["premium"],
	},
	{
		id: 31,
		name: "Vinho importado",

		category: "importados",
		purchasePrice: 130,
		sellingPrice: 230,
		rarity: "lendario",
		unlockLevel: 13,
		demand: 14,
		popularity: 62,
		preferredCustomers: ["premium"],
	},
	{
		id: 32,
		name: "Trufa gourmet",

		category: "gourmet",
		purchasePrice: 92,
		sellingPrice: 165,
		rarity: "epico",
		unlockLevel: 14,
		demand: 18,
		popularity: 72,
		preferredCustomers: ["premium", "impulsivo"],
	},
	{
		id: 33,
		name: "Champanhe reserva",

		category: "luxo",
		purchasePrice: 260,
		sellingPrice: 480,
		rarity: "luxo",
		unlockLevel: 17,
		demand: 7,
		popularity: 75,
		preferredCustomers: ["premium"],
	},
	{
		id: 34,
		name: "Shampoo",

		category: "higiene",
		purchasePrice: 18,
		sellingPrice: 31,
		rarity: "incomum",
		unlockLevel: 6,
		demand: 59,
		popularity: 63,
		preferredCustomers: ["familia", "normal"],
	},
	{
		id: 35,
		name: "Detergente",

		category: "limpeza",
		purchasePrice: 10,
		sellingPrice: 18,
		rarity: "comum",
		unlockLevel: 4,
		demand: 73,
		popularity: 70,
		preferredCustomers: ["familia", "economico"],
	},
	{
		id: 36,
		name: "Ração premium",

		category: "pets",
		purchasePrice: 45,
		sellingPrice: 76,
		rarity: "raro",
		unlockLevel: 8,
		demand: 39,
		popularity: 55,
		preferredCustomers: ["familia", "premium"],
	},
	{
		id: 37,
		name: "Fralda",

		category: "bebes",
		purchasePrice: 62,
		sellingPrice: 102,
		rarity: "raro",
		unlockLevel: 9,
		demand: 45,
		popularity: 60,
		preferredCustomers: ["familia"],
	},
	{
		id: 38,
		name: "Pilha portátil",

		category: "eletronicos",
		purchasePrice: 28,
		sellingPrice: 52,
		rarity: "incomum",
		unlockLevel: 10,
		demand: 31,
		popularity: 49,
		preferredCustomers: ["normal", "premium"],
	},
	{
		id: 39,
		name: "Caderno",

		category: "papelaria",
		purchasePrice: 12,
		sellingPrice: 24,
		rarity: "comum",
		unlockLevel: 5,
		demand: 52,
		popularity: 56,
		preferredCustomers: ["normal", "economico"],
	},
	{
		id: 40,
		name: "Refeição pronta",

		category: "conveniencia",
		purchasePrice: 24,
		sellingPrice: 44,
		rarity: "incomum",
		unlockLevel: 6,
		demand: 69,
		popularity: 72,
		preferredCustomers: ["premium", "impulsivo"],
	},
	{
		id: 41,
		name: "Panetone",

		category: "sazonais",
		purchasePrice: 50,
		sellingPrice: 95,
		rarity: "raro",
		unlockLevel: 12,
		demand: 34,
		popularity: 78,
		preferredCustomers: ["familia", "premium"],
	},
	{
		id: 42,
		name: "Café colecionável",

		category: "colecionaveis",
		purchasePrice: 350,
		sellingPrice: 700,
		rarity: "colecionavel",
		unlockLevel: 20,
		demand: 3,
		popularity: 88,
		preferredCustomers: ["premium"],
	},
	{
		id: 43,
		name: "Farinha de trigo",

		category: "padaria",
		purchasePrice: 8,
		sellingPrice: 14,
		rarity: "comum",
		unlockLevel: 1,
		demand: 72,
		popularity: 58,
		preferredCustomers: ["familia", "economico"],
	},
	{
		id: 44,
		name: "Peixe fresco",

		category: "peixes",
		purchasePrice: 42,
		sellingPrice: 60,
		rarity: "raro",
		unlockLevel: 14,
		demand: 38,
		popularity: 58,
		preferredCustomers: ["premium", "familia"],
	},
	{
		id: 45,
		name: "Camarão fresco",

		category: "peixes",
		purchasePrice: 65,
		sellingPrice: 95,
		rarity: "epico",
		unlockLevel: 17,
		demand: 24,
		popularity: 66,
		preferredCustomers: ["premium"],
	},
	{
		id: 101,
		name: "Baguete rústica",

		category: "padaria",
		purchasePrice: 13,
		sellingPrice: 30,
		rarity: "incomum",
		unlockLevel: 2,
		demand: 68,
		popularity: 76,
		preferredCustomers: ["familia", "normal"],
		xpPerSale: 6,
		acquisition: "production",
	},
	{
		id: 102,
		name: "Croissant premium",

		category: "padaria",
		purchasePrice: 25,
		sellingPrice: 43,
		rarity: "raro",
		unlockLevel: 3,
		demand: 52,
		popularity: 82,
		preferredCustomers: ["premium", "impulsivo"],
		xpPerSale: 14,
		acquisition: "production",
	},
	{
		id: 103,
		name: "Bolo de vitrine",

		category: "doces",
		purchasePrice: 71,
		sellingPrice: 102,
		rarity: "epico",
		unlockLevel: 6,
		demand: 30,
		popularity: 88,
		preferredCustomers: ["premium", "familia"],
		xpPerSale: 30,
		acquisition: "production",
	},
	{
		id: 104,
		name: "Queijo minas artesanal",

		category: "queijos",
		purchasePrice: 23,
		sellingPrice: 54,
		rarity: "incomum",
		unlockLevel: 6,
		demand: 60,
		popularity: 72,
		preferredCustomers: ["familia", "normal"],
		xpPerSale: 7,
		acquisition: "production",
	},
	{
		id: 105,
		name: "Brie maturado",

		category: "queijos",
		purchasePrice: 44,
		sellingPrice: 78,
		rarity: "raro",
		unlockLevel: 8,
		demand: 40,
		popularity: 80,
		preferredCustomers: ["premium"],
		xpPerSale: 18,
		acquisition: "production",
	},
	{
		id: 106,
		name: "Tábua de queijos",

		category: "gourmet",
		purchasePrice: 128,
		sellingPrice: 182,
		rarity: "lendario",
		unlockLevel: 13,
		demand: 16,
		popularity: 92,
		preferredCustomers: ["premium"],
		xpPerSale: 38,
		acquisition: "production",
	},
	{
		id: 107,
		name: "Hambúrguer artesanal",

		category: "carnes",
		purchasePrice: 34,
		sellingPrice: 78,
		rarity: "raro",
		unlockLevel: 10,
		demand: 58,
		popularity: 86,
		preferredCustomers: ["familia", "impulsivo"],
		xpPerSale: 10,
		acquisition: "production",
	},
	{
		id: 108,
		name: "Corte dry-aged",

		category: "carnes",
		purchasePrice: 129,
		sellingPrice: 230,
		rarity: "epico",
		unlockLevel: 12,
		demand: 24,
		popularity: 84,
		preferredCustomers: ["premium"],
		xpPerSale: 25,
		acquisition: "production",
	},
	{
		id: 109,
		name: "Kit churrasco premium",

		category: "carnes",
		purchasePrice: 162,
		sellingPrice: 230,
		rarity: "lendario",
		unlockLevel: 16,
		demand: 18,
		popularity: 94,
		preferredCustomers: ["premium", "familia"],
		xpPerSale: 48,
		acquisition: "production",
	},
	{
		id: 110,
		name: "Filé de peixe fresco",

		category: "peixes",
		purchasePrice: 23,
		sellingPrice: 55,
		rarity: "raro",
		unlockLevel: 16,
		demand: 54,
		popularity: 78,
		preferredCustomers: ["familia", "premium"],
		xpPerSale: 12,
		acquisition: "production",
	},
	{
		id: 111,
		name: "Sushi especial",

		category: "gourmet",
		purchasePrice: 31,
		sellingPrice: 57,
		rarity: "epico",
		unlockLevel: 18,
		demand: 36,
		popularity: 90,
		preferredCustomers: ["premium", "impulsivo"],
		xpPerSale: 26,
		acquisition: "production",
	},
	{
		id: 112,
		name: "Barco de frutos do mar",

		category: "luxo",
		purchasePrice: 152,
		sellingPrice: 218,
		rarity: "luxo",
		unlockLevel: 22,
		demand: 10,
		popularity: 98,
		preferredCustomers: ["premium"],
		xpPerSale: 54,
		acquisition: "production",
	},
	{
		id: 113,
		name: "Suco gelado da casa",
		category: "bebidas",
		purchasePrice: 12,
		sellingPrice: 25,
		rarity: "incomum",
		unlockLevel: 12,
		demand: 67,
		popularity: 78,
		preferredCustomers: ["normal", "familia"],
		acquisition: "production",
	},
	{
		id: 114,
		name: "Chá gelado artesanal",
		category: "bebidas",
		purchasePrice: 14,
		sellingPrice: 29,
		rarity: "raro",
		unlockLevel: 15,
		demand: 48,
		popularity: 75,
		preferredCustomers: ["normal", "premium"],
		acquisition: "production",
	},
	{
		id: 115,
		name: "Vitamina cremosa",
		category: "bebidas",
		purchasePrice: 33,
		sellingPrice: 55,
		rarity: "epico",
		unlockLevel: 18,
		demand: 41,
		popularity: 84,
		preferredCustomers: ["familia", "premium"],
		acquisition: "production",
	},
	{
		id: 116,
		name: "Sorvete de creme",
		category: "congelados",
		purchasePrice: 24,
		sellingPrice: 43,
		rarity: "raro",
		unlockLevel: 24,
		demand: 69,
		popularity: 89,
		preferredCustomers: ["familia", "impulsivo"],
		acquisition: "production",
	},
	{
		id: 117,
		name: "Sundae de chocolate",
		category: "doces",
		purchasePrice: 55,
		sellingPrice: 89,
		rarity: "epico",
		unlockLevel: 26,
		demand: 40,
		popularity: 92,
		preferredCustomers: ["familia", "premium"],
		acquisition: "production",
	},
	{
		id: 118,
		name: "Pote de sorvete família",
		category: "congelados",
		purchasePrice: 58,
		sellingPrice: 98,
		rarity: "lendario",
		unlockLevel: 28,
		demand: 35,
		popularity: 90,
		preferredCustomers: ["familia", "premium"],
		acquisition: "production",
	},
	{
		id: 119,
		name: "Vinho tinto da casa",
		category: "bebidas",
		purchasePrice: 30,
		sellingPrice: 58,
		rarity: "raro",
		unlockLevel: 20,
		demand: 52,
		popularity: 80,
		preferredCustomers: ["normal", "premium"],
		acquisition: "production",
	},
	{
		id: 120,
		name: "Sangria da casa",
		category: "bebidas",
		purchasePrice: 48,
		sellingPrice: 86,
		rarity: "epico",
		unlockLevel: 21,
		demand: 44,
		popularity: 86,
		preferredCustomers: ["familia", "premium"],
		acquisition: "production",
	},
	{
		id: 121,
		name: "Kit harmonização",
		category: "gourmet",
		purchasePrice: 190,
		sellingPrice: 320,
		rarity: "lendario",
		unlockLevel: 23,
		demand: 30,
		popularity: 94,
		preferredCustomers: ["premium"],
		acquisition: "production",
	},
];

const baseItemCatalog = catalogSeeds.map(createItem);

export const itemCatalog = balanceCraftedProductEconomy(baseItemCatalog);

function balanceCraftedProductEconomy(catalog: ItemDefinition[]) {
	let balancedCatalog = catalog;

	for (let pass = 0; pass < productionRecipes.length; pass += 1) {
		balancedCatalog = balancedCatalog.map((product) => {
			const recipe = productionRecipes.find(
				(item) => item.outputProductId === product.id,
			);

			if (!recipe) {
				return product;
			}

			const ingredientPurchaseCost = recipe.ingredients.reduce(
				(total, ingredient) => {
					const ingredientProduct = balancedCatalog.find(
						(item) => item.id === ingredient.productId,
					);

					return (
						total +
						(ingredientProduct?.purchasePrice ?? 0) * ingredient.quantity
					);
				},
				0,
			);
			const ingredientSaleValue = recipe.ingredients.reduce(
				(total, ingredient) => {
					const ingredientProduct = balancedCatalog.find(
						(item) => item.id === ingredient.productId,
					);

					return (
						total + (ingredientProduct?.sellingPrice ?? 0) * ingredient.quantity
					);
				},
				0,
			);
			const productionUnitCost = Math.ceil(
				ingredientPurchaseCost / recipe.outputQuantity,
			);
			const minimumCraftedBatchRevenue =
				Math.floor(ingredientSaleValue * 1.08) + 1;
			const sellingPrice = Math.max(
				product.sellingPrice,
				Math.ceil(minimumCraftedBatchRevenue / recipe.outputQuantity),
			);

			return {
				...product,
				maxPrice: Math.round(sellingPrice * 1.3),
				minPrice: Math.round(sellingPrice * 0.75),
				profitPerUnit: sellingPrice - productionUnitCost,
				purchasePrice: productionUnitCost,
				sellingPrice,
				supplierTime: getSupplierTime(
					product.unlockLevel,
					sellingPrice - productionUnitCost,
				),
				suggestedPrice: sellingPrice,
			};
		});
	}

	return balancedCatalog;
}

export const marketProducts = itemCatalog
	.filter((product): product is ItemDefinition & { shelfId: string } =>
		Boolean(product.shelfId),
	)
	.map((product) => ({
		...product,
		experience: product.xpPerSale,
		marketPrice: product.suggestedPrice,
		necessity: product.demand,
		productId: product.id,
	}));

export const productionProducts = itemCatalog.filter(
	(product) => product.acquisition === "production",
);

// The shop opens with two shelves and the drinks cooler: they come first, the rest unlock in this order.
const shelfOrder = ["produce", "dairy", "drinks"];
const shelfRank = (shelfId: string) => {
	const rank = shelfOrder.indexOf(shelfId);
	return rank < 0 ? shelfOrder.length : rank;
};
const orderedShelfProducts = marketProducts
	.map((product, index) => ({ product, index }))
	.sort(
		(a, b) =>
			shelfRank(a.product.shelfId) - shelfRank(b.product.shelfId) ||
			a.index - b.index,
	)
	.map(({ product }) => product);

export const shelves: StoreShelf[] = orderedShelfProducts.map((product, index) => ({
	id: product.shelfId,
	name: product.shelfId === "drinks" ? "Geladeira de bebidas" : `Prateleira ${index + 1}`,
}));

/** Shelves the player owns on a new game (placed by the player in build mode). */
export const starterShelfIds = shelfOrder;

export const initialShelfAssignments = Object.fromEntries(
	marketProducts.map((product, index) => [
		product.shelfId,
		index < 4 || starterShelfIds.includes(product.shelfId) ? product.id : null,
	]),
);

export function getUnlockedProductIds(level: number) {
	return itemCatalog
		.filter((product) => product.unlockLevel <= level)
		.map((product) => product.id);
}

export type MarketProduct = (typeof marketProducts)[number];
