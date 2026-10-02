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
	const processLotClearing = useGameStore((state) => state.processLotClearing);
	const processMarketEraConstruction = useGameStore((state) => state.processMarketEraConstruction);

	useEffect(() => {
		const tick = () => {
			processProductionJobs();
			// Market expansions under construction open on the same clock.
			processMarketExpansionConstruction();
			// So do the shelves, sectors and fixtures being built inside the market.
			processInteriorConstructions();
			// And the next expansion and the lot being cleared.
			processMarketEraConstruction();
			processLotClearing();
		};
		tick();
		const interval = setInterval(tick, 1_000);

		return () => clearInterval(interval);
	}, [
		processProductionJobs,
		processMarketExpansionConstruction,
		processInteriorConstructions,
		processMarketEraConstruction,
		processLotClearing,
	]);

	return null;
}
