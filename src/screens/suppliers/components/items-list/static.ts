import type { SupplierProduct } from "@/@types/supplier";
import { itemCatalog } from "@/data/market-products";
import { productionRecipes } from "@/data/production-sectors";
import { getProductionEconomy } from "@/services/production";

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
		productionSavingsPercent: recipe
			? getProductionEconomy(recipe).savingsPercent
			: undefined,
		sellPrice: product.sellingPrice,
		shelfTime: product.supplierTime,
	};
});
