import type { ShelfUnlockUpgrade } from "./shelf-capacity";

export type StoreShelf = {
	id: string;
	name?: string;
	nextShelfUpgrade?: ShelfUnlockUpgrade;
	productId?: number;
	locked?: boolean;
};

export type StoreCustomerStatus = "pagou" | "saiu sem comprar";

export type StoreActiveCustomer = {
	id: string;
	item: string;
	mood?: "calmo" | "com-pressa" | "feliz" | "estressado";
	name: string;
	satisfaction?: number;
	spent: number;
	status: StoreCustomerStatus;
};

export type StoreAlert = {
	actionLabel: string;
	id: string;
	issue: string;
	name: string;
	productId?: number;
	type: "low" | "notice";
};

export type StoreTopSeller = {
	id: string;
	name: string;
	productId?: number;
	revenue: number;
	sold: number;
};
