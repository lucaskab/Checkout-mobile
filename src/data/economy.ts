import type { MarketEraDefinition, MarketEraId } from "@/@types/economy";

// Balance sheet of the whole game: one place for the numbers that decide how fast the market grows.
// The robot player (scripts/economy-robot.ts) plays 30+ days with these numbers and reports the day
// each era is reached; tune here, run the robot, repeat.

const MINUTE = 60_000;
const HOUR = 60 * MINUTE;

/** One market turn ("dia" inside the game). */
export const TURN_MINUTES = 10;
export const TURN_DURATION_MS = TURN_MINUTES * MINUTE;
/** Contract targets and rewards were first sized for 5-minute turns. */
export const TURN_SCALE = TURN_MINUTES / 5;

/** Coins of a brand-new game (enough for a few crates of stock, not for the stall). */
export const STARTING_COINS = 200;

/**
 * Coins and experience of a finished contract (before the difficulty multiplier). About half to one
 * turn of sales: the contract is a bonus for the day, selling is still the job.
 */
export function getContractCoins(level: number) {
	return 60 + level * 20;
}
export function getContractExperience(level: number) {
	return 15 + level * 6;
}

/** Levels an item can gain on top of the one bought (income up to ×1,10^10 ≈ ×2,6). */
export const MAX_ITEM_LEVEL = 10;

/** Every new level of the same thing costs 15% more… */
export const ITEM_COST_GROWTH = 1.15;
/** …and earns 10% more than the level before. */
export const ITEM_INCOME_GROWTH = 1.1;

/** Away time that still counts for offline sales (longer absences earn the same). */
export const OFFLINE_CAP_MS = 8 * HOUR;
/** Offline sales give this share of the experience a played turn would. */
export const OFFLINE_XP_SHARE = 1;

/** Shortest and longest build in the game. */
export const MIN_BUILD_MS = 3 * MINUTE;
export const MAX_BUILD_MS = 36 * HOUR;

export const marketEras: MarketEraDefinition[] = [
	{
		id: "mesinha",
		index: 0,
		name: "Mesinha na calçada",
		coinCost: 0,
		targetDay: 1,
		buildDurationMs: 0,
		productSlots: 2,
		arrivalMultiplier: 0.8,
		ticketMultiplier: 1,
		offlineTurnsPerHour: 0.1,
		itemUpgradeBaseCost: 40,
		nightTurn: false,
	},
	{
		id: "banca",
		index: 1,
		name: "Banca de feira",
		coinCost: 600,
		targetDay: 1,
		buildDurationMs: 3 * MINUTE,
		productSlots: 4,
		arrivalMultiplier: 0.9,
		ticketMultiplier: 1,
		offlineTurnsPerHour: 0.3,
		itemUpgradeBaseCost: 80,
		nightTurn: false,
	},
	{
		id: "tenda",
		index: 2,
		name: "Tenda",
		coinCost: 6_000,
		targetDay: 3,
		buildDurationMs: 20 * MINUTE,
		productSlots: 6,
		arrivalMultiplier: 1,
		ticketMultiplier: 1,
		offlineTurnsPerHour: 0.4,
		itemUpgradeBaseCost: 160,
		nightTurn: false,
	},
	{
		id: "conteiner",
		index: 3,
		name: "Mini-contêiner",
		coinCost: 28_000,
		targetDay: 6,
		buildDurationMs: 1 * HOUR,
		productSlots: 10,
		arrivalMultiplier: 1.15,
		ticketMultiplier: 1,
		offlineTurnsPerHour: 0.5,
		itemUpgradeBaseCost: 300,
		nightTurn: false,
	},
	{
		id: "spati",
		index: 4,
		name: "Späti",
		coinCost: 90_000,
		targetDay: 10,
		buildDurationMs: 3 * HOUR,
		productSlots: 14,
		arrivalMultiplier: 1.3,
		ticketMultiplier: 1,
		offlineTurnsPerHour: 0.6,
		itemUpgradeBaseCost: 550,
		nightTurn: true,
	},
	{
		id: "mercadinho",
		index: 5,
		name: "Mercadinho",
		coinCost: 240_000,
		targetDay: 15,
		buildDurationMs: 8 * HOUR,
		productSlots: 20,
		arrivalMultiplier: 1.5,
		ticketMultiplier: 1.3,
		offlineTurnsPerHour: 0.6,
		itemUpgradeBaseCost: 900,
		nightTurn: true,
	},
	{
		id: "supermercado",
		index: 6,
		name: "Supermercado",
		coinCost: 600_000,
		targetDay: 22,
		buildDurationMs: 18 * HOUR,
		productSlots: 30,
		arrivalMultiplier: 1.75,
		ticketMultiplier: 2.7,
		offlineTurnsPerHour: 0.7,
		itemUpgradeBaseCost: 1_800,
		nightTurn: true,
	},
	{
		id: "hipermercado",
		index: 7,
		name: "Hipermercado",
		coinCost: 2_000_000,
		targetDay: 30,
		buildDurationMs: MAX_BUILD_MS,
		productSlots: 40,
		arrivalMultiplier: 2,
		ticketMultiplier: 5.1,
		offlineTurnsPerHour: 0.7,
		itemUpgradeBaseCost: 3_500,
		nightTurn: true,
	},
	{
		id: "rede",
		index: 8,
		name: "Rede de filiais",
		coinCost: 6_000_000,
		targetDay: 40,
		buildDurationMs: MAX_BUILD_MS,
		productSlots: 40,
		arrivalMultiplier: 2,
		ticketMultiplier: 5.1,
		offlineTurnsPerHour: 0.7,
		itemUpgradeBaseCost: 3_500,
		nightTurn: true,
	},
];

export function getMarketEra(id: MarketEraId) {
	return marketEras.find((era) => era.id === id) ?? marketEras[0];
}

export function getNextMarketEra(id: MarketEraId) {
	return marketEras[getMarketEra(id).index + 1] ?? null;
}

/** Price of taking an item from `level` to `level + 1` (level 0 = as bought). */
export function getItemUpgradeCost(baseCost: number, level: number) {
	return roundPrice(baseCost * ITEM_COST_GROWTH ** Math.max(0, level));
}

/** Income of an item at `level`, relative to level 0. */
export function getItemIncomeMultiplier(level: number) {
	return ITEM_INCOME_GROWTH ** Math.max(0, level);
}

/**
 * Build time for something that costs `coinCost`: 3 min for pocket change, 36 h for the hypermarket.
 * Grows with the log of the price so every era step feels a bit longer than the last.
 */
export function getBuildDurationForCost(coinCost: number) {
	const cheap = 500;
	const expensive = 2_000_000;
	if (coinCost <= cheap) return MIN_BUILD_MS;
	const t = Math.min(1, Math.log(coinCost / cheap) / Math.log(expensive / cheap));
	const ms = MIN_BUILD_MS * (MAX_BUILD_MS / MIN_BUILD_MS) ** t;
	return Math.round(ms / MINUTE) * MINUTE;
}

/** Friendly prices: 2 significant digits (1.234 → 1.200, 48.765 → 49.000). */
export function roundPrice(value: number) {
	if (value < 100) return Math.max(1, Math.round(value));
	const step = 10 ** (Math.floor(Math.log10(value)) - 1);
	return Math.round(value / step) * step;
}
