import type { SupplierProduct } from "@/@types/supplier";
import { itemCatalog } from "@/data/market-products";

export const initialProducts: SupplierProduct[] = itemCatalog.map(
	(product) => ({
		category: product.category,
		emoji: product.emoji,
		id: product.id,
		name: product.name,
		owned: 0,
		price: product.purchasePrice * product.supplierQuantity,
		quantity: product.supplierQuantity,
		sellPrice: product.sellingPrice,
		shelfTime: product.supplierTime,
	}),
);
