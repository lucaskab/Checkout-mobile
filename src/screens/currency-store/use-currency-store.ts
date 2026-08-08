import { useEffect, useRef, useState } from "react";
import type { PurchasesStoreProduct } from "react-native-purchases";
import type {
	CurrencyPack,
	RevenueCatStoreStatus,
} from "@/@types/currency-purchase";
import { currencyPacks, getCurrencyPack } from "@/data/currency-packs";
import {
	configureRevenueCat,
	getCurrencyStoreProducts,
	isRevenueCatPurchaseCancelled,
	purchaseCurrencyProduct,
} from "@/services/revenue-cat";
import { useGameStore } from "@/stores/game-store";

type PurchaseFeedback = {
	kind: "error" | "success";
	message: string;
};

export function useCurrencyStore() {
	const grantCurrencyPurchase = useGameStore(
		(state) => state.grantCurrencyPurchase,
	);
	const purchaseInFlight = useRef(false);
	const [feedback, setFeedback] = useState<PurchaseFeedback | null>(null);
	const [products, setProducts] = useState<
		Record<string, PurchasesStoreProduct>
	>({});
	const [purchasingProductId, setPurchasingProductId] = useState<string | null>(
		null,
	);
	const [status, setStatus] = useState<RevenueCatStoreStatus>("loading");

	async function loadProducts() {
		setFeedback(null);
		setStatus("loading");

		const result = await loadStoreProducts();

		setProducts(result.products);
		setStatus(result.status);
	}

	useEffect(() => {
		let isMounted = true;

		loadStoreProducts().then((result) => {
			if (!isMounted) {
				return;
			}

			setProducts(result.products);
			setStatus(result.status);
		});

		return () => {
			isMounted = false;
		};
	}, []);

	async function purchase(pack: CurrencyPack) {
		const product = products[pack.productId];

		if (!product || purchaseInFlight.current) {
			return;
		}

		purchaseInFlight.current = true;
		setFeedback(null);
		setPurchasingProductId(pack.productId);

		try {
			const result = await purchaseCurrencyProduct(product);
			const purchasedPack = getCurrencyPack(result.productIdentifier);

			if (!purchasedPack) {
				throw new Error("Purchased product is not in the currency catalog.");
			}

			const wasCredited = grantCurrencyPurchase({
				coins: purchasedPack.coins,
				diamonds: purchasedPack.diamonds,
				transactionId: result.transaction.transactionIdentifier,
			});

			setFeedback({
				kind: "success",
				message: wasCredited
					? `${purchasedPack.name} foi creditado na sua conta.`
					: "Esta compra já havia sido creditada.",
			});
		} catch (error) {
			if (!isRevenueCatPurchaseCancelled(error)) {
				setFeedback({
					kind: "error",
					message:
						"Não foi possível concluir a compra. Confira a loja e tente novamente.",
				});
			}
		} finally {
			purchaseInFlight.current = false;
			setPurchasingProductId(null);
		}
	}

	return {
		availableProductCount: Object.keys(products).length,
		feedback,
		loadProducts,
		products,
		purchase,
		purchasingProductId,
		status,
		totalProductCount: currencyPacks.length,
	};
}

async function loadStoreProducts(): Promise<{
	products: Record<string, PurchasesStoreProduct>;
	status: RevenueCatStoreStatus;
}> {
	try {
		const isConfigured = await configureRevenueCat();

		if (!isConfigured) {
			return { products: {}, status: "missing-configuration" };
		}

		const storeProducts = await getCurrencyStoreProducts();

		return {
			products: Object.fromEntries(
				storeProducts.map((product) => [product.identifier, product]),
			),
			status: storeProducts.length > 0 ? "ready" : "unavailable",
		};
	} catch {
		return { products: {}, status: "unavailable" };
	}
}
