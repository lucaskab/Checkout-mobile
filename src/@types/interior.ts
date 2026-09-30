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
	/** Where it can be placed: inside the shop or on the block around it. */
	zone: "inside" | "outside";
};
