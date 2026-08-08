import type {
	CurrencyPack,
	CurrencyPackCategory,
} from "@/@types/currency-purchase";

// Coin tiers follow the upgrade curve from thousands to millions. Diamond tiers
// cover consumables (50-150) through permanent premium items (500-3,000).
export const currencyPacks: CurrencyPack[] = [
	{
		badge: "Começo rápido",
		category: "bundle",
		coins: 10_000,
		diamonds: 200,
		fallbackPrice: "€ 4,99",
		id: "bundle-starter",
		name: "Combo Mercadinho",
		productId: "com.checkout.currency.bundle.starter",
		tier: 1,
	},
	{
		badge: "Mais popular",
		category: "bundle",
		coins: 60_000,
		diamonds: 450,
		fallbackPrice: "€ 9,99",
		id: "bundle-growing",
		name: "Combo Mercado",
		productId: "com.checkout.currency.bundle.growing",
		tier: 2,
	},
	{
		badge: "Ótimo valor",
		category: "bundle",
		coins: 600_000,
		diamonds: 1_000,
		fallbackPrice: "€ 19,99",
		id: "bundle-supermarket",
		name: "Combo Supermercado",
		productId: "com.checkout.currency.bundle.supermarket",
		tier: 3,
	},
	{
		badge: "Magnata",
		category: "bundle",
		coins: 7_000_000,
		diamonds: 2_200,
		fallbackPrice: "€ 39,99",
		id: "bundle-tycoon",
		name: "Combo Magnata",
		productId: "com.checkout.currency.bundle.tycoon",
		tier: 4,
	},
	{
		badge: "Melhor valor",
		category: "bundle",
		coins: 80_000_000,
		diamonds: 5_000,
		fallbackPrice: "€ 79,99",
		id: "bundle-empire",
		name: "Combo Império",
		productId: "com.checkout.currency.bundle.empire",
		tier: 5,
	},
	{
		badge: "Essencial",
		category: "coins",
		coins: 5_000,
		diamonds: 0,
		fallbackPrice: "€ 1,99",
		id: "coins-pouch",
		name: "Bolsa de Moedas",
		productId: "com.checkout.currency.coins.pouch",
		tier: 1,
	},
	{
		badge: "Popular",
		category: "coins",
		coins: 25_000,
		diamonds: 0,
		fallbackPrice: "€ 4,99",
		id: "coins-sack",
		name: "Saco de Moedas",
		productId: "com.checkout.currency.coins.sack",
		tier: 2,
	},
	{
		badge: "Bom negócio",
		category: "coins",
		coins: 150_000,
		diamonds: 0,
		fallbackPrice: "€ 9,99",
		id: "coins-chest",
		name: "Baú de Moedas",
		productId: "com.checkout.currency.coins.chest",
		tier: 3,
	},
	{
		badge: "Grande estoque",
		category: "coins",
		coins: 1_500_000,
		diamonds: 0,
		fallbackPrice: "€ 19,99",
		id: "coins-vault",
		name: "Cofre de Moedas",
		productId: "com.checkout.currency.coins.vault",
		tier: 4,
	},
	{
		badge: "Reserva máxima",
		category: "coins",
		coins: 20_000_000,
		diamonds: 0,
		fallbackPrice: "€ 39,99",
		id: "coins-reserve",
		name: "Reserva de Moedas",
		productId: "com.checkout.currency.coins.reserve",
		tier: 5,
	},
	{
		badge: "Essencial",
		category: "diamonds",
		coins: 0,
		diamonds: 75,
		fallbackPrice: "€ 1,99",
		id: "diamonds-handful",
		name: "Punhado de Diamantes",
		productId: "com.checkout.currency.diamonds.handful",
		tier: 1,
	},
	{
		badge: "Popular",
		category: "diamonds",
		coins: 0,
		diamonds: 220,
		fallbackPrice: "€ 4,99",
		id: "diamonds-pouch",
		name: "Bolsa de Diamantes",
		productId: "com.checkout.currency.diamonds.pouch",
		tier: 2,
	},
	{
		badge: "Bom negócio",
		category: "diamonds",
		coins: 0,
		diamonds: 500,
		fallbackPrice: "€ 9,99",
		id: "diamonds-chest",
		name: "Baú de Diamantes",
		productId: "com.checkout.currency.diamonds.chest",
		tier: 3,
	},
	{
		badge: "Tesouro",
		category: "diamonds",
		coins: 0,
		diamonds: 1_100,
		fallbackPrice: "€ 19,99",
		id: "diamonds-vault",
		name: "Cofre de Diamantes",
		productId: "com.checkout.currency.diamonds.vault",
		tier: 4,
	},
	{
		badge: "Melhor valor",
		category: "diamonds",
		coins: 0,
		diamonds: 2_400,
		fallbackPrice: "€ 39,99",
		id: "diamonds-reserve",
		name: "Reserva de Diamantes",
		productId: "com.checkout.currency.diamonds.reserve",
		tier: 5,
	},
];

export const currencyPackSections: {
	category: CurrencyPackCategory;
	description: string;
	title: string;
}[] = [
	{
		category: "bundle",
		description: "Moedas e diamantes juntos, com o melhor custo-benefício.",

		title: "Combos",
	},
	{
		category: "coins",
		description: "Para estoque, equipamentos e expansão do mercado.",

		title: "Moedas",
	},
	{
		category: "diamonds",
		description: "Para itens premium, boosters e atalhos.",

		title: "Diamantes",
	},
];

export const currencyProductIds = currencyPacks.map((pack) => pack.productId);

export function getCurrencyPack(productId: string) {
	return currencyPacks.find((pack) => pack.productId === productId);
}
