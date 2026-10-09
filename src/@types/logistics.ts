export type SupplierOrderStatus =
	| "em-producao"
	| "enviado"
	| "em-transporte"
	| "entregue";

/** One product on a truck: its boxes (src/data/case-sizes.ts) and what they cost before the freight coupon. */
export type SupplierOrderLine = {
	productId: number;
	boxes: number;
	caseSize: number;
	/** Units in the line (boxes × caseSize). */
	quantity: number;
	cost: number;
};

export type SupplierOrder = {
	createdAt: number;
	deliveryDurationMs: number;
	deliveredAt: number | null;
	id: string;
	/** The first product of the truck (the only one on orders from before carts). */
	productId: number;
	/** Units ordered in all (boxes × caseSize of every line). */
	quantity: number;
	/** Supplier boxes ordered in all and units in each (orders before boxes have neither). */
	boxes?: number;
	caseSize?: number;
	/** The products on the truck (orders before carts have none: one product, see getOrderLines). */
	lines?: SupplierOrderLine[];
	status: SupplierOrderStatus;
	/** What was charged for the whole truck. */
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
	/** Supplier boxes to buy (each holds the product's caseSize units). */
	boxes?: number;
	/** Old callers: units wanted, rounded up to whole boxes. */
	quantity?: number;
	useFreightCoupon?: boolean;
};

/** A shopping cart of supplier boxes: one truck carrying every line (each product once). */
export type PlaceSupplierCartInput = {
	lines: { productId: number; boxes: number }[];
	useFreightCoupon?: boolean;
};
