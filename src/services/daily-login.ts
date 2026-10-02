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
};

export const LOGIN_STREAK_DAYS = 7;
/** Coins of each day of the streak, in item-level prices of the current expansion. */
const COIN_STEPS = [1, 1.5, 2, 2.5, 3, 4, 6];
const DIAMONDS_ON_LAST_DAY = 5;

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
	return { coins, diamonds: day >= LOGIN_STREAK_DAYS ? DIAMONDS_ON_LAST_DAY : 0 };
}
