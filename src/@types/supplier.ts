export type SupplierCategory = string;

export type SupplierProduct = {
	id: number;
	emoji: string;
	name: string;
	category: string;
	price: number;
	quantity: number;
	shelfTime: string;
	sellPrice: number;
	owned: number;
};

export type SupplierCategoryOption = {
	id: SupplierCategory;
	emoji: string;
	label: string;
};

export type SupplierToast = {
	message: string;
	type: "success" | "error";
};
