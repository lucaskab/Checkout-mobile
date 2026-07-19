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
	extraTruckExpiresAt: number | null;
	freightCoupons: number;
	logisticsBoostExpiresAt: number | null;
	orders: SupplierOrder[];
	premiumCurrency: number;
	vipExpiresAt: number | null;
};

export type PlaceSupplierOrderInput = {
	productId: number;
	quantity: number;
	totalCost: number;
	useFreightCoupon?: boolean;
};
