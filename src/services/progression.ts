import type { MarketPurchase } from "@/@types/customer-simulation";
import type { ExperienceProgress } from "@/@types/game";
import type { ItemDefinition } from "@/@types/item";

/** Experience a level costs in the long run (the mid and late game are balanced on this). */
function fullLevelCost(level: number) {
	return 80 * level ** 1.45 + 20 * level;
}

/** Levels that cost less than the full price: the opening must level up in minutes, not hours. */
export const EARLY_LEVELS = 12;
/** Share of the full price paid by level 1; it grows until EARLY_LEVELS pays the full price. */
const FIRST_LEVEL_SHARE = 0.12;

/** Experience paid by every customer who buys something (serving people is the job, not only selling). */
export const CUSTOMER_EXPERIENCE = 2;

export function getExperienceToNextLevel(level: number) {
	const progress = Math.min(1, Math.max(0, (level - 1) / (EARLY_LEVELS - 1)));
	const share = FIRST_LEVEL_SHARE + (1 - FIRST_LEVEL_SHARE) * progress ** 1.6;
	const cost = fullLevelCost(level) * share;
	// Round to a friendly number: 5 by 5 early, 10 by 10 later.
	const step = cost < 200 ? 5 : 10;
	return Math.max(step, Math.round(cost / step) * step);
}

export function getExperienceFromSales(
	purchases: MarketPurchase[],
	products: Pick<ItemDefinition, "id" | "xpPerSale">[],
) {
	const fromProducts = purchases.reduce((total, purchase) => {
		const product = products.find((item) => item.id === purchase.productId);

		return total + (product?.xpPerSale ?? 0) * purchase.quantity;
	}, 0);

	return purchases.length > 0 ? fromProducts + CUSTOMER_EXPERIENCE : 0;
}

export function applyExperience(
	level: number,
	experience: number,
	experienceGained: number,
): ExperienceProgress {
	let nextLevel = level;
	let nextExperience = experience + experienceGained;
	let levelsGained = 0;

	while (nextExperience >= getExperienceToNextLevel(nextLevel)) {
		nextExperience -= getExperienceToNextLevel(nextLevel);
		nextLevel += 1;
		levelsGained += 1;
	}

	return {
		experience: nextExperience,
		level: nextLevel,
		levelsGained,
	};
}
