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
		expect(adsHost.takePendingAd("made-up")).toBe(false);
		expect(adsHost.takePendingAd(request.message.id)).toBe(true);
		expect(adsHost.takePendingAd(request.message.id)).toBe(false);
	});

	test("a video closed early or failed frees the button and pays nothing", () => {
		const request = adsHost.requestRewardedAd(store());
		adsHost.applyAdsMessage({ kind: "ad", event: "closed", id: request.message.id });
		expect(adsHost.adsStore.pendingId).toBe("");
		expect(adCard().lines[0]).toContain("sem prêmio");
		expect(adCard().buttons[0].enabled).toBe(true);
	});

	test("the card shows today's count, the reward and the wait", () => {
		useGameStore.setState({ logistics: { ...store().logistics, premiumCurrency: 0 } });
		expect(adCard().buttons[0].label).toBe("Assistir · +3");
		expect(adCard().subtitle).toContain("hoje: 0 de 5");
		const request = adsHost.requestRewardedAd(store());
		adsHost.takePendingAd(request.message.id);
		adsHost.noteAdReward(store().claimRewardedAd(request.message.id));
		expect(adCard().lines[0]).toBe("Você ganhou +3 diamantes!");
		expect(adCard().subtitle).toContain("hoje: 1 de 5");
		expect(adCard().buttons[0].label).toMatch(/^Próximo em \d:\d\d$/);
		expect(adCard().buttons[0].enabled).toBe(false);
	});

	test("no video available: the button is off and says why", () => {
		adsHost.applyAdsMessage({ kind: "ad", status: "unavailable" });
		expect(adsHost.requestRewardedAd(store())).toEqual({ ok: false, reason: "Nenhum vídeo disponível agora. Tente mais tarde." });
		expect(adCard().buttons[0].enabled).toBe(false);
	});
});
