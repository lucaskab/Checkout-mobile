export type ShopEffects = {
	customerArrivalMultiplier: number;
	customerBudgetMultiplier: number;
	maxProductsBonus: number;
	offlineRevenueMultiplier: number;
	productionDurationMultiplier: number;
	revenueMultiplier: number;
	storeReputationBonus: number;
	restockMultiplier: number;
	supplierCostMultiplier: number;
	supplierDurationMultiplier: number;
};

const cartBonuses: Record<string, number> = {
	"large-cart": 5,
	"simple-cart": 2,
	"turbo-cart": 8,
};

const customerBonuses: Record<string, number> = {
	billboard: 0.2,
	influencer: 0.8,
	"national-ad": 1.2,
	"promotion-panel": 0.15,
	radio: 0.3,
	"shopping-basket": 0.1,
	"street-banner": 0.1,
	television: 0.5,
};

const revenueBonuses: Record<string, number> = {
	computer: 0.05,
	"golden-register": 0.15,
	"legendary-manager": 0.4,
	"permanent-vip": 0.1,
	"premium-floor": 0.02,
	"premium-checkout": 0.25,
	"refrigerated-fridge": 0.2,
	"vertical-freezer": 0.3,
};

const restockBonuses: Record<string, number> = {
	"atlas-drone": 1,
	forklift: 0.35,
	"inventory-drone": 0.25,
	"premium-restock-robot": 1,
	"stock-cart": 0.1,
	"stock-robot": 0.5,
};

const arrivalBonuses: Record<string, number> = {
	"auto-scanner": 0.25,
	"delivery-truck": 0.2,
	"face-checkout": 0.35,
	"promotion-panel": 0.15,
	"self-checkout": 0.4,
	"smart-conveyor": 0.15,
};

const supplierCostBonuses: Record<string, number> = {
	"distribution-center": -0.15,
	"erp-system": -0.1,
	pallet: -0.05,
};

const supplierDurationBonuses: Record<string, number> = {
	"delivery-drone": 0.65,
	"premium-truck": 0.5,
	"smart-conveyor": 0.9,
};

const productionDurationBonuses: Record<string, number> = {
	"golden-register": 0.9,
};

const reputationBonuses: Record<string, number> = {
	fountain: 10,
	garden: 6,
	plant: 1,
};

const offlineRevenueBonuses: Record<string, number> = {
	"ceo-manager": 1.4,
	"delivery-drone": 1.5,
};

export function getShopEffects(ownedItemIds: string[]): ShopEffects {
	return ownedItemIds.reduce<ShopEffects>(
		(effects, itemId) => {
			const supplierCostBonus = supplierCostBonuses[itemId] ?? 0;
			const supplierDurationBonus = supplierDurationBonuses[itemId];
			const productionDurationBonus = productionDurationBonuses[itemId];

			return {
				customerArrivalMultiplier:
					effects.customerArrivalMultiplier +
					(customerBonuses[itemId] ?? 0) +
					(arrivalBonuses[itemId] ?? 0),
				customerBudgetMultiplier: effects.customerBudgetMultiplier,
				maxProductsBonus: effects.maxProductsBonus + (cartBonuses[itemId] ?? 0),
				offlineRevenueMultiplier:
					effects.offlineRevenueMultiplier +
					(offlineRevenueBonuses[itemId] ?? 0),
				productionDurationMultiplier:
					productionDurationBonus === undefined
						? effects.productionDurationMultiplier
						: effects.productionDurationMultiplier *
							(productionDurationBonus ?? 1),
				revenueMultiplier:
					effects.revenueMultiplier + (revenueBonuses[itemId] ?? 0),
				storeReputationBonus:
					effects.storeReputationBonus + (reputationBonuses[itemId] ?? 0),
				restockMultiplier:
					effects.restockMultiplier + (restockBonuses[itemId] ?? 0),
				supplierCostMultiplier: Math.max(
					0.35,
					effects.supplierCostMultiplier + supplierCostBonus,
				),
				supplierDurationMultiplier:
					effects.supplierDurationMultiplier * (supplierDurationBonus ?? 1),
			};
		},
		{
			customerArrivalMultiplier: 1,
			customerBudgetMultiplier: 1,
			maxProductsBonus: 0,
			offlineRevenueMultiplier: 1,
			productionDurationMultiplier: 1,
			revenueMultiplier: 1,
			storeReputationBonus: 0,
			restockMultiplier: 1,
			supplierCostMultiplier: 1,
			supplierDurationMultiplier: 1,
		},
	);
}
