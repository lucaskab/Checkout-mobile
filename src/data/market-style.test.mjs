import { afterAll, beforeEach, expect, mock, test } from "bun:test";

// "Estilo do mercado" (Lucas 08/11): floor, walls, staff uniform and the big sign — buy each item once, colours free.
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
const style = await import("./market-style.ts");
const { getMarketPaintCoinPrice } = await import("./market-paint.ts");
const { createSimulatorSnapshot } = await import("../services/simulator-snapshot.ts");
const initial = JSON.stringify(useGameStore.getState());
beforeEach(() => useGameStore.setState(JSON.parse(initial)));
afterAll(() => useGameStore.setState(JSON.parse(initial)));
const game = () => useGameStore.getState();
const choice = (patch) => JSON.stringify({ ...game().marketStyle, ...patch, sign: { ...game().marketStyle.sign, ...(patch.sign ?? {}) } });

function at(era, coins = 10_000_000) {
	game().setMarketLevel(50);
	game().devSetMarketEra(era);
	useGameStore.setState({ coins });
}

test("every kind has exactly one free item and ids are unique", () => {
	for (const kind of ["floor", "wall", "uniform", "font", "look", "effect"]) {
		const items = style.marketStyleItems.filter((entry) => entry.kind === kind);
		expect(items.filter((entry) => entry.free).length).toBe(1);
		expect(new Set(items.map((entry) => entry.id)).size).toBe(items.length);
		expect(items.length).toBeGreaterThanOrEqual(7);
	}
});

test("new saves wear the classic look", () => {
	const state = game().marketStyle;
	expect(state.floor).toBe("classico");
	expect(state.wall).toBe("classico");
	expect(state.uniform).toBe("classico");
	expect(state.sign).toEqual(style.createMarketSignChoice());
	expect(state.owned).toEqual([]);
});

test("old saves and broken values normalize to something wearable", () => {
	expect(style.normalizeMarketStyleState(undefined)).toEqual(style.createMarketStyleState());
	const broken = style.normalizeMarketStyleState({ floor: "taco", wall: "nope", owned: ["floor:xadrez", "wall:classico", 3], sign: { look: "neon" } });
	// taco is not owned → classic; the free wall never sits in "owned"
	expect(broken.floor).toBe("classico");
	expect(broken.owned).toEqual(["floor:xadrez"]);
	expect(broken.sign.look).toBe("classico");
});

test("floor and walls need an inside; nothing to buy at the sidewalk table", () => {
	at("mesinha");
	expect(game().applyMarketStyle(choice({ floor: "taco" }))).toBe(false);
	at("spati");
	expect(game().applyMarketStyle(choice({ floor: "taco" }))).toBe(true);
	expect(game().marketStyle.floor).toBe("taco");
});

test("buying charges the new items together, then re-wearing is free", () => {
	at("mercadinho", 1_000_000);
	const base = getMarketPaintCoinPrice("mercadinho");
	const draft = choice({ floor: "madeira-clara", sign: { look: "neon", effect: "piscar", main: "ff4fd8" } });
	const quote = style.getMarketStylePrice(game().marketStyle, style.normalizeMarketStyleChoice(JSON.parse(draft)), "mercadinho");
	expect(quote.items.map((entry) => entry.id).sort()).toEqual(["madeira-clara", "neon", "piscar"]);
	expect(quote.coins).toBeGreaterThan(base * 2);
	expect(game().applyMarketStyle(draft)).toBe(true);
	expect(game().coins).toBe(1_000_000 - quote.coins);
	expect(game().marketStyle.sign.main).toBe("FF4FD8");
	expect(game().marketStyle.owned.length).toBe(3);
	// back to classic and to the bought items again: no charge
	expect(game().applyMarketStyle(choice({ floor: "classico", sign: { look: "classico", effect: "fixo" } }))).toBe(true);
	const coins = game().coins;
	expect(game().applyMarketStyle(draft)).toBe(true);
	expect(game().coins).toBe(coins);
	// the same look again is a no-op
	expect(game().applyMarketStyle(draft)).toBe(false);
});

test("colours are free once the item is owned", () => {
	at("mercadinho", 1_000_000);
	expect(game().applyMarketStyle(choice({ wall: "tinta", wallColor: "C0392B" }))).toBe(true);
	const coins = game().coins;
	expect(game().applyMarketStyle(choice({ wallColor: "1F7A4D" }))).toBe(true);
	expect(game().coins).toBe(coins);
	expect(game().marketStyle.wallColor).toBe("1F7A4D");
});

test("preset uniforms keep their own colours, free colours keep the player's", () => {
	at("quitanda");
	expect(game().applyMarketStyle(choice({ uniform: "vermelho", uniformMain: "000000" }))).toBe(true);
	expect(game().marketStyle.uniformMain).toBe("C0392B");
	expect(game().applyMarketStyle(choice({ uniform: "personalizado", uniformMain: "123456", uniformDetail: "abcdef" }))).toBe(true);
	expect(game().marketStyle.uniformMain).toBe("123456");
	expect(game().marketStyle.uniformDetail).toBe("ABCDEF");
});

test("not enough coins refuses; diamonds pay the diamond total", () => {
	at("mercadinho", 10);
	const draft = choice({ floor: "taco" });
	expect(game().applyMarketStyle(draft)).toBe(false);
	useGameStore.setState({ logistics: { ...game().logistics, premiumCurrency: 100 } });
	expect(game().applyMarketStyle(draft, "diamonds")).toBe(true);
	expect(game().logistics.premiumCurrency).toBe(80);
	expect(game().coins).toBe(10);
});

test("garbage JSON is refused", () => {
	at("mercadinho");
	expect(game().applyMarketStyle("{not json")).toBe(false);
});

test("the snapshot carries the catalog, prices and where it is unlocked", () => {
	at("spati");
	const snap = createSimulatorSnapshot(game(), "qa", 1).style;
	expect(snap.insideUnlocked).toBe(true);
	expect(snap.signUnlocked).toBe(false);
	expect(snap.items.find((entry) => entry.id === "taco").coinPrice).toBe(getMarketPaintCoinPrice("spati"));
	expect(snap.palettes.length).toBeGreaterThan(3);
	at("supermercado");
	expect(createSimulatorSnapshot(game(), "qa", 1).style.signUnlocked).toBe(true);
});
