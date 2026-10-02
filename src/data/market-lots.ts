import type { MarketEraId } from "@/@types/economy";

// The market's block and its lots. World metres, same frame as Unity (CheckoutStreetLayout: block x ±17.25,
// from z −8.5 at the avenue to z 44.5 at the back). Like the land expansions of Township, Hay Day or Forge of
// Empires the whole block is one grid of equal lots (3 columns × 4 rows of 11.5 × 13.25 m): A is the column on
// the left (west, by the roundabout), B the middle, C the right; row 1 is on the avenue, row 4 at the back.
// The player starts on the sidewalk in front of A1 (the mesinha), buys A1 for the tenda and the little shops,
// B1 for the minimercado and the mercadinho (A1 + B1), then the supermarket takes the first two rows of A and B
// plus C1 for its parking lot and B3 for its depot, and the hypermarket the whole front (A1–C2) with the big
// warehouse, the loading yard and the parking lot on rows 3 and 4. Every lot has a different old building on it
// that has to be cleared after buying (src/services/market-lots.ts).

/** What stands on a lot before the player buys and clears it (one Blender model each: CheckoutLots/Lot_<Name>). */
export type LotRuin =
	| "casa"
	| "loja"
	| "sobrado"
	| "oficina"
	| "posto"
	| "galpao"
	| "garagem"
	| "mato"
	| "entulho"
	| "fabrica"
	| "armazem"
	| "patio"
	| "praca";

export type MarketLot = {
	id: string;
	/** Short name shown on the lot. */
	label: string;
	x0: number;
	z0: number;
	x1: number;
	z1: number;
	/** Coins to buy the lot (0 = free square, never bought). */
	price: number;
	ruin: LotRuin;
	/** Name of what has to be cleared ("Casa abandonada"). */
	ruinName: string;
};

export const LOT_GRID = {
	x0: -17.25,
	z0: -8.5,
	width: 34.5,
	depth: 53,
	columns: 3,
	rows: 4,
} as const;

const COLUMNS = ["A", "B", "C"] as const;
const LOT_W = LOT_GRID.width / LOT_GRID.columns;
const LOT_D = LOT_GRID.depth / LOT_GRID.rows;

function lot(id: string, price: number, ruin: LotRuin, ruinName: string): MarketLot {
	const column = COLUMNS.indexOf(id[0] as (typeof COLUMNS)[number]);
	const row = Number(id.slice(1)) - 1;
	const x0 = LOT_GRID.x0 + column * LOT_W;
	const z0 = LOT_GRID.z0 + row * LOT_D;
	const r = (n: number) => Math.round(n * 100) / 100;
	return { id, label: `Lote ${id}`, x0: r(x0), z0: r(z0), x1: r(x0 + LOT_W), z1: r(z0 + LOT_D), price, ruin, ruinName };
}

// Prices: A1 is the first goal of the game (the mesinha on the sidewalk saves for it), B1 comes with the
// minimercado, then the lots are part of the price of the supermercado (A2, B2, C1, B3: 165 mil) and of the
// hipermercado (the other six: 270 mil).
export const MARKET_LOTS: MarketLot[] = [
	lot("A1", 300, "casa", "Casa abandonada"),
	lot("B1", 12_000, "loja", "Loja fechada"),
	lot("A2", 30_000, "sobrado", "Sobrado abandonado"),
	lot("B2", 35_000, "oficina", "Oficina mecânica velha"),
	lot("C1", 45_000, "posto", "Posto de gasolina abandonado"),
	lot("B3", 55_000, "galpao", "Galpão velho"),
	lot("C2", 50_000, "garagem", "Garagens fechadas"),
	lot("A3", 35_000, "mato", "Terreno com mato e muro caído"),
	lot("C3", 45_000, "entulho", "Entulho"),
	lot("A4", 40_000, "armazem", "Armazém abandonado"),
	lot("B4", 45_000, "fabrica", "Fábrica velha"),
	lot("C4", 55_000, "patio", "Pátio de caminhões abandonado"),
];

/** Free public squares (none: the whole block is lots now). */
export const PLAZA_LOTS: string[] = [];

/** The first lot of the game: every other lot is bought next to land the player already has. */
export const FIRST_LOT = "A1";

/** Lot ids of older saves (before the grid) and the grid lot that took their place. */
export const OLD_LOT_IDS: Record<string, string> = { "1": "A1", "2": "C1", "3": "B2", "4": "B3", "5": "C2", "6": "A2" };

const FRONT = ["A1", "B1"];
const SUPER = ["A1", "B1", "A2", "B2", "C1", "B3"];
const ALL = MARKET_LOTS.map((item) => item.id);

/**
 * Lots the player must own (bought and cleared) to have each expansion. The mesinha stands on the sidewalk;
 * the tenda and the small shops on A1; the minimercado and the mercadinho on A1 + B1; the supermercado and
 * the hipermercado need more lots (building, parking lot, depot).
 */
export const ERA_LOTS: Record<MarketEraId, string[]> = {
	mesinha: [],
	tenda: ["A1"],
	banca: ["A1"],
	conteiner: ["A1"],
	spati: ["A1"],
	quitanda: ["A1"],
	minimercado: FRONT,
	mercadinho: FRONT,
	supermercado: SUPER,
	hipermercado: ALL,
	rede: ALL,
};

export function getMarketLot(id: string) {
	return MARKET_LOTS.find((lot) => lot.id === id) ?? null;
}

/** Centre of a lot in world metres (x, z). */
export function getLotCentre(id: string) {
	const lot = getMarketLot(id);
	if (!lot) return { x: 0, z: 0 };
	return { x: (lot.x0 + lot.x1) / 2, z: (lot.z0 + lot.z1) / 2 };
}
