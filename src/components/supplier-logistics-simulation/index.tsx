import { useEffect } from "react";
import { useGameStore } from "@/stores/game-store";

export function SupplierLogisticsSimulation() {
	const processSupplierOrders = useGameStore(
		(state) => state.processSupplierOrders,
	);

	useEffect(() => {
		processSupplierOrders();
		const interval = setInterval(processSupplierOrders, 1_000);

		return () => clearInterval(interval);
	}, [processSupplierOrders]);

	return null;
}
