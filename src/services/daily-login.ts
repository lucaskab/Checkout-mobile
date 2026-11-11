import type { MarketEraId } from "@/@types/economy";
import { getMarketEra } from "@/data/economy";

// Daily login reward ("presente do dia"): one claim per calendar day, a 7-day streak that grows each day in a
// row and starts again after a missed day. Coins follow the current expansion (the price of an item level), so
// the gift stays worth something from the mesinha to the hypermarket; the 7th day also gives diamonds.

export type DailyLoginState = {
	/** Local calendar day of the last claim ("2026-10-01"), "" before the first one. */
	lastClaimDay: string;
	/** Days in a row claimed so far (1–7 after a claim). */
	streak: number;
	/** Day the gift was doubled with a video (once a day, after claiming it). */
	bonusDay?: string;
};

export const LOGIN_STREAK_DAYS = 7;
/** Coins of each day of the streak, in item-level prices of the current expansion. The 7th day is worth more than
 * the six before it together (Lucas 06/11, launch audit: the genre's habit, a reason to keep the streak). */
const COIN_STEPS = [1, 1.5, 2, 2.5, 3, 4, 15];
const DIAMONDS_ON_LAST_DAY = 15;
/** Days of the streak that also give a freight coupon (10% off one supplier order; Lucas 11/11). */
export const COUPON_DAYS: readonly number[] = [3, 7];

export function createDailyLoginState(): DailyLoginState {
	return { lastClaimDay: "", streak: 0 };
}

export function normalizeDailyLoginState(value: unknown): DailyLoginState {
	if (!value || typeof value !== "object") return createDailyLoginState();
	const item = value as Partial<DailyLoginState>;
	return {
		lastClaimDay: typeof item.lastClaimDay === "string" ? item.lastClaimDay : "",
		streak:
			typeof item.streak === "number" && Number.isFinite(item.streak)
				? Math.max(0, Math.min(LOGIN_STREAK_DAYS, Math.floor(item.streak)))
				: 0,
		...(typeof item.bonusDay === "string" && item.bonusDay ? { bonusDay: item.bonusDay } : {}),
	};
}

/** Local calendar day of a timestamp. */
export function getDayKey(now: number) {
	const date = new Date(now);
	const pad = (n: number) => String(n).padStart(2, "0");
	return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function canClaimDailyLogin(state: DailyLoginState | undefined, now: number) {
	return (state?.lastClaimDay ?? "") !== getDayKey(now);
}

/** Today's gift was claimed and not doubled yet: a video doubles it (once a day). */
export function canDoubleDailyLogin(state: DailyLoginState | undefined, now: number) {
	const today = getDayKey(now);
	return (state?.lastClaimDay ?? "") === today && state?.bonusDay !== today;
}

/** Day of the streak (1–7) a claim made now would be. */
export function getNextLoginDay(state: DailyLoginState | undefined, now: number) {
	const last = state?.lastClaimDay ?? "";
	const yesterday = getDayKey(now - 24 * 60 * 60_000);
	if (last !== yesterday || !state) return 1;
	return state.streak >= LOGIN_STREAK_DAYS ? 1 : state.streak + 1;
}

export function getLoginReward(day: number, eraId: MarketEraId) {
	const base = getMarketEra(eraId).itemUpgradeBaseCost;
	const step = COIN_STEPS[Math.max(0, Math.min(LOGIN_STREAK_DAYS, day) - 1)];
	const coins = Math.round((base * step) / 10) * 10;
	const clamped = Math.max(1, Math.min(LOGIN_STREAK_DAYS, day));
	return {
		coins,
		diamonds: day >= LOGIN_STREAK_DAYS ? DIAMONDS_ON_LAST_DAY : 0,
		coupons: COUPON_DAYS.includes(clamped) ? 1 : 0,
	};
}

// ---------------------------------------------------------------- Recuperar a sequência (Lucas 11/11)
// A streak broken by 1 to 3 missed days can be bought back: the gift goes on from where it stopped instead of day 1.
// Diamonds for any of those cases; a video only when it was a single day.
export const STREAK_RECOVERY_MAX_DAYS = 3;
export const STREAK_RECOVERY_DIAMONDS_PER_DAY = 10;

const dayNumber = (key: string) => {
	const [y, m, d] = key.split("-").map(Number);
	return Number.isFinite(y) && Number.isFinite(m) && Number.isFinite(d) ? Math.round(Date.UTC(y, m - 1, d) / 86_400_000) : NaN;
};

/** Days missed since the last claim (0 = claimed yesterday or today). */
export function getMissedLoginDays(state: DailyLoginState | undefined, now: number) {
	const last = state?.lastClaimDay ?? "";
	if (!last) return 0;
	const gap = dayNumber(getDayKey(now)) - dayNumber(last);
	return Number.isFinite(gap) ? Math.max(0, gap - 1) : 0;
}

/** What getting the streak back costs now, or null when there is nothing to get back. */
export function getStreakRecovery(state: DailyLoginState | undefined, now: number) {
	const missed = getMissedLoginDays(state, now);
	const streak = state?.streak ?? 0;
	// After day 7 the gift starts again anyway, and a streak of 1 has nothing to lose.
	if (missed < 1 || missed > STREAK_RECOVERY_MAX_DAYS || streak < 2 || streak >= LOGIN_STREAK_DAYS) return null;
	return { missed, streak, diamonds: missed * STREAK_RECOVERY_DIAMONDS_PER_DAY, video: missed === 1 };
}

/** The streak back: as if yesterday's gift had been claimed (the next claim is day streak + 1). */
export function recoverStreak(state: DailyLoginState, now: number): DailyLoginState {
	return { ...state, lastClaimDay: getDayKey(now - 24 * 60 * 60_000) };
}
