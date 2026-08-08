import { Platform } from "react-native";
import Purchases, {
	LOG_LEVEL,
	PRODUCT_CATEGORY,
	PURCHASES_ERROR_CODE,
	type PurchasesError,
	type PurchasesStoreProduct,
} from "react-native-purchases";
import { currencyProductIds } from "@/data/currency-packs";

let configurationPromise: Promise<boolean> | null = null;

export function configureRevenueCat() {
	configurationPromise ??= configure().catch((error) => {
		configurationPromise = null;
		throw error;
	});

	return configurationPromise;
}

export async function getCurrencyStoreProducts() {
	const isConfigured = await configureRevenueCat();

	if (!isConfigured) {
		return [];
	}

	return Purchases.getProducts(
		currencyProductIds,
		PRODUCT_CATEGORY.NON_SUBSCRIPTION,
	);
}

export function purchaseCurrencyProduct(product: PurchasesStoreProduct) {
	return Purchases.purchaseStoreProduct(product);
}

export function isRevenueCatPurchaseCancelled(error: unknown) {
	return (
		isPurchasesError(error) &&
		error.code === PURCHASES_ERROR_CODE.PURCHASE_CANCELLED_ERROR
	);
}

function configure() {
	return Purchases.isConfigured().then((isConfigured) => {
		if (isConfigured) {
			return true;
		}

		const apiKey = getRevenueCatApiKey();

		if (!apiKey) {
			return false;
		}

		Purchases.setLogLevel(__DEV__ ? LOG_LEVEL.DEBUG : LOG_LEVEL.INFO);
		Purchases.configure({ apiKey });

		return true;
	});
}

function getRevenueCatApiKey() {
	if (__DEV__ && process.env.EXPO_PUBLIC_REVENUECAT_TEST_API_KEY) {
		return process.env.EXPO_PUBLIC_REVENUECAT_TEST_API_KEY;
	}

	if (Platform.OS === "ios") {
		return process.env.EXPO_PUBLIC_REVENUECAT_IOS_API_KEY;
	}

	if (Platform.OS === "android") {
		return process.env.EXPO_PUBLIC_REVENUECAT_ANDROID_API_KEY;
	}

	return undefined;
}

function isPurchasesError(error: unknown): error is PurchasesError {
	return Boolean(
		error &&
			typeof error === "object" &&
			"code" in error &&
			typeof error.code === "string",
	);
}
