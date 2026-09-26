import { useEffect, useRef } from "react";
import { useBottomSheet } from "@/components/bottom-sheet";
import { useGameStore } from "@/stores/game-store";
import { DayResultSheet } from "./day-result-sheet";

// When a day ends (by the clock or by the player) its results open by themselves.
export function MarketDayPrompts() {
	const { openBottomSheet } = useBottomSheet();
	const phase = useGameStore((state) => state.day.phase);
	const previous = useRef(phase);

	useEffect(() => {
		if (previous.current !== phase && phase === "results") {
			openBottomSheet(<DayResultSheet />);
		}
		previous.current = phase;
	}, [phase, openBottomSheet]);

	return null;
}
