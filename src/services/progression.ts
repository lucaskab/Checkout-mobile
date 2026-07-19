import type { MarketPurchase } from "@/@types/customer-simulation";
import type { ExperienceProgress } from "@/@types/game";
import type { MarketProduct } from "@/data/market-products";

export function getExperienceToNextLevel(level: number) {
	return Math.round(80 * level ** 1.45 + 20 * level);
}

export function getExperienceFromSales(
	purchases: MarketPurchase[],
	products: MarketProduct[],
) {
	return purchases.reduce((total, purchase) => {
		const product = products.find((item) => item.id === purchase.productId);

		return total + (product?.experience ?? 0) * purchase.quantity;
	}, 0);
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
