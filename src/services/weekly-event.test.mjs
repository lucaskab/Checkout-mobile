import { expect, test } from "bun:test";
import {
	getWeekKey,
	getWeeklyProgress,
	getWeeklyTheme,
	syncWeeklyEvent,
	weeklyThemes,
} from "./weekly-event";
import { itemCatalog } from "../data/market-products";

const WEEK = 7 * 24 * 60 * 60_000;
const now = new Date(2026, 9, 1, 15, 0).getTime();

test("themes take turns week after week", () => {
	const themes = new Set([0, 1, 2, 3].map((n) => getWeeklyTheme(now + n * WEEK).id));
	expect(themes.size).toBe(weeklyThemes.length);
	expect(getWeekKey(now)).not.toBe(getWeekKey(now + WEEK));
});

test("only sales made during the week count towards its goal", () => {
	const theme = getWeeklyTheme(now);
	const product = itemCatalog.find((item) => theme.categories.includes(item.category));
	const sold = { [product.id]: 50 };
	const week = syncWeeklyEvent(undefined, sold, now);
	expect(getWeeklyProgress(week, sold, now).sold).toBe(0);
	sold[product.id] = 50 + theme.goal;
	const progress = getWeeklyProgress(week, sold, now);
	expect(progress.sold).toBe(theme.goal);
	expect(progress.done).toBe(true);
	expect(syncWeeklyEvent(week, sold, now)).toBe(week);
	expect(syncWeeklyEvent(week, sold, now + WEEK).weekKey).not.toBe(week.weekKey);
});
