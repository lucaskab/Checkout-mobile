export type InventoryLot = {
	expiresAt: number | null;
	quantity: number;
};

export type GameInventoryLots = Record<number, InventoryLot[]>;

export type GameShelfLots = Record<string, InventoryLot[]>;
