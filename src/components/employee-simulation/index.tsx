import { useEffect } from "react";
import { useGameStore } from "@/stores/game-store";

export function EmployeeSimulation() {
	const processEmployeePayroll = useGameStore(
		(state) => state.processEmployeePayroll,
	);

	useEffect(() => {
		processEmployeePayroll();
		const interval = setInterval(processEmployeePayroll, 5_000);

		return () => clearInterval(interval);
	}, [processEmployeePayroll]);

	return null;
}
