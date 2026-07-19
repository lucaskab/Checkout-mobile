export const logisticsIapProducts = {
	emergencyPack: "com.checkout.logistics.emergency-pack",
	extraTruck: "com.checkout.logistics.extra-truck",
	gemsSmall: "com.checkout.logistics.gems.small",
	logisticsBoost: "com.checkout.logistics.boost",
	vipMonthly: "com.checkout.vip.monthly",
} as const;

export const logisticsConsumableProductIds = [
	logisticsIapProducts.emergencyPack,
	logisticsIapProducts.extraTruck,
	logisticsIapProducts.gemsSmall,
	logisticsIapProducts.logisticsBoost,
];
