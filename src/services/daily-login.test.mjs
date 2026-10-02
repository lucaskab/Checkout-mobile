import { expect, test } from "bun:test";
import {
	canClaimDailyLogin,
	getDayKey,
	getLoginReward,
	getNextLoginDay,
	normalizeDailyLoginState,
} from "./daily-login";

const DAY = 24 * 60 * 60_000;
const now = new Date(2026, 9, 1, 15, 0).getTime();

test("one gift per calendar day, a streak that grows and restarts after a missed day", () => {
	const fresh = normalizeDailyLoginState(undefined);
	expect(canClaimDailyLogin(fresh, now)).toBe(true);
	expect(getNextLoginDay(fresh, now)).toBe(1);
	const claimed = { lastClaimDay: getDayKey(now), streak: 3 };
	expect(canClaimDailyLogin(claimed, now)).toBe(false);
	expect(getNextLoginDay(claimed, now + DAY)).toBe(4);
	expect(getNextLoginDay(claimed, now + 2 * DAY)).toBe(1);
	expect(getNextLoginDay({ lastClaimDay: getDayKey(now), streak: 7 }, now + DAY)).toBe(1);
});

test("gifts grow during the week, follow the expansion and the 7th day gives diamonds", () => {
	expect(getLoginReward(2, "mesinha").coins).toBeGreaterThan(getLoginReward(1, "mesinha").coins);
	expect(getLoginReward(1, "mercadinho").coins).toBeGreaterThan(getLoginReward(1, "mesinha").coins);
	expect(getLoginReward(6, "tenda").diamonds).toBe(0);
	expect(getLoginReward(7, "tenda").diamonds).toBeGreaterThan(0);
});
