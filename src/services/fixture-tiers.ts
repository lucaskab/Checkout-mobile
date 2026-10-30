import type { GameState } from "@/@types/game";
import type { FixtureKind } from "@/@types/fixture-tiers";
import {
	canBuyCapacityTier,
	getCapacityTier,
	getCheckoutTier,
	getCheckoutVisualTier,
	getColdRoomTier,
	getColdRoomUpgradeCap,
	getEraFixtureTierCap,
	getFixtureTierDefinition,
	getFixtureTierEra,
	getFixtureTierTemplate,
	getShelfFixtureTier,
	getTierSlotLimit,
	isChilledCategory,
	isStallEra,
	PREMIUM_TIER,
	shelfFixtureKinds,
} from "@/data/fixture-tiers";
import { getMarketEra } from "@/data/economy";
import { getNextShelfCapacityUpgrade, getShelfCapacity } from "@/data/shelf-capacity";
import { getShelfType, type ShelfTypeId } from "@/data/shelf-types";

// The tier of each piece of furniture, read from the save (nothing new is stored for the product fixtures:
// src/data/fixture-tiers.ts). Pages and the Unity snapshot use these.

type TierState = Pick<GameState, "era" | "shelfUpgradeLevels" | "shop">;

export type FixtureTierInfo = {
	kind: FixtureKind;
	/** Tier shown now (1..5; 5 = the premium finish of the T4 model). 0: the stall's own crates/cooler. */
	tier: number;
	/** Tier the capacity bought stands for (may be above `tier` in a small shop). */
	boughtTier: number;
	name: string;
	width: number;
	depth: number;
	/** Unity template of the model. */
	template: string;
	premium: boolean;
};

export function getShelfFixtureKind(shelfId: string): FixtureKind | null {
	return getShelfType(shelfId) ? shelfFixtureKinds[shelfId as ShelfTypeId] : null;
}

export function getShelfTierInfo(state: TierState, shelfId: string): FixtureTierInfo | null {
	const kind = getShelfFixtureKind(shelfId);
	if (!kind) return null;
	const level = state.shelfUpgradeLevels[shelfId] ?? 0;
	const tier = isStallEra(state.era.id) ? 0 : getShelfFixtureTier(level, state.era.id);
	const definition = getFixtureTierDefinition(kind, Math.max(1, tier));
	return {
		kind,
		tier,
		boughtTier: getCapacityTier(level),
		name: definition.name,
		width: definition.width,
		depth: definition.depth,
		template: getFixtureTierTemplate(kind, Math.max(1, tier)),
		premium: tier >= PREMIUM_TIER,
	};
}

/** The next evolution of a product fixture, or why there is none yet. */
export function getShelfEvolution(state: TierState & Pick<GameState, "market">, shelfId: string) {
	const kind = getShelfFixtureKind(shelfId);
	if (!kind) return null;
	const level = state.shelfUpgradeLevels[shelfId] ?? 0;
	const upgrade = getNextShelfCapacityUpgrade(level);
	if (!upgrade) return null;
	const fromTier = getShelfFixtureTier(level, state.era.id);
	const toTier = getCapacityTier(level + 1);
	const from = getFixtureTierDefinition(kind, Math.max(1, fromTier));
	const to = getFixtureTierDefinition(kind, toTier);
	const allowed = canBuyCapacityTier(level, state.era.id);
	return {
		upgrade,
		fromTier,
		toTier,
		from,
		to,
		capacityFrom: getShelfCapacity(level),
		capacityTo: upgrade.capacity,
		/** The shop is too small for the next tier: it comes with this expansion. */
		blockedUntil: allowed ? null : getMarketEra(getFixtureTierEra(toTier)).name,
		/** The look changes now (in the stalls the crates stay; a premium finish keeps the footprint). */
		changesLook: !isStallEra(state.era.id) && allowed,
		grows: !isStallEra(state.era.id) && allowed && (to.width > from.width || to.depth > from.depth),
	};
}

/** Product places the fixture has room for (sector counters: no limit here). */
export function getShelfSlotLimit(state: TierState, shelfId: string) {
	if (!getShelfType(shelfId)) return Number.POSITIVE_INFINITY;
	const level = state.shelfUpgradeLevels[shelfId] ?? 0;
	return getTierSlotLimit(Math.min(getCapacityTier(level), getEraFixtureTierCap(state.era.id)));
}

export function getCheckoutTierInfo(state: TierState) {
	const tier = getCheckoutTier(state.shop.ownedItemIds, state.era.id);
	const visual = getCheckoutVisualTier(state.shop.ownedItemIds, state.era.id);
	const definition = getFixtureTierDefinition("checkout", visual);
	return {
		tier,
		visualTier: visual,
		scanner: state.shop.ownedItemIds.includes("auto-scanner"),
		name: definition.name,
		template: getFixtureTierTemplate("checkout", visual),
	};
}

export function getColdRoomInfo(state: Pick<GameState, "shop">) {
	const tier = getColdRoomTier(state.shop.ownedItemIds);
	const definition = getFixtureTierDefinition("coldroom", tier);
	return { tier, name: definition.name, upgradeCap: getColdRoomUpgradeCap(tier), template: getFixtureTierTemplate("coldroom", tier) };
}

/** Highest stockroom upgrade this product may buy: chilled goods are limited by the cold room. */
export function getInventoryUpgradeCap(state: Pick<GameState, "shop">, category: string | undefined) {
	return isChilledCategory(category) ? getColdRoomUpgradeCap(getColdRoomTier(state.shop.ownedItemIds)) : Number.POSITIVE_INFINITY;
}
