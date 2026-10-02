import type { MarketEraId } from "@/@types/economy";
import {
	getItemIncomeMultiplier,
	getItemUpgradeCost,
	getMarketEra,
	MAX_ITEM_LEVEL,
} from "@/data/economy";

// Item levels ("nível do produto"): every product can be improved up to MAX_ITEM_LEVEL times. Each level
// earns 10% more profit per sale and makes the product a little more attractive to impulse buyers. The price
// of a level follows the current expansion (bigger shops, pricier upgrades) and grows 15% per level.

export type ProductLevels = Record<number, number>;

/** Extra attractiveness (0–100 scale of the catalogue) per level. */
export const ATTRACTIVENESS_PER_LEVEL = 5;

export function getProductLevel(levels: ProductLevels | undefined, productId: number) {
	const level = levels?.[productId] ?? 0;
	return Number.isFinite(level) ? Math.max(0, Math.min(MAX_ITEM_LEVEL, Math.floor(level))) : 0;
}

/** Price of the next level of a product, or null when it is already at the top. */
export function getProductUpgradeCost(eraId: MarketEraId, level: number) {
	if (level >= MAX_ITEM_LEVEL) return null;
	return getItemUpgradeCost(getMarketEra(eraId).itemUpgradeBaseCost, level);
}

/** A sale of a levelled product: the profit (revenue above cost) grows by the level's multiplier. */
export function applyProductLevel<T extends { revenue: number; quantity: number }>(
	purchase: T,
	purchasePrice: number,
	level: number,
): T {
	if (level <= 0) return purchase;
	const margin = purchase.revenue - purchasePrice * purchase.quantity;
	if (margin <= 0) return purchase;
	return { ...purchase, revenue: purchase.revenue + margin * (getItemIncomeMultiplier(level) - 1) };
}

export function normalizeProductLevels(value: unknown): ProductLevels {
	if (!value || typeof value !== "object") return {};
	const levels: ProductLevels = {};
	for (const [key, level] of Object.entries(value as Record<string, unknown>)) {
		const id = Number(key);
		if (Number.isFinite(id) && typeof level === "number" && level > 0)
			levels[id] = Math.min(MAX_ITEM_LEVEL, Math.floor(level));
	}
	return levels;
}
