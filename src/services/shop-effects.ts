import type { GameShopState, ShopItemEffect } from "@/@types/shop";
import { shopItems } from "@/data/shop-items";

export type ShopEffects = {
	/** Customers come this many times as often (the shop's marketing and boosters). */
	customerArrivalMultiplier: number;
	/** The era's cap on customers per turn grows by this much too (more people fit in). */
	customerCapacityMultiplier: number;
	customerBudgetMultiplier: number;
	maxProductsBonus: number;
	offlineRevenueMultiplier: number;
	productionDurationMultiplier: number;
	revenueMultiplier: number;
	/** Extra revenue share per product category (on top of revenueMultiplier). */
	categoryRevenueBonuses: Record<string, number>;
	storeReputationBonus: number;
	restockMultiplier: number;
	supplierCostMultiplier: number;
	supplierDurationMultiplier: number;
	/** The working cashier rings customers up this many times as fast. */
	cashierSpeedMultiplier: number;
	/** Self-checkout kiosks, in cashier-efficiency units: they work without a cashier. */
	selfCheckoutRate: number;
	/** Customers wait this many times as long in line. */
	checkoutPatienceMultiplier: number;
};

export function createEmptyShopEffects(): ShopEffects {
	return {
		customerArrivalMultiplier: 1,
		customerCapacityMultiplier: 1,
		customerBudgetMultiplier: 1,
		maxProductsBonus: 0,
		offlineRevenueMultiplier: 1,
		productionDurationMultiplier: 1,
		revenueMultiplier: 1,
		categoryRevenueBonuses: {},
		storeReputationBonus: 0,
		restockMultiplier: 1,
		supplierCostMultiplier: 1,
		supplierDurationMultiplier: 1,
		cashierSpeedMultiplier: 1,
		selfCheckoutRate: 0,
		checkoutPatienceMultiplier: 1,
	};
}

function addEffect(effects: ShopEffects, effect: ShopItemEffect): ShopEffects {
	const customers = effect.customers ?? 0;
	const categoryRevenueBonuses = { ...effects.categoryRevenueBonuses };
	if (effect.categoryRevenue)
		for (const category of effect.categoryRevenue.categories)
			categoryRevenueBonuses[category] = (categoryRevenueBonuses[category] ?? 0) + effect.categoryRevenue.bonus;
	return {
		...effects,
		customerArrivalMultiplier: effects.customerArrivalMultiplier + customers,
		customerCapacityMultiplier: effects.customerCapacityMultiplier + customers,
		maxProductsBonus: effects.maxProductsBonus + (effect.basketItems ?? 0),
		offlineRevenueMultiplier: effects.offlineRevenueMultiplier + (effect.offline ?? 0),
		revenueMultiplier: effects.revenueMultiplier + (effect.revenue ?? 0),
		categoryRevenueBonuses,
		storeReputationBonus: effects.storeReputationBonus + (effect.reputation ?? 0),
		restockMultiplier: effects.restockMultiplier + (effect.restock ?? 0),
		supplierCostMultiplier: Math.max(0.5, effects.supplierCostMultiplier - (effect.supplierDiscount ?? 0)),
		supplierDurationMultiplier: effects.supplierDurationMultiplier * (effect.deliveryTime ?? 1),
		cashierSpeedMultiplier: effects.cashierSpeedMultiplier * (effect.cashierSpeed ?? 1),
		selfCheckoutRate: effects.selfCheckoutRate + (effect.selfCheckout ?? 0),
		checkoutPatienceMultiplier: effects.checkoutPatienceMultiplier * (effect.checkoutPatience ?? 1),
	};
}

type ShopEffectsSource = Pick<GameShopState, "ownedItemIds"> & Partial<Pick<GameShopState, "activeBoosts">>;

/**
 * Everything the shop does right now: the upgrades owned plus the boosters still running at `now`.
 * Accepts the shop state (or, for old callers, just the owned ids).
 */
export function getShopEffects(shop: ShopEffectsSource | string[], now = Date.now()): ShopEffects {
	const ownedItemIds = Array.isArray(shop) ? shop : shop.ownedItemIds;
	const activeBoosts = Array.isArray(shop) ? {} : (shop.activeBoosts ?? {});
	let effects = createEmptyShopEffects();
	for (const item of shopItems) {
		if (!item.effect) continue;
		const running = item.isConsumable ? (activeBoosts[item.id] ?? 0) > now : ownedItemIds.includes(item.id);
		if (running) effects = addEffect(effects, item.effect);
	}
	return effects;
}

/** Boosters running at `now`, with the time left (ms). */
export function getActiveBoosts(shop: Partial<Pick<GameShopState, "activeBoosts">>, now = Date.now()) {
	return Object.entries(shop.activeBoosts ?? {})
		.filter(([, endsAt]) => endsAt > now)
		.map(([id, endsAt]) => ({ id, remainingMs: endsAt - now }));
}
