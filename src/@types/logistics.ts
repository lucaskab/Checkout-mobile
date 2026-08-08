export type SupplierOrderStatus =
	| "em-producao"
	| "enviado"
	| "em-transporte"
	| "entregue";

export type SupplierOrder = {
	createdAt: number;
	deliveryDurationMs: number;
	deliveredAt: number | null;
	id: string;
	productId: number;
	quantity: number;
	status: SupplierOrderStatus;
	totalCost: number;
};

export type LogisticsState = {
	emergencyTokens: number;
	freightCoupons: number;
	logisticsBoostExpiresAt: number | null;
	orders: SupplierOrder[];
	premiumCurrency: number;
	supplierOrderSlots: number;
};

export type PlaceSupplierOrderInput = {
	productId: number;
	quantity: number;
	useFreightCoupon?: boolean;
};
