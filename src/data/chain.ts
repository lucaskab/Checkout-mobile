import type { ChainBranchId, ChainClientId, ChainEmblemId, FleetTruckKind } from "@/@types/chain";

// Numbers of the Rede de supermercados (src/services/chain.ts has the rules). The chain opens when the "rede"
// expansion's works end; saves already in the rede get it the next time the game opens.

export const CHAIN_ERA_ID = "rede" as const;

/** Name rules: what the naming card accepts (letters of any language, digits, spaces and a few signs). */
export const CHAIN_NAME_MIN = 2;
export const CHAIN_NAME_MAX = 18;
/** Diamonds to rename the chain (the first naming is free). */
export const CHAIN_RENAME_DIAMONDS = 50;

export const chainEmblems: ChainEmblemId[] = [
	"cesta",
	"carrinho",
	"folha",
	"estrela",
	"coroa",
	"sol",
	"coracao",
	"sacola",
	"maca",
	"trigo",
	"toldo",
	"diamante",
];

// ------------------------------------------------------------------------------------------------ fleet
/** The distribution centre starts with one dry truck and one refrigerated truck. */
export const FLEET_START: FleetTruckKind[] = ["seco", "refrigerado"];
/** Price of each extra truck, in order (the list's length is how many more can be bought). */
export const FLEET_TRUCK_PRICES: Record<FleetTruckKind, number[]> = {
	seco: [180_000, 320_000, 520_000],
	refrigerado: [350_000, 600_000],
};
/** Engine upgrades: price of each level and the trip time multiplier at each level (0..3). */
export const FLEET_SPEED_PRICES = [250_000, 500_000, 900_000];
export const FLEET_SPEED_FACTORS = [1, 0.85, 0.72, 0.6];

/** Restocking through the chain's own distribution centre: cheaper (wholesale) and faster than a supplier. */
export const DC_PRICE_FACTOR = 0.9;
export const DC_TIME_FACTOR = 0.5;
export const DC_MAX_BOXES = 30;
/** A restock truck drives back to the centre in this share of its trip after unloading. */
export const FLEET_RETURN_SHARE = 0.5;
/** Categories that need a refrigerated truck. */
export const COLD_CATEGORIES = ["carnes", "peixes", "laticinios", "queijos", "frios", "congelados", "sorvetes"];

/** Automatic restock: checked at most this often; it never spends the coins below the reserve. */
export const AUTO_ORDER_EVERY_MS = 60_000;
export const AUTO_ORDER_RESERVE = 50_000;

// ------------------------------------------------------------------------------------------------ contracts
export type ChainClientDefinition = { id: ChainClientId; name: string; categories: string[] };

export const chainClients: ChainClientDefinition[] = [
	{ id: "restaurante", name: "Restaurante", categories: ["carnes", "hortifruti", "alcoolicos", "massas"] },
	{ id: "hotel", name: "Hotel", categories: ["padaria", "laticinios", "bebidas", "queijos"] },
	{ id: "escola", name: "Escola", categories: ["padaria", "bolachas", "bebidas", "hortifruti"] },
	{ id: "hospital", name: "Hospital", categories: ["laticinios", "hortifruti", "higiene", "aguas"] },
	{ id: "lanchonete", name: "Lanchonete", categories: ["padaria", "refrigerantes", "frios", "congelados"] },
	{ id: "buffet", name: "Buffet de festas", categories: ["doces", "refrigerantes", "sorvetes", "padaria"] },
];

export const CONTRACT_OFFERS = 3;
/** New offers come in every half hour; an offer nobody takes leaves after two hours. */
export const CONTRACT_REFRESH_MS = 30 * 60_000;
export const CONTRACT_LIFETIME_MS = 2 * 60 * 60_000;
/** Trip to the client (before the engine upgrades). */
export const CONTRACT_TRIP_MS: [number, number] = [8 * 60_000, 16 * 60_000];
/** The client pays this much over the shelf price of what it takes. */
export const CONTRACT_PREMIUM = 2;
/** One offer in this many also gives diamonds. */
export const CONTRACT_DIAMOND_EVERY = 6;

// ------------------------------------------------------------------------------------------------ branches
export type ChainBranchDefinition = {
	id: ChainBranchId;
	name: string;
	/** What the neighbourhood buys most: a cargo with these on it fills the shelves up to the top. */
	favorites: string[];
	price: number;
	buildMs: number;
	/** Income multiplier of the neighbourhood. */
	income: number;
};

export const chainBranches: ChainBranchDefinition[] = [
	{ id: "centro", name: "Centro", favorites: ["bebidas", "padaria", "mercearia", "refrigerantes"], price: 450_000, buildMs: 3 * 3_600_000, income: 1 },
	{ id: "praia", name: "Praia", favorites: ["sorvetes", "aguas", "bebidas", "peixes"], price: 600_000, buildMs: 4 * 3_600_000, income: 1.1 },
	{ id: "universitario", name: "Universitário", favorites: ["mercearia", "congelados", "massas", "energeticos"], price: 750_000, buildMs: 5 * 3_600_000, income: 1 },
	{ id: "vila", name: "Vila Residencial", favorites: ["hortifruti", "laticinios", "padaria", "limpeza"], price: 900_000, buildMs: 5 * 3_600_000, income: 1.15 },
	{ id: "nobre", name: "Bairro Nobre", favorites: ["alcoolicos", "queijos", "gourmet", "carnes"], price: 1_100_000, buildMs: 6 * 3_600_000, income: 1.4 },
];

/** Upgrading a branch: price share of its purchase price and works time, for levels 2 and 3. */
export const BRANCH_UPGRADES: { priceShare: number; buildMs: number }[] = [
	{ priceShare: 0.8, buildMs: 4 * 3_600_000 },
	{ priceShare: 1.4, buildMs: 8 * 3_600_000 },
];
/** Coins per minute of a level-1 branch with full shelves; levels 2 and 3 multiply it. */
export const BRANCH_INCOME_PER_MIN = 260;
export const BRANCH_LEVEL_INCOME = [0, 1, 1.9, 3.2];
/** Full shelves run empty in this many hours (the income follows the shelves). */
export const BRANCH_SUPPLY_HOURS = 12;
/** Coins wait to be collected for at most this many hours of income. */
export const BRANCH_PENDING_HOURS = 8;
/** A cargo carries this many units per branch level, taken from the market's stockroom. */
export const BRANCH_CARGO_UNITS = 40;
/** With at least this share of favourites the shelves go to the top; otherwise to BRANCH_PARTIAL_SUPPLY. */
export const BRANCH_FAVORITE_SHARE = 0.5;
export const BRANCH_PARTIAL_SUPPLY = 0.75;
export const BRANCH_TRIP_MS = 10 * 60_000;

// ------------------------------------------------------------------------------------------------ private label
/** The chain's own products ("marca própria"): which everyday product each one stands in for. */
export const privateLabelProducts: { id: number; baseId: number }[] = [
	{ id: 172, baseId: 51 },
	{ id: 173, baseId: 52 },
	{ id: 174, baseId: 55 },
	{ id: 175, baseId: 5 },
	{ id: 176, baseId: 25 },
	{ id: 177, baseId: 35 },
	{ id: 178, baseId: 58 },
	{ id: 179, baseId: 26 },
];
