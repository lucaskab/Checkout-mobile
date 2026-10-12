import type {
	CurrencyPack,
	CurrencyPackCategory,
} from "@/@types/currency-purchase";
import type { MarketEraId } from "@/@types/economy";
import { roundPrice } from "@/data/economy";

// Balance (Lucas 12/10, "the economy has to make the player want to buy"):
// - Diamonds are bought, not farmed: ~38 → 60 diamonds per euro from the smallest to the biggest pack, so bigger packs
//   are better value. One speed-up price for the whole game (src/data/diamond-skip.ts): 1 h ≈ 10, 1 day ≈ 150.
// - Coins follow the player: a coin pack holds `coinTurns` 10-minute turns of profit of the player's CURRENT expansion
//   (getCurrencyPackCoins), so a pack skips the same effort at the sidewalk table and at the chain (a fixed 20 million
//   used to skip the whole game; 5 000 at the end was nothing). `coins` is the amount at the first expansion.
// - Combos are ~1.3× the value of buying their diamonds and coins apart. The welcome combo is a one-time offer.
export const currencyPacks: CurrencyPack[] = [
	{
		badge: "Oferta de boas-vindas",
		category: "bundle",
		coins: 6_000,
		coinTurns: 40,
		oncePerPlayer: true,
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
		coins: 9_000,
		coinTurns: 60,
		diamonds: 300,
		fallbackPrice: "€ 9,99",
		id: "bundle-growing",
		name: "Combo Mercado",
		productId: "com.checkout.currency.bundle.growing",
		tier: 2,
	},
	{
		badge: "Ótimo valor",
		category: "bundle",
		coins: 20_000,
		coinTurns: 130,
		diamonds: 650,
		fallbackPrice: "€ 19,99",
		id: "bundle-supermarket",
		name: "Combo Supermercado",
		productId: "com.checkout.currency.bundle.supermarket",
		tier: 3,
	},
	{
		badge: "Magnata",
		category: "bundle",
		coins: 44_000,
		coinTurns: 280,
		diamonds: 1_400,
		fallbackPrice: "€ 39,99",
		id: "bundle-tycoon",
		name: "Combo Magnata",
		productId: "com.checkout.currency.bundle.tycoon",
		tier: 4,
	},
	{
		badge: "Melhor valor",
		category: "bundle",
		coins: 95_000,
		coinTurns: 600,
		diamonds: 3_000,
		fallbackPrice: "€ 79,99",
		id: "bundle-empire",
		name: "Combo Império",
		productId: "com.checkout.currency.bundle.empire",
		tier: 5,
	},
	{
		badge: "Essencial",
		category: "coins",
		coins: 1_900,
		coinTurns: 12,
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
		coins: 5_500,
		coinTurns: 35,
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
		coins: 12_600,
		coinTurns: 80,
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
		coins: 28_000,
		coinTurns: 180,
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
		coins: 63_000,
		coinTurns: 400,
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
	return currencyPacks.find((pack) => pack.productId === productId || pack.id === productId);
}

/**
 * Average profit of a regular player in one 10-minute turn, per expansion (scripts/economy-robot.ts, project doc
 * economia-produtos). Sizes the coin packs.
 */
export const ERA_TURN_PROFIT: Record<MarketEraId, number> = {
	mesinha: 158,
	tenda: 539,
	banca: 856,
	conteiner: 1_078,
	spati: 1_579,
	quitanda: 2_707,
	minimercado: 3_858,
	mercadinho: 6_151,
	supermercado: 10_913,
	hipermercado: 22_589,
	rede: 36_637,
};

/** Coins a pack gives a player at `eraId` (round, friendly numbers). */
export function getCurrencyPackCoins(pack: CurrencyPack, eraId: MarketEraId | undefined) {
	if (!pack.coinTurns) return pack.coins;
	const profit = ERA_TURN_PROFIT[eraId ?? "mesinha"] ?? ERA_TURN_PROFIT.mesinha;
	return roundPrice(Math.max(500, pack.coinTurns * profit));
}

/**
 * Prices by region (Lucas 12/10): euros in Europe, dollars in the US, reais in Brazil — not a straight conversion.
 * Brazil is priced for its purchasing power (about 45 % below the euro price converted), the UK a little under the
 * euro. The App Store / Google Play charge what is set per country in App Store Connect / Play Console (these
 * tables are what to enter there); the game shows the store's own price as soon as the store answers, and these
 * only until then (or on a device with no store). Index = price point of the pack (fallbackPrice).
 */
export type PriceCurrency = "EUR" | "USD" | "BRL" | "GBP";
const PRICE_POINTS = ["1,99", "4,99", "9,99", "19,99", "39,99", "79,99"];
export const REGIONAL_PRICES: Record<PriceCurrency, readonly string[]> = {
	EUR: ["1,99 €", "4,99 €", "9,99 €", "19,99 €", "39,99 €", "79,99 €"],
	USD: ["$1.99", "$4.99", "$9.99", "$19.99", "$39.99", "$79.99"],
	BRL: ["R$ 6,90", "R$ 16,90", "R$ 32,90", "R$ 64,90", "R$ 124,90", "R$ 249,90"],
	GBP: ["£1.79", "£4.49", "£8.99", "£17.99", "£34.99", "£69.99"],
};
const EURO_COUNTRIES = new Set(
	"AT BE CY DE EE ES FI FR GR HR IE IT LT LU LV MT NL PT SI SK AD MC SM VA ME XK".split(" "),
);

/** The currency the game shows for a country (ISO code of the device's region, e.g. "BR"). */
export function getPriceCurrency(region: string | undefined): PriceCurrency {
	const code = (region ?? "").toUpperCase();
	if (code === "BR") return "BRL";
	if (code === "GB") return "GBP";
	if (EURO_COUNTRIES.has(code)) return "EUR";
	return code === "US" || code ? "USD" : "EUR";
}

/** The pack's price in the region's currency ("R$ 16,90"), before the store's own price is known. */
export function getRegionalPrice(pack: CurrencyPack, region: string | undefined) {
	const point = PRICE_POINTS.indexOf(pack.fallbackPrice.replace("€", "").trim());
	return REGIONAL_PRICES[getPriceCurrency(region)][point] ?? pack.fallbackPrice;
}

/** Whether the player may still buy `pack` (the welcome combo only once). */
export function isCurrencyPackAvailable(pack: CurrencyPack, purchasedPackIds: readonly string[] | undefined) {
	return !pack.oncePerPlayer || !(purchasedPackIds ?? []).includes(pack.id);
}
