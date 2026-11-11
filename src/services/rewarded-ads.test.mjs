import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";

// Rewarded videos: by choice, 2 diamonds each, at most 14 diamonds a day (Lucas 06/11, launch audit).
globalThis.__DEV__ = true;
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../stores/game-store.ts");
const ads = await import("./rewarded-ads.ts");
const { getSkipDiamondCost } = await import("../data/diamond-skip.ts");
const { currencyPacks } = await import("../data/currency-packs.ts");

const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const store = () => useGameStore.getState();
const MIN = 60_000;
const noon = new Date(2026, 9, 12, 12, 0, 0).getTime();

describe("rules", () => {
	test("2 diamonds a video, 7 videos a day (14 diamonds), then back at midnight", () => {
		let state = ads.createRewardedAdsState();
		const paid = [];
		for (let i = 0; i < 9; i++) {
			const result = ads.rewardAd(state, `ad-${i}`, noon + i * 30_000);
			paid.push(result.diamonds);
			state = result.state;
		}
		expect(paid).toEqual([2, 2, 2, 2, 2, 2, 2, 0, 0]);
		expect(paid.reduce((a, b) => a + b, 0)).toBe(ads.AD_DAILY_DIAMONDS);
		const offer = ads.getRewardedAdOffer(state, noon + 10 * MIN);
		expect(offer).toEqual(expect.objectContaining({ available: false, watchedToday: 7, leftToday: 0, reason: "limit" }));
		expect(offer.waitMs).toBe(12 * 60 * MIN - 10 * MIN);
		// the next day it pays again
		const tomorrow = noon + 24 * 60 * MIN;
		expect(ads.getRewardedAdOffer(state, tomorrow)).toEqual(expect.objectContaining({ available: true, watchedToday: 0, leftToday: 7 }));
		expect(ads.rewardAd(state, "ad-next-day", tomorrow).diamonds).toBe(2);
	});

	test("the same video is paid once", () => {
		const first = ads.rewardAd(undefined, "same", noon);
		expect(ads.rewardAd(first.state, "same", noon + 10 * MIN).diamonds).toBe(0);
	});

	test("a day of videos is worth about an hour of skipping, never a long build", () => {
		expect(ads.AD_DAILY_DIAMONDS).toBeGreaterThanOrEqual(getSkipDiamondCost(60 * MIN));
		expect(ads.AD_DAILY_DIAMONDS).toBeLessThan(getSkipDiamondCost(6 * 60 * MIN));
	});
});

describe("store", () => {
	test("a watched video credits its diamonds once", () => {
		useGameStore.setState({ logistics: { ...store().logistics, premiumCurrency: 0 } });
		expect(store().claimRewardedAd("ad-1")).toBe(2);
		expect(store().logistics.premiumCurrency).toBe(2);
		expect(store().claimRewardedAd("ad-1")).toBe(null);
		// Another one right away pays too (up to the day's limit).
		expect(store().claimRewardedAd("ad-2")).toBe(2);
		expect(store().rewardedAds.total).toBe(2);
	});

	test("the count is saved with the game", () => {
		store().claimRewardedAd("ad-3");
		const saved = useGameStore.persist.getOptions().partialize(store());
		expect(saved.rewardedAds.watched).toBe(1);
	});

	test("old saves without it start fresh", () => {
		expect(ads.normalizeRewardedAdsState(undefined)).toEqual(ads.createRewardedAdsState());
		expect(ads.normalizeRewardedAdsState({ watched: "x", processedIds: [1, "a"] }).processedIds).toEqual(["a"]);
	});
});

// Lucas 10/11: the player picks diamonds or coins; 7 coin videos a day apart from the 7 diamond ones, coins low at
// the start and growing with the level.
describe("coin videos", () => {
	test("coins grow on every level, low at the start", () => {
		const values = Array.from({ length: 60 }, (_, i) => ads.getAdCoinReward(i + 1));
		for (let i = 1; i < values.length; i++) expect(values[i]).toBeGreaterThanOrEqual(values[i - 1]);
		expect(values[0]).toBeLessThanOrEqual(100);
		expect(ads.getAdCoinReward(10)).toBeGreaterThan(600);
		expect(ads.getAdCoinReward(10)).toBeLessThan(1_000);
		expect(ads.getAdCoinReward(30)).toBeGreaterThan(ads.getAdCoinReward(20));
	});

	test("7 coin videos a day, counted apart from the diamond ones", () => {
		let state = ads.createRewardedAdsState();
		for (let i = 0; i < 7; i++) state = ads.rewardAd(state, `d-${i}`, noon + i).state;
		expect(ads.getRewardedAdOffer(state, noon).available).toBe(false);
		const coins = [];
		for (let i = 0; i < 9; i++) {
			const result = ads.rewardCoinAd(state, `c-${i}`, 10, noon + 100 + i);
			state = result.state;
			coins.push(result.coins);
		}
		expect(coins.filter((c) => c > 0)).toHaveLength(7);
		expect(coins[0]).toBe(ads.getAdCoinReward(10));
		expect(ads.getRewardedCoinAdOffer(state, 10, noon).available).toBe(false);
		expect(ads.getRewardedVideosLeft(state, 10, noon)).toBe(0);
		// a new day
		const tomorrow = noon + 24 * 60 * MIN;
		expect(ads.getRewardedCoinAdOffer(state, 10, tomorrow).leftToday).toBe(7);
		expect(ads.getRewardedVideosLeft(state, 10, tomorrow)).toBe(14);
		// the same video id never pays twice
		expect(ads.rewardCoinAd(state, "c-0", 10, tomorrow).coins).toBe(0);
	});

	test("store: a coin video adds the level's coins, keeps diamonds", () => {
		useGameStore.setState({ coins: 100, market: { ...store().market, level: 12 } });
		const diamonds = store().logistics.premiumCurrency;
		const got = store().claimRewardedCoinAd("coin-ad-1");
		expect(got).toBe(ads.getAdCoinReward(12));
		expect(store().coins).toBe(100 + got);
		expect(store().logistics.premiumCurrency).toBe(diamonds);
		expect(store().claimRewardedCoinAd("coin-ad-1")).toBe(null);
	});

	test("old saves (no coin fields) load with 7 coin videos", () => {
		const old = { day: "2026-10-12", watched: 3, lastAt: 1, total: 3, diamonds: 6, processedIds: ["a"] };
		const state = ads.normalizeRewardedAdsState(old);
		expect(state.coinWatched).toBe(0);
		expect(ads.getRewardedCoinAdOffer(state, 5, noon).leftToday).toBe(7);
	});
});
