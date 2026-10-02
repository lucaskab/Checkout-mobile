import type { GameState } from "@/@types/game";
import type { MissionDefinition, MissionStatus } from "@/@types/mission";
import { getMarketEra } from "@/data/economy";
import { missions } from "@/data/missions";

export function getMissionProgress(
	mission: MissionDefinition,
	state: GameState,
) {
	switch (mission.metric) {
		case "customersServed":
			return state.market.customersServed;
		case "customersWhoBought":
			return state.market.customersWhoBought;
		case "expansion":
			return getMarketEra(state.era?.id ?? "mesinha").index;
		case "productLevels":
			return Object.values(state.productLevels ?? {}).reduce((total, level) => total + level, 0);
		case "inventoryProduct":
			return state.inventory[mission.targetProductId ?? -1] ?? 0;
		case "inventoryUnits":
			return Object.values(state.inventory).reduce(
				(total, quantity) => total + quantity,
				0,
			);
		case "level":
			return state.market.level;
		case "productionCrafted":
			return state.production.totalCrafted;
		case "revenue":
			return state.market.totalRevenue;
		case "shelfUpgrades":
			return Object.values(state.shelfUpgradeLevels).reduce(
				(total, level) => total + level,
				0,
			);
		case "soldProduct":
			return state.market.soldByProduct[mission.targetProductId ?? -1] ?? 0;
		case "uniqueProductsSold":
			return Object.values(state.market.soldByProduct).filter(
				(quantity) => quantity > 0,
			).length;
		case "unitsSold":
			return state.market.unitsSold;
	}
}

export function getMissionStatus(
	mission: MissionDefinition,
	state: GameState,
): MissionStatus {
	if (state.missions.claimedMissionIds.includes(mission.id)) {
		return "claimed";
	}

	if (state.market.level < mission.requiredLevel) {
		return "locked";
	}
	if (
		mission.requiredEra &&
		getMarketEra(state.era?.id ?? "mesinha").index < getMarketEra(mission.requiredEra).index
	) {
		return "locked";
	}

	return getMissionProgress(mission, state) >= mission.goal
		? "claimable"
		: "active";
}

export function getClaimableMissionCount(state: GameState) {
	return missions.filter(
		(mission) => getMissionStatus(mission, state) === "claimable",
	).length;
}
