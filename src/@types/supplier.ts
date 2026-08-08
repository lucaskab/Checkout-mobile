export type SupplierCategory = string;

export type SupplierProduct = {
	id: number;
	name: string;
	category: string;
	capacity: number;
	price: number;
	quantity: number;
	productionSavingsPercent?: number;
	shelfTime: string;
	sellPrice: number;
	owned: number;
};

export type SupplierCategoryOption = {
	id: SupplierCategory;
	label: string;
};

export type SupplierToast = {
	message: string;
	type: "success" | "error";
};
