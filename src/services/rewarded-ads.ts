import { getDayKey } from "@/services/daily-login";

/**
 * NO LIMIT (Lucas 14/10: "não coloque limite de quantas vezes a pessoa consegue assistir ad no dia… limitar a
 * quantidade de ad é basicamente limitar o quanto de dinheiro eu vou fazer"): any number of videos a day, one after
 * the other, each paying AD_REWARD_DIAMONDS. The daily cap and the gap between videos below are gone; the notes are
 * kept for the history of the sizing. (The ad network may still run out of videos to show for a while: then the
 * button says so — that is Google's fill, not a rule of the game.)
 *
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
	/** Always 0 now (no wait between videos); kept for the pages. */
	waitMs: number;
	/** Always "" now (no daily cap, no gap). */
	reason: "";
};

/** Every video can be watched right away; the count of the day is only for the pages and the stats. */
export function getRewardedAdOffer(state: RewardedAdsState | undefined, now = Date.now()): RewardedAdOffer {
	const ads = state ?? createRewardedAdsState();
	const watchedToday = ads.day === getDayKey(now) ? ads.watched : 0;
	return { available: true, watchedToday, reward: AD_REWARD_DIAMONDS, waitMs: 0, reason: "" };
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
 * once-a-day rules and do not use the five diamond videos of the day, but each video id still pays only once.
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
