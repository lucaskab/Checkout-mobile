import { getDayKey } from "@/services/daily-login";

/**
 * Rewarded videos (Lucas 12/10): a player who does not pay can still speed up now and then by watching a video —
 * always by choice (no forced ads, no interstitials), a small reward each time that adds up until it buys what they
 * want.
 *
 * Sizing (research notes in the project doc diamantes-aceleracao-e-compras):
 * - A rewarded view earns the game about $0.01–0.03 in the US/Europe and well under a cent in Brazil; a diamond is
 *   worth ~2 cents in the store. Genre practice pays more than the ad earns, because the video is there to keep
 *   non-payers playing and to give them a taste of the speed-ups — players who use rewarded ads buy far more often.
 * - So each video gives 3 diamonds (4 % of the smallest pack, ~10–12 min of speed-up) and the fifth of the day 5:
 *   at most 17 diamonds a day. That is a 1-hour wait every day or a 1-day wait every 9 days — worth watching, but a
 *   long build still asks for money, and a player who wants it now still buys.
 * - At most 5 a day, at least 3 minutes apart (a cap protects the ads' value and the store; the gap spreads them over
 *   the session instead of five in a row).
 */
export const AD_REWARD_DIAMONDS = 3;
/** The last video of the day pays a little more (a reason to come back and finish the day's five). */
export const AD_LAST_OF_DAY_DIAMONDS = 5;
export const AD_DAILY_CAP = 5;
export const AD_COOLDOWN_MS = 3 * 60_000;

export type RewardedAdsState = {
	/** Local calendar day of the count below ("2026-10-12"). */
	day: string;
	/** Videos rewarded on that day. */
	watched: number;
	/** When the last one was rewarded. */
	lastAt: number;
	/** Videos rewarded since the start. */
	total: number;
	/** Diamonds earned from videos since the start. */
	diamonds: number;
	/** The last videos credited (each id once). */
	processedIds: string[];
};

export function createRewardedAdsState(): RewardedAdsState {
	return { day: "", watched: 0, lastAt: 0, total: 0, diamonds: 0, processedIds: [] };
}

export function normalizeRewardedAdsState(value: unknown): RewardedAdsState {
	if (!value || typeof value !== "object") return createRewardedAdsState();
	const item = value as Partial<RewardedAdsState>;
	const count = (n: unknown) => (typeof n === "number" && Number.isFinite(n) ? Math.max(0, Math.floor(n)) : 0);
	return {
		day: typeof item.day === "string" ? item.day : "",
		watched: count(item.watched),
		lastAt: count(item.lastAt),
		total: count(item.total),
		diamonds: count(item.diamonds),
		processedIds: Array.isArray(item.processedIds)
			? item.processedIds.filter((id): id is string => typeof id === "string").slice(-50)
			: [],
	};
}

export type RewardedAdOffer = {
	/** A video can be watched now. */
	available: boolean;
	/** Videos already rewarded today. */
	watchedToday: number;
	/** Diamonds the next video gives. */
	reward: number;
	/** Wait before the next one (0 = now; until tomorrow when today's are done). */
	waitMs: number;
	/** Why not now: "" | "cooldown" | "daily-cap". */
	reason: "" | "cooldown" | "daily-cap";
};

function nextMidnight(now: number) {
	const date = new Date(now);
	date.setHours(24, 0, 0, 0);
	return date.getTime();
}

export function getRewardedAdOffer(state: RewardedAdsState | undefined, now = Date.now()): RewardedAdOffer {
	const ads = state ?? createRewardedAdsState();
	const watchedToday = ads.day === getDayKey(now) ? ads.watched : 0;
	const reward = watchedToday + 1 >= AD_DAILY_CAP ? AD_LAST_OF_DAY_DIAMONDS : AD_REWARD_DIAMONDS;
	if (watchedToday >= AD_DAILY_CAP)
		return { available: false, watchedToday, reward: 0, waitMs: Math.max(0, nextMidnight(now) - now), reason: "daily-cap" };
	const waitMs = ads.lastAt ? Math.max(0, ads.lastAt + AD_COOLDOWN_MS - now) : 0;
	if (waitMs > 0) return { available: false, watchedToday, reward, waitMs, reason: "cooldown" };
	return { available: true, watchedToday, reward, waitMs: 0, reason: "" };
}

/** The state after the video `adId` was watched to the end, and the diamonds it gives (0 = refused). */
export function rewardAd(state: RewardedAdsState | undefined, adId: string, now = Date.now()) {
	const ads = normalizeRewardedAdsState(state);
	const offer = getRewardedAdOffer(ads, now);
	if (!adId || ads.processedIds.includes(adId) || !offer.available) return { state: ads, diamonds: 0 };
	return {
		diamonds: offer.reward,
		state: {
			day: getDayKey(now),
			watched: offer.watchedToday + 1,
			lastAt: now,
			total: ads.total + 1,
			diamonds: ads.diamonds + offer.reward,
			processedIds: [...ads.processedIds.slice(-49), adId],
		},
	};
}

/** "2:41" / "5 h 12 min" for the wait. */
export function formatAdWait(ms: number) {
	const minutes = Math.ceil(ms / 60_000);
	if (minutes >= 60) return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
	const seconds = Math.ceil(ms / 1000);
	return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
