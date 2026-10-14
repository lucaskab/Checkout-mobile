import { plugin } from "bun";
import { afterAll, beforeEach, describe, expect, mock, test } from "bun:test";

// The pages import game icons (require("…png")): as on desktop, the path itself is the icon id. Bun hands require()
// the module namespace, so it also exports toString (the pages turn the icon into a string).
plugin({
	name: "png-as-id",
	setup(build) {
		build.onLoad({ filter: /\.png$/ }, (args) => ({
			contents: `const path = ${JSON.stringify(args.path)}; export default path; export const toString = () => path;`,
			loader: "js",
		}));
	},
});

// The diamond store as the Unity HUD shows it (desktop/pages/progress.ts currency) and the host side of a real-money
// purchase (desktop/iap.ts): Unity buys through Unity IAP, the host asks for it and credits it.
globalThis.__DEV__ = false; // what the testers and the iPhone run
const memory = new Map();
mock.module("@/storage/mmkv", () => ({
	mmkvStorage: {
		getItem: (key) => memory.get(key) ?? null,
		setItem: (key, value) => memory.set(key, value),
		removeItem: (key) => memory.delete(key),
	},
}));
const { useGameStore } = await import("../src/stores/game-store.ts");
const { pages } = await import("./pages/index.ts");
const iap = await import("./iap.ts");
const adsHost = await import("./ads.ts");
const currencyPacksModule = await import("../src/data/currency-packs.ts");
const { currencyPacks, getCurrencyPack } = currencyPacksModule;

const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => {
	useGameStore.setState(JSON.parse(initial));
	adsHost.resetAdsStore();
});
afterAll(() => {
	useGameStore.setState(JSON.parse(initial));
	adsHost.resetAdsStore();
});
const store = () => useGameStore.getState();
const adCard = () => pages(store(), "currency:diamonds").cards.find((c) => c.title === "Diamantes grátis");

describe("rewarded videos on the host", () => {
	test("only the video the game asked for pays, once", () => {
		const request = adsHost.requestRewardedAd(store());
		expect(request.ok).toBe(true);
		expect(request.message.kind).toBe("ad-show");
		// A second press while it opens does not ask for another.
		expect(adsHost.requestRewardedAd(store()).ok).toBe(false);
		expect(adsHost.takePendingAd("made-up")).toBe(null);
		expect(adsHost.takePendingAd(request.message.id)).toBe("diamonds");
		expect(adsHost.takePendingAd(request.message.id)).toBe(null);
	});

	test("a video closed early or failed frees the button and pays nothing", () => {
		const request = adsHost.requestRewardedAd(store());
		adsHost.applyAdsMessage({ kind: "ad", event: "closed", id: request.message.id });
		expect(adsHost.adsStore.pendingId).toBe("");
		expect(adCard().lines[0]).toContain("sem prêmio");
		expect(adCard().buttons[0].enabled).toBe(true);
	});

	test("the card shows the reward, no daily limit, and the next video is ready at once", () => {
		useGameStore.setState({ logistics: { ...store().logistics, premiumCurrency: 0 } });
		expect(adCard().buttons[0].label).toBe("Assistir · +3");
		expect(adCard().subtitle).toContain("sem limite por dia");
		const request = adsHost.requestRewardedAd(store());
		adsHost.takePendingAd(request.message.id);
		adsHost.noteAdReward(store().claimRewardedAd(request.message.id));
		expect(adCard().lines[0]).toBe("Você ganhou +3 diamantes!");
		expect(adCard().subtitle).toContain("hoje: 1");
		expect(adCard().buttons[0].label).toBe("Assistir · +3");
		expect(adCard().buttons[0].enabled).toBe(true);
		expect(adsHost.requestRewardedAd(store()).ok).toBe(true);
	});

	test("no video available: the button is off and says why", () => {
		adsHost.applyAdsMessage({ kind: "ad", status: "unavailable" });
		expect(adsHost.requestRewardedAd(store())).toEqual({ ok: false, reason: "Nenhum vídeo disponível agora. Tente mais tarde." });
		expect(adCard().buttons[0].enabled).toBe(false);
	});
});

