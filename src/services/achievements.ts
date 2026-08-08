import type { AchievementDefinition } from "@/@types/achievement";
import type { GameState } from "@/@types/game";
import { achievements } from "@/data/achievements";

export function getAchievementProgress(
	achievement: AchievementDefinition,
	state: GameState,
) {
	switch (achievement.metric) {
		case "customersServed":
			return state.market.customersServed;
		case "customersWhoBought":
			return state.market.customersWhoBought;
		case "experience":
			return state.market.totalExperience;
		case "instantDeliveries":
			return state.statistics.instantDeliveries;
		case "instantProductionFinishes":
			return state.statistics.instantProductionFinishes;
		case "level":
			return state.market.level;
		case "marketOpenings":
			return state.statistics.marketOpenings;
		case "missionsClaimed":
			return state.missions.claimedMissionIds.length;
		case "priceChanges":
			return state.statistics.priceChanges;
		case "productionCrafted":
			return state.production.totalCrafted;
		case "productionJobsStarted":
			return state.statistics.productionJobsStarted;
		case "productsUnlocked":
			return state.market.unlockedProductIds.length;
		case "restockedUnits":
			return state.statistics.restockedUnits;
		case "revenue":
			return state.market.totalRevenue;
		case "shelfUpgrades":
			return Object.values(state.shelfUpgradeLevels).reduce(
				(total, level) => total + level,
				0,
			);
		case "shopPurchases":
			return state.statistics.shopPurchases;
		case "soldProduct":
			return state.market.soldByProduct[achievement.targetProductId ?? -1] ?? 0;
		case "supplierOrdersPlaced":
			return state.statistics.supplierOrdersPlaced;
		case "uniqueProductsSold":
			return Object.values(state.market.soldByProduct).filter(
				(quantity) => quantity > 0,
			).length;
		case "unitsSold":
			return state.market.unitsSold;
	}
}

export function getAchievementStars(
	achievement: AchievementDefinition,
	state: GameState,
) {
	if (state.market.level < achievement.requiredLevel) {
		return 0;
	}

	const progress = getAchievementProgress(achievement, state);

	return achievement.thresholds.filter((threshold) => progress >= threshold)
		.length;
}

export function getAchievementTotals(state: GameState) {
	const stars = achievements.reduce(
		(total, achievement) => total + getAchievementStars(achievement, state),
		0,
	);

	return {
		achievementsCompleted: achievements.filter(
			(achievement) =>
				getAchievementStars(achievement, state) ===
				achievement.thresholds.length,
		).length,
		stars,
		totalStars: achievements.reduce(
			(total, achievement) => total + achievement.thresholds.length,
			0,
		),
	};
}
