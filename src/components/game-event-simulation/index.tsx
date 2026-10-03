import { useEffect } from "react";
import { useGameStore } from "@/stores/game-store";

export function GameEventSimulation() {
	const processGameEvents = useGameStore((state) => state.processGameEvents);

	useEffect(() => {
		processGameEvents();
		const interval = setInterval(processGameEvents, 1_000);

		return () => clearInterval(interval);
	}, [processGameEvents]);

	return null;
}
