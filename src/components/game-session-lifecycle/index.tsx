import { useEffect } from "react";
import { AppState } from "react-native";
import { useGameStore } from "@/stores/game-store";

export function GameSessionLifecycle() {
	const processSessionResume = useGameStore(
		(state) => state.processSessionResume,
	);

	useEffect(() => {
		processSessionResume();

		const subscription = AppState.addEventListener("change", (nextState) => {
			if (nextState === "active") {
				processSessionResume();
			}
		});

		return () => subscription.remove();
	}, [processSessionResume]);

	return null;
}
