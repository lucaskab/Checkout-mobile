import { useEffect } from "react";
import { useGameStore } from "@/stores/game-store";

export function ProductionSimulation() {
	const processProductionJobs = useGameStore(
		(state) => state.processProductionJobs,
	);
	const processMarketExpansionConstruction = useGameStore(
		(state) => state.processMarketExpansionConstruction,
	);
	const processInteriorConstructions = useGameStore(
		(state) => state.processInteriorConstructions,
	);

	useEffect(() => {
		const tick = () => {
			processProductionJobs();
			// Market expansions under construction open on the same clock.
			processMarketExpansionConstruction();
			// So do the shelves, sectors and fixtures being built inside the market.
			processInteriorConstructions();
		};
		tick();
		const interval = setInterval(tick, 1_000);

		return () => clearInterval(interval);
	}, [
		processProductionJobs,
		processMarketExpansionConstruction,
		processInteriorConstructions,
	]);

	return null;
}
