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
const { currencyPacks, getCurrencyPack } = await import("../src/data/currency-packs.ts");

const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => {
	useGameStore.setState(JSON.parse(initial));
	iap.resetIapStore();
});
afterAll(() => {
	useGameStore.setState(JSON.parse(initial));
	iap.resetIapStore();
});
const store = () => useGameStore.getState();
const buttons = (page) => page.cards.flatMap((card) => card.buttons);

describe("the host side of a purchase", () => {
	test("Unity gets the whole catalog to ask the store for", () => {
		const message = iap.createIapCatalogMessage();
		expect(message.kind).toBe("iap-catalog");
		expect(message.products.map((p) => p.productId)).toEqual(currencyPacks.map((p) => p.productId));
	});

	test("'Comprar' asks Unity to buy only when the store is ready", () => {
		expect(iap.requestPackPurchase(store(), "diamonds-pouch").ok).toBe(false);
		iap.applyIapMessage({ kind: "iap", status: "ready", productIds: [], prices: [] });
		const request = iap.requestPackPurchase(store(), "diamonds-pouch");
		expect(request).toEqual({
			ok: true,
			message: { kind: "purchase", productId: "com.checkout.currency.diamonds.pouch", packId: "diamonds-pouch" },
		});
		// One purchase at a time.
		expect(iap.requestPackPurchase(store(), "diamonds-chest").ok).toBe(false);
		iap.applyIapMessage({ kind: "iap", event: "cancelled", productId: "com.checkout.currency.diamonds.pouch" });
		expect(iap.requestPackPurchase(store(), "diamonds-chest").ok).toBe(true);
	});

	test("unknown packs and a bought welcome combo are refused", () => {
		iap.applyIapMessage({ kind: "iap", status: "ready" });
		expect(iap.requestPackPurchase(store(), "free-money").ok).toBe(false);
		store().grantCurrencyPack("bundle-starter", "tx-1");
		expect(iap.requestPackPurchase(store(), "bundle-starter")).toEqual({ ok: false, reason: "Esta oferta já foi comprada." });
	});

	test("the store's local prices replace the catalog's, and event messages keep them", () => {
		const id = getCurrencyPack("diamonds-pouch").productId;
		expect(iap.getPackPrice(id)).toBe("€ 4,99");
		iap.applyIapMessage({ kind: "iap", status: "ready", productIds: [id], prices: ["R$ 24,90"] });
		expect(iap.getPackPrice(id)).toBe("R$ 24,90");
		// Unity's JsonUtility writes empty lists on event messages.
		iap.applyIapMessage({ kind: "iap", status: "", event: "failed", productId: id, productIds: [], prices: [] });
		expect(iap.getPackPrice(id)).toBe("R$ 24,90");
		expect(iap.iapStore.status).toBe("ready");
		expect(iap.iapStore.notice?.ok).toBe(false);
	});

	test("a credited purchase leaves a thank-you notice", () => {
		iap.iapStore.busyProductId = "x";
		iap.noteGrantedPack({ coins: 0, diamonds: 220 });
		expect(iap.iapStore.busyProductId).toBe("");
		expect(iap.iapStore.notice?.text).toContain("+220 diamantes");
	});
});

describe("the diamond store page", () => {
	test("each pack has a Comprar button that buys it (no free credit outside dev)", () => {
		const page = pages(store(), "currency:diamonds");
		const all = buttons(page);
		expect(all.some((b) => b.action === "grantCurrencyPurchase")).toBe(false);
		const buy = all.filter((b) => b.action === "buyCurrencyPack");
		expect(buy.length).toBe(currencyPacks.filter((p) => p.category === "diamonds").length);
		expect(JSON.parse(buy[0].args)[0]).toBe("diamonds-handful");
	});

	test("opened for a shortfall it says how many are missing and recommends the pack that covers it", () => {
		const page = pages(store(), "currency:diamonds:150");
		expect(page.cards.some((c) => c.title === "Faltam 150 diamantes")).toBe(true);
		const recommended = page.cards.find((c) => c.subtitle === "Recomendado para o que falta");
		expect(recommended?.title).toBe(getCurrencyPack("diamonds-pouch").name);
	});

	test("coins on the page follow the player's expansion and the bought welcome combo is gone", () => {
		useGameStore.setState({ era: { ...store().era, id: "rede" } });
		store().grantCurrencyPack("bundle-starter", "tx-9");
		const page = pages(store(), "currency:all");
		expect(page.cards.some((c) => c.title === getCurrencyPack("bundle-starter").name)).toBe(false);
		const sack = page.cards.find((c) => c.title === getCurrencyPack("coins-sack").name);
		expect(sack.lines[0]).toMatch(/milh|\d{3}\.\d{3}/);
	});
});

describe("diamond buttons stay pressable when short (the store opens instead)", () => {
	test("a lot being cleared offers Acelerar even with no diamonds", () => {
		useGameStore.setState({
			logistics: { ...store().logistics, premiumCurrency: 0 },
			lots: { owned: ["A1"], cleared: [], clearing: { lotId: "A1", startedAt: Date.now(), endsAt: Date.now() + 3_600_000 } },
		});
		const page = pages(store(), "loja:terrenos");
		const speedUp = buttons(page).find((b) => b.action === "finishLotClearingNow");
		expect(speedUp?.enabled).toBe(true);
		expect(speedUp?.label).toBe("Acelerar · 10");
	});
});
