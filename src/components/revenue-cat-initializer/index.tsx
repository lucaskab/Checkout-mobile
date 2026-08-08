import { useEffect } from "react";
import { configureRevenueCat } from "@/services/revenue-cat";

export function RevenueCatInitializer() {
	useEffect(() => {
		configureRevenueCat().catch(() => undefined);
	}, []);

	return null;
}
