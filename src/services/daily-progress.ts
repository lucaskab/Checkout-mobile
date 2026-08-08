import type { GameDailyState } from "@/@types/game";

export function getDayKey(now = Date.now()) {
	const date = new Date(now);

	return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

export function getDailyGoal(level: number) {
	return Math.round((1_500 + Math.max(0, level - 1) * 350) / 50) * 50;
}

export function createInitialDailyState(
	level: number,
	now = Date.now(),
): GameDailyState {
	return {
		claimed: false,
		customersServed: 0,
		goal: getDailyGoal(level),
		goalReached: false,
		lastCompletedDayKey: null,
		streak: 0,
		unitsSold: 0,
		dayKey: getDayKey(now),
		revenue: 0,
	};
}

export function normalizeDailyState(
	state: Partial<GameDailyState> | undefined,
	level: number,
	now = Date.now(),
) {
	const initial = createInitialDailyState(level, now);

	if (!state || state.dayKey === undefined) {
		return initial;
	}

	const currentDayKey = getDayKey(now);
	if (state.dayKey === currentDayKey) {
		return {
			...initial,
			...state,
			goal: state.goal ?? initial.goal,
		};
	}

	const completedPreviousDay = state.goalReached === true;

	return {
		...initial,
		lastCompletedDayKey: completedPreviousDay
			? state.dayKey
			: (state.lastCompletedDayKey ?? null),
		streak: completedPreviousDay ? (state.streak ?? 0) + 1 : 0,
	};
}

export function markDailySale(
	daily: GameDailyState,
	revenue: number,
	customers: number,
	units: number,
) {
	const nextRevenue = daily.revenue + revenue;

	return {
		...daily,
		customersServed: daily.customersServed + customers,
		goalReached: daily.goalReached || nextRevenue >= daily.goal,
		unitsSold: daily.unitsSold + units,
		revenue: nextRevenue,
	};
}
