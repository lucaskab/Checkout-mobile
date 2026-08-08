import { expect, test } from "bun:test";
import {
	createInitialDailyState,
	getDailyGoal,
	markDailySale,
	normalizeDailyState,
} from "./daily-progress";

const firstDay = new Date(2026, 7, 7, 12).getTime();
const nextDay = new Date(2026, 7, 8, 12).getTime();

test("tracks a daily goal and only marks it complete after the target", () => {
	const daily = createInitialDailyState(1, firstDay);
	const inProgress = markDailySale(daily, daily.goal - 1, 2, 3);
	const completed = markDailySale(inProgress, 1, 1, 1);

	expect(getDailyGoal(1)).toBe(1_500);
	expect(inProgress.goalReached).toBe(false);
	expect(completed.goalReached).toBe(true);
	expect(completed.customersServed).toBe(3);
	expect(completed.unitsSold).toBe(4);
});

test("starts a streak when the previous daily goal was completed", () => {
	const daily = markDailySale(
		{ ...createInitialDailyState(2, firstDay), streak: 2 },
		10_000,
		1,
		2,
	);
	const next = normalizeDailyState(daily, 2, nextDay);

	expect(next.dayKey).not.toBe(daily.dayKey);
	expect(next.streak).toBe(3);
	expect(next.lastCompletedDayKey).toBe(daily.dayKey);
	expect(next.revenue).toBe(0);
	expect(next.claimed).toBe(false);
});
