import { useEffect } from "react";
import { useGameStore } from "@/stores/game-store";

const SPOILAGE_CHECK_INTERVAL_MS = 60_000;

export function InventorySpoilageSimulation() {
	const processInventorySpoilage = useGameStore(
		(state) => state.processInventorySpoilage,
	);

	useEffect(() => {
		processInventorySpoilage();
		const interval = setInterval(
			processInventorySpoilage,
			SPOILAGE_CHECK_INTERVAL_MS,
		);

		return () => clearInterval(interval);
	}, [processInventorySpoilage]);

	return null;
}
