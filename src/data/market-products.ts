import type { ItemDefinition, ItemRarity } from "@/@types/item";
import type { StoreShelf } from "@/@types/store";

export const itemCategories = [
	{ id: "hortifruti", label: "Hortifruti", emoji: "🥬" },
	{ id: "laticinios", label: "Laticínios", emoji: "🧀" },
	{ id: "padaria", label: "Padaria", emoji: "🥖" },
	{ id: "bebidas", label: "Bebidas", emoji: "🧃" },
	{ id: "refrigerantes", label: "Refrigerantes", emoji: "🥤" },
	{ id: "aguas", label: "Águas", emoji: "💧" },
	{ id: "energeticos", label: "Energéticos", emoji: "⚡" },
	{ id: "doces", label: "Doces", emoji: "🍬" },
	{ id: "chocolates", label: "Chocolates", emoji: "🍫" },
	{ id: "bolachas", label: "Bolachas", emoji: "🍪" },
	{ id: "massas", label: "Massas", emoji: "🍝" },
	{ id: "congelados", label: "Congelados", emoji: "🧊" },
	{ id: "carnes", label: "Carnes", emoji: "🥩" },
	{ id: "frios", label: "Frios", emoji: "🥓" },
	{ id: "queijos", label: "Queijos", emoji: "🧀" },
	{ id: "organicos", label: "Orgânicos", emoji: "🌱" },
	{ id: "premium", label: "Premium", emoji: "✨" },
	{ id: "importados", label: "Importados", emoji: "🌍" },
	{ id: "gourmet", label: "Gourmet", emoji: "🍽️" },
	{ id: "luxo", label: "Luxo", emoji: "💎" },
	{ id: "higiene", label: "Higiene", emoji: "🧴" },
	{ id: "limpeza", label: "Limpeza", emoji: "🧼" },
	{ id: "pets", label: "Pets", emoji: "🐾" },
	{ id: "bebes", label: "Bebês", emoji: "🍼" },
	{ id: "eletronicos", label: "Eletrônicos", emoji: "🔌" },
	{ id: "papelaria", label: "Papelaria", emoji: "✏️" },
	{ id: "conveniencia", label: "Conveniência", emoji: "🛒" },
	{ id: "sazonais", label: "Sazonais", emoji: "🎁" },
] as const;

type CatalogSeed = Pick<
	ItemDefinition,
	| "category"
	| "emoji"
	| "id"
	| "name"
	| "purchasePrice"
	| "rarity"
	| "sellingPrice"
