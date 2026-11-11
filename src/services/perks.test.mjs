import { afterAll, beforeEach, expect, mock, test } from "bun:test";

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
const perks = await import("./perks.ts");
const login = await import("./daily-login.ts");
const { getSupplierTrucks } = await import("../data/supplier-capacity.ts");
const { getCurrencyPack, isCurrencyPackAvailable } = await import("../data/currency-packs.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const store = () => useGameStore.getState();
const HOUR = 3_600_000;
const dayKey = (offsetDays) => login.getDayKey(Date.now() - offsetDays * 24 * HOUR);

// ---------------------------------------------------------------- Pacote inicial
test("the starter pack opens after the tutorial for 48 h, once, and gives its extras", () => {
	useGameStore.setState({ onboarding: { ...store().onboarding, status: "active" } });
	expect(store().startStarterOffer()).toBe(false);
	useGameStore.setState({ onboarding: { ...store().onboarding, status: "done" } });
	const now = Date.now();
	expect(store().startStarterOffer(now)).toBe(true);
	expect(store().startStarterOffer(now + 1)).toBe(false);
	const pack = getCurrencyPack(perks.STARTER_PACK_ID);
	expect(pack.limitedTime).toBe(true);
	expect(perks.isStarterOfferOpen(store().perks, [], now + 47 * HOUR)).toBe(true);
	expect(perks.isStarterOfferOpen(store().perks, [], now + 49 * HOUR)).toBe(false);
	expect(isCurrencyPackAvailable(pack, [], false)).toBe(false);
	expect(isCurrencyPackAvailable(pack, [], true)).toBe(true);

	const before = store();
	const trucks = getSupplierTrucks(before);
	const grant = store().grantCurrencyPack(perks.STARTER_PACK_ID, "t-starter");
	expect(grant.diamonds).toBe(120);
	const after = store();
	expect(after.logistics.premiumCurrency).toBe(before.logistics.premiumCurrency + 120);
	expect(after.coins).toBe(before.coins + grant.coins);
	expect(getSupplierTrucks(after)).toBe(trucks + 1);
	expect(after.logistics.freightCoupons).toBe(before.logistics.freightCoupons + 3);
	expect(after.pet.owned).toContain("bandana_flowers");
	// Bought: closed for good.
	expect(perks.isStarterOfferOpen(after.perks, after.currencyPurchases.purchasedPackIds, now)).toBe(false);
});

// ---------------------------------------------------------------- Ganho offline
test("on the way back: 2× with a video, 3× with diamonds, and a longer time away", () => {
	const summary = { coins: 500, customers: 20, durationMs: 8 * HOUR, capped: true };
	useGameStore.setState({ offlineSummary: summary, coins: 1000, logistics: { ...store().logistics, premiumCurrency: 500 } });
	expect(store().claimOfflineAd("ad-1")).toBe(500);
	expect(store().coins).toBe(1500);
	expect(store().offlineSummary).toBeNull();
	expect(store().claimOfflineAd("ad-2")).toBeNull();

	useGameStore.setState({ offlineSummary: summary });
	const price = perks.getOfflineTriplePrice(summary.durationMs);
	expect(price).toBe(32);
	expect(store().tripleOfflineCoins()).toBe(true);
	expect(store().coins).toBe(2500);
	expect(store().logistics.premiumCurrency).toBe(500 - 32);

	expect(perks.getOfflineCapHours(store().perks)).toBe(8);
	expect(store().buyOfflineCap()).toBe(true);
	expect(perks.getOfflineCapHours(store().perks)).toBe(12);
	expect(store().buyOfflineCap()).toBe(true);
	expect(perks.getOfflineCapHours(store().perks)).toBe(24);
	expect(store().buyOfflineCap()).toBe(false);
	expect(store().logistics.premiumCurrency).toBe(500 - 32 - 40 - 100);
});

test("the time away that sells follows the bought limit", () => {
	useGameStore.setState({
		lastSessionAt: Date.now() - 20 * HOUR,
		market: { ...store().market, isOpen: true },
		perks: { ...store().perks, offlineCapLevel: 1 },
	});
	store().processSessionResume();
	const summary = store().offlineSummary;
	if (summary) {
		expect(summary.durationMs).toBe(12 * HOUR);
		expect(summary.capped).toBe(true);
	}
});

// ---------------------------------------------------------------- Recuperar a sequência
test("a streak broken by one day comes back with a video or 10 diamonds; three days cost 30", () => {
	useGameStore.setState({ dailyLogin: { lastClaimDay: dayKey(2), streak: 4 }, logistics: { ...store().logistics, premiumCurrency: 100 } });
	const offer = login.getStreakRecovery(store().dailyLogin, Date.now());
	expect(offer).toEqual({ missed: 1, streak: 4, diamonds: 10, video: true });
	expect(store().claimStreakAd("ad-s")).toBe(true);
	expect(login.getNextLoginDay(store().dailyLogin, Date.now())).toBe(5);
	expect(store().claimDailyLogin()).toBe(true);
	expect(store().dailyLogin.streak).toBe(5);

	useGameStore.setState({ dailyLogin: { lastClaimDay: dayKey(4), streak: 3 } });
	expect(login.getStreakRecovery(store().dailyLogin, Date.now())).toEqual({ missed: 3, streak: 3, diamonds: 30, video: false });
	expect(store().claimStreakAd("ad-t")).toBe(false);
	expect(store().recoverLoginStreak()).toBe(true);
	expect(store().logistics.premiumCurrency).toBe(70);
	expect(login.getNextLoginDay(store().dailyLogin, Date.now())).toBe(4);

	// Too long ago, or nothing to lose: no offer.
	expect(login.getStreakRecovery({ lastClaimDay: dayKey(5), streak: 5 }, Date.now())).toBeNull();
	expect(login.getStreakRecovery({ lastClaimDay: dayKey(2), streak: 1 }, Date.now())).toBeNull();
	expect(login.getStreakRecovery({ lastClaimDay: dayKey(1), streak: 4 }, Date.now())).toBeNull();
});
