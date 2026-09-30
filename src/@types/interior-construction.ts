/** What can be built inside the market: a new shelf, a production sector or a shop fixture
 * (second checkout, self-checkout kiosks). */
export type InteriorBuildKind = "shelf" | "sector" | "shop";

/** Paid for and under construction: it joins the market once `endsAt` has passed, or right away
 * when the player pays diamonds to speed it up. */
export type InteriorConstruction = {
	id: string;
	kind: InteriorBuildKind;
	/** Shelf id, sector id or shop item id. */
	targetId: string;
	startedAt: number;
	endsAt: number;
	/** Paid for and kept in the inventory: the builders only start once the player places it
	 * in the build mode (`startedAt`/`endsAt` are 0 meanwhile). */
	pending?: boolean;
	/** Building time once the works start (placed pieces wait in a queue for the crew). */
	durationMs?: number;
};
