import { useEffect, useState } from "react";

// Re-renders every second while active, for countdowns.
export function useNow(active = true) {
	const [now, setNow] = useState(Date.now());

	useEffect(() => {
		if (!active) return;
		setNow(Date.now());
		const timer = setInterval(() => setNow(Date.now()), 1_000);
		return () => clearInterval(timer);
	}, [active]);

	return now;
}

export function formatClock(ms: number) {
	const seconds = Math.max(0, Math.ceil(ms / 1_000));
	return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
