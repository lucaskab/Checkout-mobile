export type StoreShelf = {
	id: string;
	name?: string;
	product?: string;
	productId?: number;
	locked?: boolean;
};

export type StoreCustomerStatus = "pagou" | "saiu sem comprar";

export type StoreActiveCustomer = {
	id: string;
	emoji: string;
	item: string;
	name: string;
	spent: number;
	status: StoreCustomerStatus;
};

export type StoreAlert = {
	actionLabel: string;
	emoji: string;
	id: string;
	issue: string;
	name: string;
	type: "low" | "notice";
};

export type StoreTopSeller = {
	emoji: string;
	id: string;
	name: string;
	revenue: number;
	sold: number;
};

export type StoreQuickStat = {
	icon: string;
	label: string;
	value: string;
};
