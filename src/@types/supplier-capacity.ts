export type SupplierOrderSlotCurrency = "coins" | "diamonds";

export type SupplierOrderSlotUpgrade = {
	coinCost: number;
	diamondCost: number;
	playerLevel: number;
	slots: number;
};
