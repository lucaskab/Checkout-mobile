import type { MarketEraId } from "@/@types/economy";
import type {
	MarketPaintChoice,
	MarketPaintSnapshot,
	MarketPaintState,
	MarketPaletteDefinition,
} from "@/@types/market-paint";
import { ERA_TURN_PROFIT } from "@/data/currency-packs";
import { roundPrice } from "@/data/economy";

// "Cores do mercado" (Lucas 30/10): the market is painted in the game's two brand colours from the sidewalk table to
// the chain — navy (with its support blue) and gold. The player can swap them for any two colours: the "cor principal"
// takes the navy's place and the "cor de destaque" the gold's. Unity paints the market (CheckoutMarketPaint.cs, the
// HUD keeps the brand) and draws the picker (CheckoutMarketPaintPanel.cs); the rules and prices live here.

/** The brand colours: the market's look before any repaint, and the free "Voltar ao clássico". */
export const CLASSIC_PALETTE_ID = "classico";
export const CLASSIC_PRIMARY = "1D2B4F";
export const CLASSIC_ACCENT = "D3A53D";

/**
 * Curated palettes, one tap each. Every main colour is dark enough for the white and cream letters the market prints
 * on it (contrast ≥ 3 with white, tested), and every accent stands apart from its main colour.
 */
export const marketPalettes: MarketPaletteDefinition[] = [
	{ id: CLASSIC_PALETTE_ID, name: "Clássico", primary: CLASSIC_PRIMARY, accent: CLASSIC_ACCENT },
	{ id: "floresta", name: "Floresta", primary: "1F4D36", accent: "E3C77A" },
	{ id: "cereja", name: "Cereja", primary: "8A1C2B", accent: "D9A93E" },
	{ id: "uva", name: "Uva", primary: "4B2A6B", accent: "C9CED6" },
	{ id: "oceano", name: "Oceano", primary: "0F6A6E", accent: "F27D5E" },
	{ id: "grafite", name: "Grafite", primary: "2E3236", accent: "BFC5CC" },
	{ id: "chocolate", name: "Chocolate", primary: "4A2C20", accent: "EAD7B0" },
	{ id: "rosa", name: "Rosa", primary: "A8436A", accent: "8FD9B6" },
	{ id: "laranja", name: "Laranja", primary: "B9561A", accent: "1D2B4F" },
	{ id: "ceu", name: "Céu", primary: "2F6FA8", accent: "F4F6F8" },
	{ id: "noite", name: "Noite", primary: "15171B", accent: "7CF26B" },
	{ id: "cafe", name: "Café", primary: "3B2418", accent: "C8894A" },
	{ id: "oliva", name: "Oliva", primary: "4F6129", accent: "F0E2B6" },
	{ id: "lavanda", name: "Lavanda", primary: "5E4F8C", accent: "F3E9C6" },
];

/** A ready-made swatch grid for "any colour" (the picker adds a hue and a brightness bar). */
export const MARKET_PAINT_SWATCHES = [
	"1D2B4F", "2F6FA8", "0F6A6E", "1E8C7A", "1F4D36", "4F6129", "7CB342", "D3A53D",
	"F2C230", "E38B2C", "B9561A", "C0392B", "8A1C2B", "A8436A", "E86A9E", "5E4F8C",
	"4B2A6B", "3B2418", "4A2C20", "8D6E63", "2E3236", "6B7280", "BFC5CC", "F4F6F8",
];

/** Diamonds to repaint (the same at every stage: 25 is a third of the smallest diamond pack). */
export const MARKET_PAINT_DIAMONDS = 25;
/**
 * Coins to repaint: about 2.5 turns of profit of the current stage (ERA_TURN_PROFIT counts 10-minute turns, the game's
 * turns are 5 minutes), so it means the same effort at the sidewalk table and at the chain.
 */
export const MARKET_PAINT_COIN_TURNS = 1.25;
export const MARKET_PAINT_MIN_COINS = 200;
/** Palettes kept in "Recentes". */
export const MARKET_PAINT_RECENT = 3;

export function getMarketPaintCoinPrice(eraId: MarketEraId | undefined) {
	const profit = ERA_TURN_PROFIT[eraId ?? "mesinha"] ?? ERA_TURN_PROFIT.mesinha;
	return roundPrice(Math.max(MARKET_PAINT_MIN_COINS, profit * MARKET_PAINT_COIN_TURNS));
}