describe("ads consent (GDPR)", () => {
	test("the privacy button shows only where Google asks for it and reopens the form", () => {
		const labels = () => adCard().buttons.map((b) => b.action);
		expect(labels()).not.toContain("openAdPrivacy");
		expect(adsHost.requestAdPrivacy().ok).toBe(false);
		adsHost.applyAdsMessage({ kind: "ad", status: "ready", privacy: true });
		expect(labels()).toContain("openAdPrivacy");
		expect(adsHost.requestAdPrivacy()).toEqual({ ok: true, message: { kind: "ad-privacy" } });
		// Status messages without the field keep it.
		adsHost.applyAdsMessage({ kind: "ad", status: "loading" });
		expect(labels()).toContain("openAdPrivacy");
		adsHost.applyAdsMessage({ kind: "ad", status: "ready", privacy: false });
		expect(labels()).not.toContain("openAdPrivacy");
	});
});

describe("placement videos (consolation, daily gift)", () => {
	test("a missed contract's video pays its consolation once, without using the diamond videos", () => {
		const day = store().day;
		const contract = { id: "c", kind: "revenue", difficulty: 2, icon: "coin", title: "C", description: "", target: 100, reward: { coins: 200, diamonds: 0, experience: 40 } };
		useGameStore.setState({
			day: { ...day, phase: "results", result: { contract, contractCompleted: false, contractProgress: 0.8, total: { coins: 50, diamonds: 0, experience: 10 }, dayNumber: day.dayNumber, grade: "C", score: 50, highlights: [], stats: day.stats, averageSatisfaction: 70, bonus: { coins: 50, diamonds: 0, experience: 10 }, closedAt: 0, durationMs: 0 } },
		});
		const coins = store().coins;
		const request = adsHost.requestRewardedAd(store(), Date.now(), "consolation");
		expect(request.ok).toBe(true);
		expect(adsHost.takePendingAd(request.message.id)).toBe("consolation");
		const prize = store().claimContractConsolation(request.message.id);
		expect(prize.coins).toBeGreaterThanOrEqual(100);
		expect(store().coins).toBe(coins + prize.coins);
		expect(store().day.result.consolation.label).toBe(prize.label);
		expect(store().claimContractConsolation("other")).toBe(null);
		expect(adsHost.requestRewardedAd(store(), Date.now(), "consolation").ok).toBe(false);
		expect(store().rewardedAds.watched).toBe(0); // the five diamond videos are untouched
		const result = pages(store(), "day-result").cards.find((c) => c.title === "Prêmio de consolação");
		expect(result).toBeTruthy();
	});
	test("the daily gift can be doubled with a video once, after claiming it", () => {
		expect(adsHost.requestRewardedAd(store(), Date.now(), "gift").ok).toBe(false);
		expect(store().claimDailyLogin()).toBe(true);
		const coins = store().coins;
		const request = adsHost.requestRewardedAd(store(), Date.now(), "gift");
		expect(request.ok).toBe(true);
		adsHost.takePendingAd(request.message.id);
		const gift = store().claimDailyLoginBonus(request.message.id);
		expect(gift.coins).toBeGreaterThan(0);
		expect(store().coins).toBe(coins + gift.coins);
		expect(adsHost.requestRewardedAd(store(), Date.now(), "gift").ok).toBe(false);
		expect(store().claimDailyLoginBonus("again")).toBe(null);
	});
	test("the HUD's side buttons: gift, video, store; the free page", async () => {
		const { createDesktopView } = await import("./view.ts");
		adsHost.adsStore.status = "ready";
		const quick = createDesktopView(store(), 1, []).quick;
		expect(quick.map((q) => q.icon.length > 0)).toEqual([true, true, true]);
		expect(quick[0].badge).toBe("!"); // the gift can be claimed
		expect(quick[1].action).toBe("watchRewardedAd"); // a video plays right away
		expect(quick[2].route).toBe("!currency");
		const free = pages(store(), "gratis");
		expect(free.cards.map((c) => c.title)).toContain("Presente do dia");
		expect(free.cards.map((c) => c.title)).toContain("Diamantes grátis");
	});
});
