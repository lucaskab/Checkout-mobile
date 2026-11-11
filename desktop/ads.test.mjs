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
// The diamond video's card (Lucas 10/11: the "Vídeo grátis" page has a card for diamonds and one for coins).
const adCard = () => pages(store(), "currency:diamonds").cards.find((c) => c.title === "Diamantes" && c.eyebrow === "VÍDEO GRÁTIS");
const coinCard = () => pages(store(), "video").cards.find((c) => c.title === "Moedas");
// The status line under "Hoje: x de 7 vídeos".
const status = (c) => c.lines[1];

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
		expect(status(adCard())).toContain("sem prêmio");
		expect(adCard().buttons[0].enabled).toBe(true);
	});

	test("the card shows the reward and what is left today; after 7 videos it waits for midnight", () => {
		useGameStore.setState({ logistics: { ...store().logistics, premiumCurrency: 0 } });
		expect(adCard().buttons[0].label).toBe("Assistir · +2");
		expect(adCard().lines[0]).toBe("Hoje: 0 de 7 vídeos");
		const request = adsHost.requestRewardedAd(store());
		adsHost.takePendingAd(request.message.id);
		adsHost.noteAdReward(store().claimRewardedAd(request.message.id));
		expect(status(adCard())).toBe("Você ganhou +2 diamantes!");
		expect(adCard().lines[0]).toBe("Hoje: 1 de 7 vídeos");
		expect(adCard().buttons[0].enabled).toBe(true);
		for (let i = 0; i < 6; i++) {
			const next = adsHost.requestRewardedAd(store());
			adsHost.takePendingAd(next.message.id);
			adsHost.noteAdReward(store().claimRewardedAd(next.message.id));
		}
		expect(store().logistics.premiumCurrency).toBe(14);
		expect(adCard().buttons[0].enabled).toBe(false);
		expect(adCard().subtitle).toContain("volta em");
		expect(adsHost.requestRewardedAd(store()).ok).toBe(false);
	});

	test("no video loaded (or the last load failed): the button stays on, says so, and still asks Unity", async () => {
		// Lucas 08/11: a friend on the App Store found the video button dead. It must never be switched off by the
		// ad network: Unity loads a video and opens it as soon as one arrives, or answers "failed".
		const { createDesktopView } = await import("./view.ts");
		for (const status of ["starting", "loading", "unavailable"]) {
			adsHost.resetAdsStore();
			adsHost.applyAdsMessage({ kind: "ad", status });
			expect(adCard().buttons[0].enabled).toBe(true);
			expect(createDesktopView(store(), 1, []).quickFixed[0].route).toBe("!video");
		}
		expect(status(adCard())).toBe("Sem vídeo agora, tente em instantes.");
		adsHost.applyAdsMessage({ kind: "ad", status: "loading" });
		expect(status(adCard())).toBe("Carregando o vídeo…");
		const request = adsHost.requestRewardedAd(store());
		expect(request.ok).toBe(true);
		expect(request.message.kind).toBe("ad-show");
		expect(adCard().buttons[0].enabled).toBe(false); // opening: "Aguardando…"
		// No video arrived in time: Unity says "failed", the button comes back and the page says it did not load.
		adsHost.applyAdsMessage({ kind: "ad", status: "unavailable", event: "failed", id: request.message.id });
		expect(adCard().buttons[0].enabled).toBe(true);
		expect(status(adCard())).toBe("O vídeo não carregou. Tente de novo.");
		// The placement videos too.
		expect(store().claimDailyLogin()).toBe(true);
		const gift = pages(store(), "gratis").cards.find((c) => c.title === "Presente do dia");
		expect(gift.buttons[0].action).toBe("watchRewardedAd");
		expect(gift.buttons[0].enabled).toBe(true);
	});
});

describe("ads consent (GDPR)", () => {
	test("the privacy button shows only where Google asks for it and reopens the form", () => {
		const labels = () => pages(store(), "video").cards.flatMap((c) => c.buttons.map((b) => b.action));
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
	test("the HUD: \"Grátis\" (videos) always on screen; the Bônus menu has gift and store; the free page", async () => {
		const { createDesktopView } = await import("./view.ts");
		adsHost.adsStore.status = "ready";
		const view = createDesktopView(store(), 1, []);
		// Lucas 10/11: the videos stand on the screen with the diamond, counting the 7 + 7 videos left today
		expect(view.quickFixed[0]).toMatchObject({ label: "Grátis", route: "!video", variant: "gem", badge: "14" });
		expect(view.quick.map((q) => q.icon.length > 0).every(Boolean)).toBe(true);
		expect(view.quick[0].badge).toBe("!"); // the gift can be claimed
		expect(view.quick[1].route).toBe("!currency");
		expect(view.quick.some((q) => q.action === "watchRewardedAd")).toBe(false);
		const free = pages(store(), "gratis");
		expect(free.cards.map((c) => c.title)).toContain("Presente do dia");
		expect(free.cards.map((c) => c.title)).toEqual(expect.arrayContaining(["Diamantes", "Moedas"]));
	});

	test("coin videos: the player picks coins, 7 a day apart from the diamonds, by level", () => {
		useGameStore.setState({ market: { ...store().market, level: 10 } });
		const coins = store().coins;
		const request = adsHost.requestRewardedAd(store(), Date.now(), "coins");
		expect(request.ok).toBe(true);
		expect(adsHost.takePendingAd(request.message.id)).toBe("coins");
		const got = store().claimRewardedCoinAd(request.message.id);
		expect(got).toBeGreaterThan(0);
		expect(store().coins).toBe(coins + got);
		expect(coinCard().lines[0]).toBe("Hoje: 1 de 7 vídeos");
		expect(store().rewardedAds.watched).toBe(0); // the diamond videos are untouched
		for (let i = 0; i < 6; i++) {
			const next = adsHost.requestRewardedAd(store(), Date.now(), "coins");
			adsHost.takePendingAd(next.message.id);
			store().claimRewardedCoinAd(next.message.id);
		}
		expect(adsHost.requestRewardedAd(store(), Date.now(), "coins").ok).toBe(false);
		expect(coinCard().buttons[0].enabled).toBe(false);
		expect(adsHost.requestRewardedAd(store(), Date.now(), "diamonds").ok).toBe(true);
	});
});
