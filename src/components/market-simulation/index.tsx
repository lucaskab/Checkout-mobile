import { useEffect } from "react";
import { useGameStore } from "@/stores/game-store";

export function MarketSimulation() {
	const isMarketOpen = useGameStore((state) => state.market.isOpen);
	const processNextCustomer = useGameStore(
		(state) => state.processNextCustomer,
	);
	const processMarketDay = useGameStore((state) => state.processMarketDay);
	const processCheckoutCounter = useGameStore(
		(state) => state.processCheckoutCounter,
	);
	const processStoreIncidents = useGameStore(
		(state) => state.processStoreIncidents,
	);
	const processReceiving = useGameStore((state) => state.processReceiving);

	useEffect(() => {
		if (!isMarketOpen) {
			return;
		}

		processNextCustomer();
		const interval = setInterval(processNextCustomer, 1_000);

		return () => clearInterval(interval);
	}, [isMarketOpen, processNextCustomer]);

	// Day clock (requests, closing time) and the register line (patience, cashier).
	useEffect(() => {
		const tick = () => {
			processCheckoutCounter();
			processStoreIncidents();
			processReceiving();
			processMarketDay();
		};
		tick();
		const interval = setInterval(tick, 1_000);

		return () => clearInterval(interval);
	}, [processCheckoutCounter, processMarketDay, processReceiving, processStoreIncidents]);

	return null;
}
