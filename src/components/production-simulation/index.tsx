import { useEffect } from "react";
import { useGameStore } from "@/stores/game-store";

export function ProductionSimulation() {
	const processProductionJobs = useGameStore(
		(state) => state.processProductionJobs,
	);

	useEffect(() => {
		processProductionJobs();
		const interval = setInterval(processProductionJobs, 1_000);

		return () => clearInterval(interval);
	}, [processProductionJobs]);

	return null;
}
