import { useIAP } from "expo-iap";
import { createContext, type ReactNode, useContext, useEffect } from "react";
import {
	logisticsConsumableProductIds,
	logisticsIapProducts,
} from "@/data/iap-products";
import { useGameStore } from "@/stores/game-store";

type IapContextValue = {
	connected: boolean;
	purchaseLogisticsProduct: (productId: string) => Promise<void>;
};

const IapContext = createContext<IapContextValue | null>(null);

type IapProviderProps = {
	children: ReactNode;
};

export function IapProvider({ children }: IapProviderProps) {
	const addPremiumEntitlement = useGameStore(
		(state) => state.addPremiumEntitlement,
	);
	const { connected, fetchProducts, finishTransaction, requestPurchase } =
		useIAP({
			onPurchaseSuccess: async (purchase) => {
				addPremiumEntitlement(purchase.productId);
				await finishTransaction({
					isConsumable: logisticsConsumableProductIds.some(
						(productId) => productId === purchase.productId,
					),
					purchase,
				});
			},
		});

	useEffect(() => {
		if (!connected) {
			return;
		}

		fetchProducts({
			skus: logisticsConsumableProductIds,
			type: "in-app",
		});
		fetchProducts({
			skus: [logisticsIapProducts.vipMonthly],
			type: "subs",
		});
	}, [connected, fetchProducts]);

	function purchaseLogisticsProduct(productId: string) {
		const isSubscription = productId === logisticsIapProducts.vipMonthly;

		return requestPurchase({
			request: {
				apple: { sku: productId },
				google: { skus: [productId] },
			},
			type: isSubscription ? "subs" : "in-app",
		}).then(() => undefined);
	}

	return (
		<IapContext.Provider value={{ connected, purchaseLogisticsProduct }}>
			{children}
		</IapContext.Provider>
	);
}

export function useIap() {
	const context = useContext(IapContext);

	if (!context) {
		throw new Error("useIap must be used within IapProvider.");
	}

	return context;
}
