// Supplier deliveries waiting at the loading dock. The truck parks with the order and someone has
// to unload it into the stockroom: the player (System: one tap; Simulator: box by box in Unity)
// or a working stock clerk. Units only count as stock once unloaded.
export type WarehouseZone = "refrigerados" | "bebidas" | "hortifruti" | "mercearia";

export type DockDelivery = {
	arrivedAt: number;
	category: string;
	id: string;
	orderId: string;
	productId: number;
	productName: string;
	quantity: number;
	unloaded: number;
	zone: WarehouseZone;
};

export type ReceivingState = {
	dock: DockDelivery[];
	nextStaffAt: number | null;
	unloadedUnits: number;
};