> & {
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
		| "reputation"
		| "saleVelocity"
		| "visualAttractiveness"
		| "xpPerSale"
	>
> = {
	comum: { reputation: 1, saleVelocity: "rapida", visualAttractiveness: 35, xpPerSale: 4 },
	incomum: { reputation: 2, saleVelocity: "media", visualAttractiveness: 50, xpPerSale: 7 },
	raro: { reputation: 4, saleVelocity: "media", visualAttractiveness: 65, xpPerSale: 12 },
	epico: { reputation: 7, saleVelocity: "lenta", visualAttractiveness: 78, xpPerSale: 20 },
	lendario: { reputation: 12, saleVelocity: "lenta", visualAttractiveness: 88, xpPerSale: 32 },
	luxo: { reputation: 20, saleVelocity: "lenta", visualAttractiveness: 96, xpPerSale: 48 },
	colecionavel: { reputation: 28, saleVelocity: "lenta", visualAttractiveness: 100, xpPerSale: 70 },
};

function createItem(seed: CatalogSeed): ItemDefinition {
	const rarity = raritySettings[seed.rarity];
	const perishable = ["hortifruti", "laticinios", "padaria", "carnes", "frios"].includes(
		seed.category,
	);

	return {
		category: seed.category,
		demand: seed.demand ?? 50,
		emoji: seed.emoji,
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
		shelfSpace: seed.rarity === "luxo" || seed.rarity === "colecionavel" ? 2 : 1,
		spoilChance: perishable ? 0.04 + (100 - (seed.demand ?? 50)) / 2500 : 0,
		supplierQuantity: Math.max(2, Math.round((seed.demand ?? 50) / 10)),
		supplierTime: perishable ? "4m" : "8m",
		suggestedPrice: seed.sellingPrice,
		unlockLevel: seed.unlockLevel,
		visualAttractiveness: rarity.visualAttractiveness,
		xpPerSale: seed.xpPerSale ?? rarity.xpPerSale,
	};
}

const catalogSeeds: CatalogSeed[] = [
	{ id: 1, name: "Tomate", emoji: "🍅", category: "hortifruti", purchasePrice: 12, sellingPrice: 18, rarity: "comum", unlockLevel: 1, demand: 74, popularity: 72, preferredCustomers: ["familia", "normal"], shelfId: "produce", xpPerSale: 6 },
	{ id: 2, name: "Brócolis", emoji: "🥦", category: "hortifruti", purchasePrice: 16, sellingPrice: 24, rarity: "incomum", unlockLevel: 2, demand: 48, popularity: 45, preferredCustomers: ["premium", "normal"] },
	{ id: 3, name: "Cenoura", emoji: "🥕", category: "hortifruti", purchasePrice: 8, sellingPrice: 12, rarity: "comum", unlockLevel: 2, demand: 70, popularity: 66, preferredCustomers: ["familia", "economico"] },
	{ id: 4, name: "Pimentão", emoji: "🫑", category: "hortifruti", purchasePrice: 13, sellingPrice: 20, rarity: "incomum", unlockLevel: 3, demand: 42, popularity: 40, preferredCustomers: ["normal", "premium"] },
	{ id: 5, name: "Leite integral", emoji: "🥛", category: "laticinios", purchasePrice: 23, sellingPrice: 32, rarity: "comum", unlockLevel: 1, demand: 92, popularity: 91, preferredCustomers: ["familia", "normal"], shelfId: "dairy", xpPerSale: 10 },
	{ id: 6, name: "Queijo prato", emoji: "🧀", category: "queijos", purchasePrice: 42, sellingPrice: 60, rarity: "incomum", unlockLevel: 3, demand: 52, popularity: 54, preferredCustomers: ["familia", "premium"] },
	{ id: 7, name: "Manteiga", emoji: "🧈", category: "laticinios", purchasePrice: 34, sellingPrice: 48, rarity: "incomum", unlockLevel: 3, demand: 46, popularity: 48, preferredCustomers: ["familia", "normal"] },
	{ id: 8, name: "Iogurte", emoji: "🍦", category: "laticinios", purchasePrice: 28, sellingPrice: 38, rarity: "incomum", unlockLevel: 4, demand: 57, popularity: 58, preferredCustomers: ["normal", "premium"] },
	{ id: 9, name: "Pão francês", emoji: "🥖", category: "padaria", purchasePrice: 5, sellingPrice: 8, rarity: "comum", unlockLevel: 1, demand: 96, popularity: 94, preferredCustomers: ["familia", "economico"], shelfId: "bakery", xpPerSale: 4 },
	{ id: 10, name: "Croissant", emoji: "🥐", category: "padaria", purchasePrice: 28, sellingPrice: 42, rarity: "incomum", unlockLevel: 4, demand: 40, popularity: 46, preferredCustomers: ["premium", "impulsivo"] },
	{ id: 11, name: "Bolo artesanal", emoji: "🎂", category: "doces", purchasePrice: 72, sellingPrice: 120, rarity: "raro", unlockLevel: 6, demand: 25, popularity: 38, preferredCustomers: ["premium", "familia"] },
	{ id: 12, name: "Waffle", emoji: "🧇", category: "doces", purchasePrice: 18, sellingPrice: 28, rarity: "incomum", unlockLevel: 1, demand: 54, popularity: 61, preferredCustomers: ["impulsivo", "normal"], shelfId: "snacks" },
	{ id: 13, name: "Suco natural", emoji: "🧃", category: "bebidas", purchasePrice: 14, sellingPrice: 22, rarity: "comum", unlockLevel: 1, demand: 68, popularity: 70, preferredCustomers: ["normal", "premium"], shelfId: "drinks", xpPerSale: 6 },
	{ id: 14, name: "Refrigerante", emoji: "🥤", category: "refrigerantes", purchasePrice: 11, sellingPrice: 18, rarity: "comum", unlockLevel: 2, demand: 84, popularity: 86, preferredCustomers: ["impulsivo", "economico"] },
	{ id: 15, name: "Café especial", emoji: "☕", category: "bebidas", purchasePrice: 20, sellingPrice: 30, rarity: "incomum", unlockLevel: 1, demand: 58, popularity: 62, preferredCustomers: ["premium", "normal"], shelfId: "coffee", xpPerSale: 8 },
	{ id: 16, name: "Chá relaxante", emoji: "🍵", category: "bebidas", purchasePrice: 13, sellingPrice: 20, rarity: "comum", unlockLevel: 3, demand: 38, popularity: 42, preferredCustomers: ["normal", "premium"] },
	{ id: 17, name: "Pizza congelada", emoji: "🍕", category: "congelados", purchasePrice: 55, sellingPrice: 85, rarity: "raro", unlockLevel: 1, demand: 50, popularity: 64, preferredCustomers: ["familia", "impulsivo"], shelfId: "pizza", xpPerSale: 18 },
	{ id: 18, name: "Pastel congelado", emoji: "🥟", category: "congelados", purchasePrice: 31, sellingPrice: 50, rarity: "incomum", unlockLevel: 5, demand: 47, popularity: 53, preferredCustomers: ["impulsivo", "familia"] },
	{ id: 19, name: "Lasanha premium", emoji: "🫕", category: "congelados", purchasePrice: 84, sellingPrice: 140, rarity: "raro", unlockLevel: 7, demand: 27, popularity: 42, preferredCustomers: ["premium", "familia"] },
	{ id: 20, name: "Batata frita", emoji: "🍟", category: "congelados", purchasePrice: 22, sellingPrice: 35, rarity: "comum", unlockLevel: 4, demand: 71, popularity: 77, preferredCustomers: ["impulsivo", "economico"] },
	{ id: 21, name: "Água mineral", emoji: "💧", category: "aguas", purchasePrice: 4, sellingPrice: 7, rarity: "comum", unlockLevel: 2, demand: 98, popularity: 92, preferredCustomers: ["normal", "economico"], xpPerSale: 3 },
	{ id: 22, name: "Energético", emoji: "⚡", category: "energeticos", purchasePrice: 19, sellingPrice: 32, rarity: "incomum", unlockLevel: 5, demand: 62, popularity: 74, preferredCustomers: ["impulsivo", "premium"] },
	{ id: 23, name: "Bala de gelatina", emoji: "🍬", category: "doces", purchasePrice: 6, sellingPrice: 13, rarity: "comum", unlockLevel: 2, demand: 79, popularity: 83, preferredCustomers: ["impulsivo", "economico"] },
	{ id: 24, name: "Chocolate premium", emoji: "🍫", category: "chocolates", purchasePrice: 46, sellingPrice: 78, rarity: "raro", unlockLevel: 8, demand: 30, popularity: 58, preferredCustomers: ["premium", "impulsivo"] },
	{ id: 25, name: "Bolacha recheada", emoji: "🍪", category: "bolachas", purchasePrice: 9, sellingPrice: 17, rarity: "comum", unlockLevel: 3, demand: 76, popularity: 80, preferredCustomers: ["impulsivo", "economico"] },
	{ id: 26, name: "Macarrão italiano", emoji: "🍝", category: "massas", purchasePrice: 15, sellingPrice: 28, rarity: "incomum", unlockLevel: 5, demand: 65, popularity: 61, preferredCustomers: ["familia", "normal"] },
	{ id: 27, name: "Carne nobre", emoji: "🥩", category: "carnes", purchasePrice: 110, sellingPrice: 185, rarity: "epico", unlockLevel: 10, demand: 22, popularity: 48, preferredCustomers: ["premium"] },
	{ id: 28, name: "Presunto defumado", emoji: "🥓", category: "frios", purchasePrice: 38, sellingPrice: 64, rarity: "raro", unlockLevel: 7, demand: 44, popularity: 55, preferredCustomers: ["familia", "premium"] },
	{ id: 29, name: "Cesta orgânica", emoji: "🌱", category: "organicos", purchasePrice: 76, sellingPrice: 125, rarity: "raro", unlockLevel: 9, demand: 36, popularity: 66, preferredCustomers: ["premium", "normal"] },
	{ id: 30, name: "Granola premium", emoji: "✨", category: "premium", purchasePrice: 58, sellingPrice: 96, rarity: "epico", unlockLevel: 11, demand: 28, popularity: 57, preferredCustomers: ["premium"] },
	{ id: 31, name: "Vinho importado", emoji: "🍷", category: "importados", purchasePrice: 130, sellingPrice: 230, rarity: "lendario", unlockLevel: 13, demand: 14, popularity: 62, preferredCustomers: ["premium"] },
	{ id: 32, name: "Trufa gourmet", emoji: "🍬", category: "gourmet", purchasePrice: 92, sellingPrice: 165, rarity: "epico", unlockLevel: 14, demand: 18, popularity: 72, preferredCustomers: ["premium", "impulsivo"] },
	{ id: 33, name: "Champanhe reserva", emoji: "🍾", category: "luxo", purchasePrice: 260, sellingPrice: 480, rarity: "luxo", unlockLevel: 17, demand: 7, popularity: 75, preferredCustomers: ["premium"] },
	{ id: 34, name: "Shampoo", emoji: "🧴", category: "higiene", purchasePrice: 18, sellingPrice: 31, rarity: "incomum", unlockLevel: 6, demand: 59, popularity: 63, preferredCustomers: ["familia", "normal"] },
	{ id: 35, name: "Detergente", emoji: "🧼", category: "limpeza", purchasePrice: 10, sellingPrice: 18, rarity: "comum", unlockLevel: 4, demand: 73, popularity: 70, preferredCustomers: ["familia", "economico"] },
	{ id: 36, name: "Ração premium", emoji: "🐾", category: "pets", purchasePrice: 45, sellingPrice: 76, rarity: "raro", unlockLevel: 8, demand: 39, popularity: 55, preferredCustomers: ["familia", "premium"] },
	{ id: 37, name: "Fralda", emoji: "🍼", category: "bebes", purchasePrice: 62, sellingPrice: 102, rarity: "raro", unlockLevel: 9, demand: 45, popularity: 60, preferredCustomers: ["familia"] },
	{ id: 38, name: "Pilha portátil", emoji: "🔋", category: "eletronicos", purchasePrice: 28, sellingPrice: 52, rarity: "incomum", unlockLevel: 10, demand: 31, popularity: 49, preferredCustomers: ["normal", "premium"] },
	{ id: 39, name: "Caderno", emoji: "📓", category: "papelaria", purchasePrice: 12, sellingPrice: 24, rarity: "comum", unlockLevel: 5, demand: 52, popularity: 56, preferredCustomers: ["normal", "economico"] },
	{ id: 40, name: "Refeição pronta", emoji: "🥡", category: "conveniencia", purchasePrice: 24, sellingPrice: 44, rarity: "incomum", unlockLevel: 6, demand: 69, popularity: 72, preferredCustomers: ["premium", "impulsivo"] },
	{ id: 41, name: "Panetone", emoji: "🎁", category: "sazonais", purchasePrice: 50, sellingPrice: 95, rarity: "raro", unlockLevel: 12, demand: 34, popularity: 78, preferredCustomers: ["familia", "premium"] },
	{ id: 42, name: "Café colecionável", emoji: "🏆", category: "colecionaveis", purchasePrice: 350, sellingPrice: 700, rarity: "colecionavel", unlockLevel: 20, demand: 3, popularity: 88, preferredCustomers: ["premium"] },
];

export const itemCatalog = catalogSeeds.map(createItem);

export const marketProducts = itemCatalog
	.filter((product): product is ItemDefinition & { shelfId: string } => Boolean(product.shelfId))
	.map((product) => ({
		...product,
		experience: product.xpPerSale,
		marketPrice: product.suggestedPrice,
		necessity: product.demand,
		productId: product.id,
	}));

export const shelves: StoreShelf[] = [
	...marketProducts.map((product) => ({
		id: product.shelfId,
		name: product.name,
		product: product.emoji,
		productId: product.id,
	})),
	{ id: "locked", locked: true },
];

export function getUnlockedProductIds(level: number) {
	return itemCatalog
		.filter((product) => product.unlockLevel <= level)
		.map((product) => product.id);
}

export type MarketProduct = (typeof marketProducts)[number];
