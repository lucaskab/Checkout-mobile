import { getDayKey } from "@/services/daily-login";

/**
 * Rewarded videos for diamonds (Lucas 06/11, launch audit): 2 diamonds a video, at most 14 diamonds a day (7 videos),
 * so the free diamonds stay a taste of the speed-ups and the store keeps its reason to exist. The other placements
 * (the missed contract's consolation, doubling the daily gift) have their own once-a-day rules and do not count here.
 *
 * History: 12/10 3 diamonds and at most 5 a day; 14/10 no limit at all ("limitar a quantidade de ad é basicamente
 * limitar o quanto de dinheiro eu vou fazer"); the audit showed a free player could cover every build with videos
 * (~34 videos for a 10 h build, ~US$ 0.06 of ad revenue in Brazil) instead of the €1.99 pack.
 * Research notes in the project doc diamantes-aceleracao-e-compras.
 */
export const AD_REWARD_DIAMONDS = 2;
/** Diamonds the videos can give in one local day. */
export const AD_DAILY_DIAMONDS = 14;

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
	/** Videos still paying today. */
	leftToday: number;
	/** Until the next local midnight when today's videos are used up, else 0. */
	waitMs: number;
	/** "limit" once today's videos are used up. */
	reason: "" | "limit";
};

function msToMidnight(now: number) {
	const next = new Date(now);
	next.setHours(24, 0, 0, 0);
	return Math.max(0, next.getTime() - now);
}

/** The video of now: available until today's AD_DAILY_DIAMONDS are paid out. */
export function getRewardedAdOffer(state: RewardedAdsState | undefined, now = Date.now()): RewardedAdOffer {
	const ads = state ?? createRewardedAdsState();
	const watchedToday = ads.day === getDayKey(now) ? ads.watched : 0;
	const perDay = Math.floor(AD_DAILY_DIAMONDS / AD_REWARD_DIAMONDS);
	const leftToday = Math.max(0, perDay - watchedToday);
	const available = leftToday > 0;
	return { available, watchedToday, leftToday, reward: AD_REWARD_DIAMONDS, waitMs: available ? 0 : msToMidnight(now), reason: available ? "" : "limit" };
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

/**
 * A video of another placement (the missed contract's consolation, doubling the daily gift): those have their own
 * once-a-day rules and do not use the diamond videos of the day, but each video id still pays only once.
 */
export function creditPlacementAd(state: RewardedAdsState | undefined, adId: string, now = Date.now()) {
	const ads = normalizeRewardedAdsState(state);
	if (!adId || ads.processedIds.includes(adId)) return null;
	return { ...ads, lastAt: ads.lastAt, total: ads.total + 1, processedIds: [...ads.processedIds.slice(-49), adId], day: ads.day || getDayKey(now) };
}

/** "2:41" / "5 h 12 min" for the wait. */
export function formatAdWait(ms: number) {
	const minutes = Math.ceil(ms / 60_000);
	if (minutes >= 60) return `${Math.floor(minutes / 60)} h ${minutes % 60} min`;
	const seconds = Math.ceil(ms / 1000);
	return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}
