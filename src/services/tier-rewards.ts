import type { GameShelfSlotCounts, GameState } from "@/@types/game";
import type { ProductionSectorId } from "@/@types/production";
import {
	fixtureTierAttraction,
	fixtureTierRestock,
	getCapacityTier,
	getEraFixtureTierCap,
	getSectorTier,
	getSectorTierDefinition,
	getTierSlotLimit,
} from "@/data/fixture-tiers";
import { isExclusiveAllowed } from "@/data/fixture-products";
import { itemCatalog } from "@/data/market-products";
import { getShelfCapacity } from "@/data/shelf-capacity";
import { getPhysicalShelfId, getShelfSlotCount, getTotalUnlockedShelfSlots } from "@/data/shelf-slots";
import { getSectorCounter, getShelfType } from "@/data/shelf-types";

export { isExclusiveAllowed };

// What every evolution gives (claude/evolucoes-recompensas.md, Lucas 01/11), read from the tiers the save already has:
// - product fixtures: places for products (T1 4 … ★ 8), customers pick from them more often, restocking is faster and
//   one exclusive product per tier;
// - sectors: the counter shows 5 / 6 products with +5 / +10 units each, and one exclusive recipe per tier (the
//   production bonuses are in src/data/fixture-tiers.ts sectorTiers).
// Nothing here ever takes something away: places bought before stay, products already open stay open.

type RewardState = Pick<GameState, "era" | "shelfUpgradeLevels" | "sectorTiers" | "builtSectorIds">;

/** The tier a product fixture counts for its rewards: what was bought, as big as this shop allows (1..5). */
export function getRewardTier(state: Pick<GameState, "era" | "shelfUpgradeLevels">, shelfId: string) {
	return Math.max(1, Math.min(getCapacityTier(state.shelfUpgradeLevels[shelfId] ?? 0), getEraFixtureTierCap(state.era.id)));
}

/** Product places the fixture comes with at its tier (sector counters: by the sector's tier). */
export function getTierPlaces(state: RewardState, physicalShelfId: string) {
	if (getShelfType(physicalShelfId)) return getTierSlotLimit(getRewardTier(state, physicalShelfId));
	const counter = getSectorCounter(physicalShelfId);
	if (counter) return getSectorTierDefinition(getSectorTier(state.sectorTiers, counter.sectorId)).counterPlaces;
	return 0;
}

/** Units each product of this slot's fixture holds: the capacity bought, plus the sector counter's tier bonus. */
export function getSlotCapacity(state: Pick<GameState, "shelfUpgradeLevels" | "sectorTiers">, slotId: string) {
	const shelfId = getPhysicalShelfId(slotId);
	const base = getShelfCapacity(state.shelfUpgradeLevels[shelfId] ?? 0);
	const counter = getSectorCounter(shelfId);
	return counter ? base + getSectorTierDefinition(getSectorTier(state.sectorTiers, counter.sectorId)).counterUnits : base;
}

/** Customers pick from the fixture × (1 + this). */
export function getFixtureAttraction(state: Pick<GameState, "era" | "shelfUpgradeLevels">, physicalShelfId: string) {
	return getShelfType(physicalShelfId) ? (fixtureTierAttraction[getRewardTier(state, physicalShelfId)] ?? 0) : 0;
}

/** Restocking the fixture takes × (1 − this) of the time (stock clerk and the stockroom mini-game). */
export function getFixtureRestockBonus(state: Pick<GameState, "era" | "shelfUpgradeLevels">, physicalShelfId: string) {
	return getShelfType(physicalShelfId) ? (fixtureTierRestock[getRewardTier(state, physicalShelfId)] ?? 0) : 0;
}

/** The exclusive products the fixtures and sectors have earned with their tiers so far. */
export function getEarnedExclusiveProductIds(state: RewardState) {
	return itemCatalog
		.filter((product) => {
			const exclusive = product.exclusive;
			if (!exclusive) return false;
			if (getShelfType(exclusive.fixture))
				return getCapacityTier(state.shelfUpgradeLevels[exclusive.fixture] ?? 0) >= exclusive.tier;
			return (
				state.builtSectorIds.includes(exclusive.fixture as ProductionSectorId) &&
				getSectorTier(state.sectorTiers, exclusive.fixture) >= exclusive.tier
			);
		})
		.map((product) => product.id);
}

/** The exclusive product a fixture/sector earns at `tier` (null when it has none). */
export function getExclusiveProductFor(fixture: string, tier: number) {
	return itemCatalog.find((product) => product.exclusive?.fixture === fixture && product.exclusive.tier === tier) ?? null;
}

/**
 * The places and products every tier the save has gives, merged into it (idempotent; never lowers anything). Used when
 * an evolution ends and on old saves (src/stores/game-store.ts migrate).
 */
export function withTierRewards(state: RewardState & Pick<GameState, "shelfSlotCounts" | "market">) {
	const shelfSlotCounts: GameShelfSlotCounts = { ...state.shelfSlotCounts };
	const grantedPlaces: string[] = [];
	for (const shelfId of Object.keys(shelfSlotCounts)) {
		const count = getShelfSlotCount(shelfId, shelfSlotCounts);
		if (count <= 0) continue;
		const places = getTierPlaces(state, shelfId);
		if (places > count) {
			shelfSlotCounts[shelfId] = places;
			grantedPlaces.push(shelfId);
		}
	}
	const earned = getEarnedExclusiveProductIds(state);
	const newProducts = earned.filter((id) => !state.market.unlockedProductIds.includes(id));
	return {
		shelfSlotCounts,
		unlockedShelfSlots: getTotalUnlockedShelfSlots(shelfSlotCounts),
		unlockedProductIds: newProducts.length ? [...state.market.unlockedProductIds, ...newProducts] : state.market.unlockedProductIds,
		grantedPlaces,
		newProducts,
	};
}
