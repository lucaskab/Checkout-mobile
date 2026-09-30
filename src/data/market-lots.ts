import type { MarketEraId } from "@/@types/economy";

// The market's block, split in equal lots: columns A–D (west → east) and rows 1–5 (from the avenue
// to the back). The first eras stand on the sidewalk in front of B1/C1; from the mercadinho on the
// market takes lots one next to the other. Rows 4 and 5 are the free square (praça).
// World metres, same frame as Unity (CheckoutStreetLayout: block x ±17.25, from z −8.5 at the avenue).

export const LOT_COLUMNS = ["A", "B", "C", "D"] as const;
export const LOT_ROWS = [1, 2, 3, 4, 5] as const;
export const LOT_GRID = {
	x0: -17.25,
	z0: -8.5,
	width: 34.5,
	depth: 53,
	columns: LOT_COLUMNS.length,
	rows: LOT_ROWS.length,
} as const;
export const LOT_WIDTH = LOT_GRID.width / LOT_GRID.columns;
export const LOT_DEPTH = LOT_GRID.depth / LOT_GRID.rows;

const row = (r: number) => LOT_COLUMNS.map((c) => `${c}${r}`);

/** Free public square: never bought, decorated later. */
export const PLAZA_LOTS = [...row(4), ...row(5)];

/** Lots the market occupies in each era (eras 0–4 stand on the sidewalk and in front of B1/C1). */
export const ERA_LOTS: Record<MarketEraId, string[]> = {
	mesinha: [],
	banca: [],
	tenda: [],
	conteiner: [],
	spati: [],
	mercadinho: ["B1", "C1", "B2", "C2"],
	supermercado: [...row(1), ...row(2)],
	hipermercado: [...row(1), ...row(2), ...row(3)],
	rede: [...row(1), ...row(2), ...row(3)],
};

/** Centre of a lot in world metres (x, z). */
export function getLotCentre(id: string) {
	const column = LOT_COLUMNS.indexOf(id[0] as (typeof LOT_COLUMNS)[number]);
	const r = Number(id.slice(1)) - 1;
	return {
		x: LOT_GRID.x0 + (column + 0.5) * LOT_WIDTH,
		z: LOT_GRID.z0 + (r + 0.5) * LOT_DEPTH,
	};
}
