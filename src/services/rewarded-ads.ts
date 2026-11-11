import { roundPrice } from "@/data/economy";
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

/**
 * Rewarded videos for coins (Lucas 10/11: "a pessoa consegue escolher se quer assistir ad pra ganhar diamante ou
 * moeda amarela… 7 vezes pegando diamante e mais 7 vezes pegando moedas… valores baixos e crescendo baseado no
 * nível do jogador"). A count of its own: 7 coin videos a day, apart from the 7 diamond ones. Each pays about half
 * a 10-minute turn of profit of a regular player at the player's level (getAdCoinReward), so it grows a little on
 * every level and keeps the same weight from the sidewalk table to the chain.
 */
export const AD_DAILY_COIN_VIDEOS = 7;
/** Share of a 10-minute turn of profit one coin video pays. */
export const AD_COIN_TURN_SHARE = 0.5;
/**
 * Profit per 10-minute turn of a regular player by level (the economy robot: the level they reach each expansion
 * at, and that expansion's average profit — project doc economia-produtos). Between two marks it grows smoothly.
 */
const LEVEL_TURN_PROFIT: readonly [number, number][] = [
	[1, 158], [3, 539], [6, 856], [7, 1_078], [10, 1_579], [13, 2_707], [17, 3_858],
	[22, 6_151], [29, 10_913], [40, 22_589], [53, 36_637],
];
/** Past the last mark the profit keeps growing 3 % a level. */
const LEVEL_TURN_GROWTH = 1.03;

/** A regular player's profit per 10-minute turn at `level` (geometric between the marks). */
export function getLevelTurnProfit(level: number) {
	const lv = Math.max(1, Math.floor(Number(level) || 1));
	const last = LEVEL_TURN_PROFIT[LEVEL_TURN_PROFIT.length - 1];
	if (lv >= last[0]) return last[1] * LEVEL_TURN_GROWTH ** (lv - last[0]);
	for (let i = 1; i < LEVEL_TURN_PROFIT.length; i++) {
		const [l1, p1] = LEVEL_TURN_PROFIT[i];
		if (lv > l1) continue;
		const [l0, p0] = LEVEL_TURN_PROFIT[i - 1];
		return p0 * (p1 / p0) ** ((lv - l0) / (l1 - l0));
	}
	return LEVEL_TURN_PROFIT[0][1];
}

/** Coins one video gives at `level` (round numbers, never below 50). */
export function getAdCoinReward(level: number) {
	return roundPrice(Math.max(50, getLevelTurnProfit(level) * AD_COIN_TURN_SHARE));
}

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
	/** Coin videos: local day of the count, videos rewarded that day, coins earned since the start. */
	coinDay: string;
	coinWatched: number;
	coins: number;
};

export function createRewardedAdsState(): RewardedAdsState {
	return { day: "", watched: 0, lastAt: 0, total: 0, diamonds: 0, processedIds: [], coinDay: "", coinWatched: 0, coins: 0 };
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
		coinDay: typeof item.coinDay === "string" ? item.coinDay : "",
		coinWatched: count(item.coinWatched),
		coins: count(item.coins),
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

/** The coin video of now at `level`: available until today's AD_DAILY_COIN_VIDEOS are paid out. */
export function getRewardedCoinAdOffer(state: RewardedAdsState | undefined, level: number, now = Date.now()): RewardedAdOffer {
	const ads = normalizeRewardedAdsState(state);
	const watchedToday = ads.coinDay === getDayKey(now) ? ads.coinWatched : 0;
	const leftToday = Math.max(0, AD_DAILY_COIN_VIDEOS - watchedToday);
	const available = leftToday > 0;
	return { available, watchedToday, leftToday, reward: getAdCoinReward(level), waitMs: available ? 0 : msToMidnight(now), reason: available ? "" : "limit" };
}

/** The state after the coin video `adId` was watched to the end, and the coins it gives (0 = refused). */
export function rewardCoinAd(state: RewardedAdsState | undefined, adId: string, level: number, now = Date.now()) {
	const ads = normalizeRewardedAdsState(state);
	const offer = getRewardedCoinAdOffer(ads, level, now);
	if (!adId || ads.processedIds.includes(adId) || !offer.available) return { state: ads, coins: 0 };
	return {
		coins: offer.reward,
		state: {
			...ads,
			coinDay: getDayKey(now),
			coinWatched: offer.watchedToday + 1,
			lastAt: now,
			total: ads.total + 1,
			coins: ads.coins + offer.reward,
			processedIds: [...ads.processedIds.slice(-49), adId],
		},
	};
}

/** Videos left today for either prize (the HUD's "Diamante grátis" button counts them). */
export function getRewardedVideosLeft(state: RewardedAdsState | undefined, level: number, now = Date.now()) {
	return getRewardedAdOffer(state, now).leftToday + getRewardedCoinAdOffer(state, level, now).leftToday;
}

/** The state after the video `adId` was watched to the end, and the diamonds it gives (0 = refused). */
export function rewardAd(state: RewardedAdsState | undefined, adId: string, now = Date.now()) {
	const ads = normalizeRewardedAdsState(state);
	const offer = getRewardedAdOffer(ads, now);
	if (!adId || ads.processedIds.includes(adId) || !offer.available) return { state: ads, diamonds: 0 };
	return {
		diamonds: offer.reward,
		state: {
			...ads,
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
