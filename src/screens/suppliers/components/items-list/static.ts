import type { SupplierProduct } from "@/@types/supplier";
import { itemCatalog } from "@/data/market-products";
import { productionRecipes } from "@/data/production-sectors";
import {
	getProductionEconomy,
	getSupplierOrderPrice,
} from "@/services/production";

export const initialProducts: SupplierProduct[] = itemCatalog.map((product) => {
	const recipe = productionRecipes.find(
		(item) => item.outputProductId === product.id,
	);

	return {
		capacity: 0,
		category: product.category,
		id: product.id,
		name: product.name,
		owned: 0,
		price: getSupplierOrderPrice(product.id, product.supplierQuantity),
		productionSavingsPercent: recipe
			? getProductionEconomy(recipe).savingsPercent
			: undefined,
		quantity: product.supplierQuantity,
		sellPrice: product.sellingPrice,
		shelfTime: product.supplierTime,
	};
});
