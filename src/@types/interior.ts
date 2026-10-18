/**
 * One piece of furniture. Inside the market: position in the unprojected base map of the shop (it follows the
 * shop as it grows). Outside (`outside: true`): world metres on the market's city block.
 */
export type InteriorItem = {
	/** "shelf:produce", "sector:padaria", "checkout:main", "checkout:extra", "kiosk:1", "decor-7"... */
	id: string;
	/** "shelf", "sector", "checkout", "kiosk" or a decoration id from interior-decor. */
	type: string;
	x: number;
	z: number;
	/** Degrees around the vertical axis. */
	rot: number;
	/** Waiting in the build-mode inventory: decorations taken out, or shop furniture not placed yet. */
	stored?: boolean;
	/** Placed on the city block around the market instead of inside it. */
	outside?: boolean;
};

export type InteriorState = {
	/** Placed pieces, plus stored ones. Shop furniture with no entry is laid out by Unity at a free spot. */
	items: InteriorItem[];
	/** Decorations bought, by decoration id. */
	owned: Record<string, number>;
};

export type InteriorDecorDefinition = {
	id: string;
	name: string;
	description: string;
	coinPrice?: number;
	diamondPrice?: number;
	requiredLevel: number;
	/** Where it can be placed: inside the shop, on the block around it, or either. */
	zone: "inside" | "outside" | "both";
	/** A "melhoria": what it does while it stands placed (stored pieces do nothing). */
	effect?: DecorEffect;
};

/**
 * What a placed decoration does for the market (src/services/decor-effects.ts adds them up). The decoration's
 * description states the same numbers.
 */
export type DecorEffect = {
	/** Extra products each customer may put in the basket (counted once, however many are placed). */
	basketItems?: number;
	/** Customers bring this share more money to spend (0.15 = +15%; counted once). */
	budget?: number;
	/** A coin machine: each customer may stop and play (chance per placed machine, up to `maxPlaced`). */
	play?: { chance: number; coins: number; maxPlaced: number };
};
