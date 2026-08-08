import { useEffect } from "react";
import { useGameStore } from "@/stores/game-store";

export function MarketSimulation() {
	const isMarketOpen = useGameStore((state) => state.market.isOpen);
	const processNextCustomer = useGameStore(
		(state) => state.processNextCustomer,
	);

	useEffect(() => {
		if (!isMarketOpen) {
			return;
		}

		processNextCustomer();
		const interval = setInterval(processNextCustomer, 1_000);

		return () => clearInterval(interval);
	}, [isMarketOpen, processNextCustomer]);

	return null;
}
