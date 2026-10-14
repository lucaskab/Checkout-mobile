import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";

// Rewarded videos: by choice, a small reward each, as many as the player wants (Lucas 14/10: no daily limit).
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
	test("no limit: every video pays 3 diamonds, one right after the other, all day", () => {
		let state = ads.createRewardedAdsState();
		const paid = [];
		for (let i = 0; i < 20; i++) {
			const result = ads.rewardAd(state, `ad-${i}`, noon + i * 30_000);
			paid.push(result.diamonds);
			state = result.state;
		}
		expect(paid).toEqual(Array(20).fill(3));
		expect(ads.getRewardedAdOffer(state, noon + 10 * MIN)).toEqual(expect.objectContaining({ available: true, watchedToday: 20, waitMs: 0 }));
	});

	test("the same video is paid once", () => {
		const first = ads.rewardAd(undefined, "same", noon);
		expect(ads.rewardAd(first.state, "same", noon + 10 * MIN).diamonds).toBe(0);
	});

	test("one video is worth a few minutes of skipping", () => {
		expect(ads.AD_REWARD_DIAMONDS).toBeGreaterThanOrEqual(getSkipDiamondCost(10 * MIN));
	});
});

describe("store", () => {
	test("a watched video credits its diamonds once", () => {
		useGameStore.setState({ logistics: { ...store().logistics, premiumCurrency: 0 } });
		expect(store().claimRewardedAd("ad-1")).toBe(3);
		expect(store().logistics.premiumCurrency).toBe(3);
		expect(store().claimRewardedAd("ad-1")).toBe(null);
		// Another one right away pays too (no limit).
		expect(store().claimRewardedAd("ad-2")).toBe(3);
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