/** "#1d2b4f" / "1D2B4F" → "1D2B4F"; anything else → null. */
export function normalizeHex(value: unknown): string | null {
	if (typeof value !== "string") return null;
	const hex = value.trim().replace(/^#/, "").toUpperCase();
	return /^[0-9A-F]{6}$/.test(hex) ? hex : null;
}

export function getMarketPalette(id: string) {
	return marketPalettes.find((palette) => palette.id === id) ?? null;
}

/** The curated palette with exactly these colours ("custom" when none). */
export function getPaletteIdFor(primary: string, accent: string) {
	return marketPalettes.find((palette) => palette.primary === primary && palette.accent === accent)?.id ?? "custom";
}

export function isClassicPaint(choice: Pick<MarketPaintChoice, "primary" | "accent">) {
	return choice.primary === CLASSIC_PRIMARY && choice.accent === CLASSIC_ACCENT;
}

export function createMarketPaintState(): MarketPaintState {
	return { paletteId: CLASSIC_PALETTE_ID, primary: CLASSIC_PRIMARY, accent: CLASSIC_ACCENT, recent: [], purchases: 0 };
}

/** Saves from before the feature (v46 and older) and anything malformed: the classic look. */
export function normalizeMarketPaintState(value: unknown): MarketPaintState {
	const state = (value ?? {}) as Partial<MarketPaintState>;
	const primary = normalizeHex(state.primary);
	const accent = normalizeHex(state.accent);
	if (!primary || !accent) return createMarketPaintState();
	const recent = (Array.isArray(state.recent) ? state.recent : [])
		.map((entry) => {
			const p = normalizeHex(entry?.primary);
			const a = normalizeHex(entry?.accent);
			return p && a ? { paletteId: getPaletteIdFor(p, a), primary: p, accent: a } : null;
		})
		.filter((entry): entry is MarketPaintChoice => entry !== null)
		.slice(0, MARKET_PAINT_RECENT);
	return {
		paletteId: getPaletteIdFor(primary, accent),
		primary,
		accent,
		recent,
		purchases: Math.max(0, Math.floor(Number(state.purchases) || 0)),
	};
}

/** The new state after applying `primary` + `accent` (the old pair goes first in "Recentes" unless it is classic). */
export function withAppliedPaint(state: MarketPaintState, primary: string, accent: string, paid: boolean): MarketPaintState {
	const before: MarketPaintChoice = { paletteId: state.paletteId, primary: state.primary, accent: state.accent };
	const next: MarketPaintChoice = { paletteId: getPaletteIdFor(primary, accent), primary, accent };
	const same = (a: MarketPaintChoice, b: MarketPaintChoice) => a.primary === b.primary && a.accent === b.accent;
	// "Recentes" = the palettes the player paid for, newest first: the new one and the ones before it.
	const recent = [next, before, ...state.recent]
		.filter((entry) => !isClassicPaint(entry))
		.filter((entry, index, list) => list.findIndex((other) => same(other, entry)) === index)
		.slice(0, MARKET_PAINT_RECENT);
	return { ...next, recent, purchases: state.purchases + (paid ? 1 : 0) };
}

/** WCAG contrast ratio of two hex colours (1–21). */
export function getContrastRatio(a: string, b: string) {
	const luminance = (hex: string) => {
		const [r, g, b2] = [0, 2, 4].map((i) => {
			const c = Number.parseInt(hex.slice(i, i + 2), 16) / 255;
			return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
		});
		return 0.2126 * r + 0.7152 * g + 0.0722 * b2;
	};
	const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
	return (hi + 0.05) / (lo + 0.05);
}

/** What Unity gets in every snapshot (paint: CheckoutMarketPaint + CheckoutMarketPaintPanel). */
export function createMarketPaintSnapshot(state: MarketPaintState | undefined, eraId: MarketEraId | undefined): MarketPaintSnapshot {
	const paint = normalizeMarketPaintState(state);
	return {
		primary: paint.primary,
		accent: paint.accent,
		palette: paint.paletteId,
		coinPrice: getMarketPaintCoinPrice(eraId),
		diamondPrice: MARKET_PAINT_DIAMONDS,
		palettes: marketPalettes,
		recent: paint.recent.map((entry) => ({
			id: entry.paletteId,
			name: getMarketPalette(entry.paletteId)?.name ?? "Sua cor",
			primary: entry.primary,
			accent: entry.accent,
		})),
	};
}
