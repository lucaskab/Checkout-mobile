import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";

// Rewarded videos (Lucas 12/10): by choice, a small reward each, at most a few a day, never too generous.
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
	test("a video pays 3 diamonds, the fifth of the day 5, then none until tomorrow", () => {
		let state = ads.createRewardedAdsState();
		const paid = [];
		for (let i = 0; i < 7; i++) {
			const result = ads.rewardAd(state, `ad-${i}`, noon + i * 10 * MIN);
			paid.push(result.diamonds);
			state = result.state;
		}
		expect(paid).toEqual([3, 3, 3, 3, 5, 0, 0]);
		expect(ads.getRewardedAdOffer(state, noon + 70 * MIN)).toEqual(expect.objectContaining({ available: false, reason: "daily-cap" }));
		// Next day it starts again.
		const tomorrow = noon + 24 * 60 * MIN;
		expect(ads.getRewardedAdOffer(state, tomorrow)).toEqual(expect.objectContaining({ available: true, watchedToday: 0, reward: 3 }));
		expect(ads.rewardAd(state, "ad-next-day", tomorrow).diamonds).toBe(3);
	});

	test("videos are at least 3 minutes apart", () => {
		const first = ads.rewardAd(undefined, "a", noon);
		expect(ads.rewardAd(first.state, "b", noon + 2 * MIN).diamonds).toBe(0);
		const offer = ads.getRewardedAdOffer(first.state, noon + 2 * MIN);
		expect(offer.reason).toBe("cooldown");
		expect(offer.waitMs).toBe(MIN);
		expect(ads.rewardAd(first.state, "b", noon + 3 * MIN).diamonds).toBe(3);
	});

	test("the same video is paid once", () => {
		const first = ads.rewardAd(undefined, "same", noon);
		expect(ads.rewardAd(first.state, "same", noon + 10 * MIN).diamonds).toBe(0);
	});

	test("balance: worth it, but never a substitute for buying", () => {
		const perDay = (ads.AD_DAILY_CAP - 1) * ads.AD_REWARD_DIAMONDS + ads.AD_LAST_OF_DAY_DIAMONDS;
		expect(perDay).toBe(17);
		// Worth it: a day of videos skips at least an hour of waiting; one video a few minutes.
		expect(perDay).toBeGreaterThanOrEqual(getSkipDiamondCost(60 * MIN));
		expect(ads.AD_REWARD_DIAMONDS).toBeGreaterThanOrEqual(getSkipDiamondCost(10 * MIN));
		// Not too much: a week of every video is less than the €4,99 pack, and a 1-day skip takes over a week.
		const pouch = currencyPacks.find((p) => p.id === "diamonds-pouch");
		expect(perDay * 7).toBeLessThan(pouch.diamonds);
		expect(getSkipDiamondCost(24 * 60 * MIN) / perDay).toBeGreaterThan(7);
	});
});

describe("store", () => {
	test("a watched video credits its diamonds once", () => {
		useGameStore.setState({ logistics: { ...store().logistics, premiumCurrency: 0 } });
		expect(store().claimRewardedAd("ad-1")).toBe(3);
		expect(store().logistics.premiumCurrency).toBe(3);
		expect(store().claimRewardedAd("ad-1")).toBe(null);
		// Too soon for another.
		expect(store().claimRewardedAd("ad-2")).toBe(null);
		expect(store().rewardedAds.total).toBe(1);
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
