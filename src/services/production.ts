import type {
	ProductionEconomy,
	ProductionJob,
	ProductionRecipe,
} from "@/@types/production";
import { itemCatalog } from "@/data/market-products";
import { productionRecipes } from "@/data/production-sectors";

const SUPPLIER_PRODUCTION_MARKUP = 1.25;

export function getProductionDiamondCost(remainingMs: number) {
	return Math.max(1, Math.ceil(Math.max(remainingMs, 0) / 60_000));
}

export function getProductionProgress(job: ProductionJob, now: number) {
	const duration = job.endsAt - job.startedAt;

	if (duration <= 0) {
		return 1;
	}

	return Math.min(1, Math.max(0, (now - job.startedAt) / duration));
}

export function getProductionRemainingTime(endsAt: number, now: number) {
	const remainingSeconds = Math.max(0, Math.ceil((endsAt - now) / 1_000));
	const minutes = Math.floor(remainingSeconds / 60);
	const seconds = remainingSeconds % 60;

	return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function getRecipeIngredientCost(recipe: ProductionRecipe) {
	return recipe.ingredients.reduce((total, ingredient) => {
		const product = itemCatalog.find(
			(item) => item.id === ingredient.productId,
		);

		return total + (product?.purchasePrice ?? 0) * ingredient.quantity;
	}, 0);
}

export function getRecipeIngredientSaleValue(recipe: ProductionRecipe) {
	return recipe.ingredients.reduce((total, ingredient) => {
		const product = itemCatalog.find(
			(item) => item.id === ingredient.productId,
		);

		return total + (product?.sellingPrice ?? 0) * ingredient.quantity;
	}, 0);
}

export function getSupplierUnitPrice(productId: number) {
	const product = itemCatalog.find((item) => item.id === productId);
	const recipe = productionRecipes.find(
		(item) => item.outputProductId === productId,
	);

	if (!product) {
		return 0;
	}

	if (!recipe) {
		return product.purchasePrice;
	}

	const productionUnitCost =
		getRecipeIngredientCost(recipe) / recipe.outputQuantity;
	const minimumSupplierPrice = Math.floor(productionUnitCost) + 1;
	const markedUpPrice = Math.ceil(
		productionUnitCost * SUPPLIER_PRODUCTION_MARKUP,
	);

	return Math.max(
		minimumSupplierPrice,
		Math.min(markedUpPrice, product.sellingPrice - 1),
	);
}

export function getSupplierOrderPrice(productId: number, quantity: number) {
	return getSupplierUnitPrice(productId) * Math.max(0, Math.floor(quantity));
}

export function getProductionEconomy(
	recipe: ProductionRecipe,
): ProductionEconomy {
	const product = itemCatalog.find(
		(item) => item.id === recipe.outputProductId,
	);
	const ingredientPurchaseCost = getRecipeIngredientCost(recipe);
	const ingredientSaleValue = getRecipeIngredientSaleValue(recipe);
	const productionUnitCost = ingredientPurchaseCost / recipe.outputQuantity;
	const supplierUnitPrice = getSupplierUnitPrice(recipe.outputProductId);
	const craftedBatchRevenue =
		(product?.sellingPrice ?? 0) * recipe.outputQuantity;

	return {
		craftedBatchRevenue,
		ingredientPurchaseCost,
		ingredientSaleValue,
		opportunityProfit: craftedBatchRevenue - ingredientSaleValue,
		productionUnitCost,
		savingsPercent:
			supplierUnitPrice > 0
				? Math.round(
						((supplierUnitPrice - productionUnitCost) / supplierUnitPrice) *
							100,
					)
				: 0,
		supplierUnitPrice,
	};
}

export function getRecipeProfitMargin(recipe: ProductionRecipe) {
	const product = itemCatalog.find(
		(item) => item.id === recipe.outputProductId,
	);
	const revenue = (product?.sellingPrice ?? 0) * recipe.outputQuantity;

	if (revenue <= 0) {
		return 0;
	}

	return Math.round(
		((revenue - getRecipeIngredientCost(recipe)) / revenue) * 100,
	);
}
