/** "Estilo do mercado" (Lucas 08/11): floor, walls, staff uniform and the big sign on the back of the market. */

export type MarketStyleKind = "floor" | "wall" | "uniform" | "font" | "look" | "effect";

/** One thing the player can buy once and then use as often as they like (src/data/market-style.ts). */
export type MarketStyleItem = {
	id: string;
	kind: MarketStyleKind;
	/** Shown on the card (Portuguese; translated on the way out). */
	name: string;
	/** Free for everyone (the look the market had before the feature, and "Fixo"). */
	free?: boolean;
	/** The player picks a colour for it (painted walls, tiles with a glaze...). */
	tintable?: boolean;
	/** The colour it starts with when tintable (hex without #). */
	color?: string;
	/** A uniform's two colours: the main garment and the details (hex without #). */
	main?: string;
	detail?: string;
	/** Price in coins = the stage's paint price × this. */
	coinFactor: number;
	diamondPrice: number;
	/** A short hint under the name ("Brilha no escuro"...). */
	note?: string;
};

/** Colours that go together for the letters of "Letras coloridas". */
export type MarketSignPalette = { id: string; name: string; colors: string[] };

export type MarketSignChoice = {
	font: string;
	look: string;
	effect: string;
	/** Main colour of the letters (hex, "" = the look's own). */
	main: string;
	/** Second colour (gradient end, outline, 3D side, the other colour of "Alternar cores"). */
	second: string;
	/** Palette of "Letras coloridas". */
	palette: string;
	/** 0 slow, 1 normal, 2 fast. */
	speed: number;
};

/** What the market wears now (every id is one the player owns or a free one). */
export type MarketStyleChoice = {
	floor: string;
	/** "" = the floor's own colour. */
	floorColor: string;
	wall: string;
	wallColor: string;
	uniform: string;
	uniformMain: string;
	uniformDetail: string;
	sign: MarketSignChoice;
};

export type MarketStyleState = MarketStyleChoice & {
	/** "kind:id" of every item bought (free ones are never listed). */
	owned: string[];
	/** How many times the player paid (statistics). */
	purchases: number;
};

export type MarketStyleCurrency = "coins" | "diamonds";

/** What Unity gets in every snapshot (style). */
export type MarketStyleSnapshot = MarketStyleChoice & {
	owned: string[];
	/** Floor and walls can be changed (the shop has an inside). */
	insideUnlocked: boolean;
	/** The big sign exists (the market building). */
	signUnlocked: boolean;
	/** Coins of an item with coinFactor 1 at the current stage (the panel multiplies). */
	coinBase: number;
	items: (MarketStyleItem & { coinPrice: number })[];
	palettes: MarketSignPalette[];
	swatches: string[];
};
