/** One of the curated palettes of "Cores do mercado" (src/data/market-paint.ts). */
export type MarketPaletteDefinition = {
	id: string;
	/** Short name shown on the chip (Portuguese; translated on the way out). */
	name: string;
	/** Hex without # that takes the place of the brand navy. */
	primary: string;
	/** Hex without # that takes the place of the brand gold. */
	accent: string;
};

/** A pair of colours the player applied (curated palette id, or "custom"). */
export type MarketPaintChoice = {
	paletteId: string;
	primary: string;
	accent: string;
};

/** The market's colours in the save: the current pair and the last ones applied (newest first, at most 3). */
export type MarketPaintState = MarketPaintChoice & {
	recent: MarketPaintChoice[];
	/** How many times the player paid to repaint (statistics). */
	purchases: number;
};

export type MarketPaintCurrency = "coins" | "diamonds";

/** What Unity gets in every snapshot (paint): the current pair, the palettes, the last ones applied and the prices. */
export type MarketPaintSnapshot = {
	primary: string;
	accent: string;
	palette: string;
	coinPrice: number;
	diamondPrice: number;
	palettes: MarketPaletteDefinition[];
	recent: MarketPaletteDefinition[];
};
