import type { GameState } from "@/@types/game";
import type { MissionDefinition, MissionStatus } from "@/@types/mission";
import { getMarketEra } from "@/data/economy";
import { getInventoryCapacity } from "@/data/inventory-capacity";
import { itemCatalog } from "@/data/market-products";
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

	return getMissionProgress(mission, state) >= mission.goal ||
		(state.missions.reachedMissionIds ?? []).includes(mission.id)
		? "claimable"
		: "active";
}

/** Stock missions done right now that are not latched yet (see the subscription in stores/game-store.ts). */
export function getNewlyReachedMissionIds(state: GameState) {
	const reached = state.missions.reachedMissionIds ?? [];
	return missions
		.filter(
			(mission) =>
				(mission.metric === "inventoryUnits" || mission.metric === "inventoryProduct") &&
				!reached.includes(mission.id) &&
				!state.missions.claimedMissionIds.includes(mission.id) &&
				getMissionStatus(mission, state) === "claimable",
		)
		.map((mission) => mission.id);
}

export function getClaimableMissionCount(state: GameState) {
	return missions.filter(
		(mission) => getMissionStatus(mission, state) === "claimable",
	).length;
}

/** What claiming a mission gives right now: the coins, the reward products that go to the stockroom, and the
 * ones that don't (no room in the stockroom, or a product the market doesn't sell yet), paid in coins at
 * their supplier price instead, so a mission can always be claimed. */
export type MissionRewardPlan = {
	coins: number;
	stored: { productId: number; quantity: number }[];
	sold: { productId: number; quantity: number; coins: number; reason: "full" | "locked" }[];
};
export function getMissionRewardPlan(
	mission: MissionDefinition,
	state: Pick<GameState, "inventory" | "inventoryCapacityLevels" | "market">,
): MissionRewardPlan {
	const plan: MissionRewardPlan = { coins: mission.reward.coins, stored: [], sold: [] };
	const held: Record<number, number> = {};
	for (const item of mission.reward.items ?? []) {
		const product = itemCatalog.find((entry) => entry.id === item.productId);
		if (!product || item.quantity <= 0) continue;
		const sells = state.market.unlockedProductIds.includes(product.id);
		const have = (state.inventory[product.id] ?? 0) + (held[product.id] ?? 0);
		const room = sells ? Math.max(0, getInventoryCapacity(product, state.inventoryCapacityLevels[product.id]) - have) : 0;
		const keep = Math.min(item.quantity, room);
		if (keep > 0) {
			plan.stored.push({ productId: product.id, quantity: keep });
			held[product.id] = (held[product.id] ?? 0) + keep;
		}
		const rest = item.quantity - keep;
		if (rest > 0) {
			const value = Math.max(1, Math.round(rest * product.purchasePrice));
			plan.sold.push({ productId: product.id, quantity: rest, coins: value, reason: sells ? "full" : "locked" });
			plan.coins += value;
		}
	}
	return plan;
}

/** The reward as the player reads it: the coins, each product, and products turned into coins (and why). */
export function describeMissionReward(
	mission: MissionDefinition,
	state: Pick<GameState, "inventory" | "inventoryCapacityLevels" | "market">,
) {
	const plan = getMissionRewardPlan(mission, state);
	const name = (id: number) => itemCatalog.find((item) => item.id === id)?.name ?? "Produto";
	const coins = (value: number) => value.toLocaleString("pt-BR");
	return [
		`${coins(mission.reward.coins)} moedas`,
		...plan.stored.map((item) => `${item.quantity}× ${name(item.productId)}`),
		...plan.sold.map(
			(item) =>
				`${item.quantity}× ${name(item.productId)} → +${coins(item.coins)} moedas (${item.reason === "full" ? "sem espaço no depósito" : "ainda não vende"})`,
		),
	];
}
