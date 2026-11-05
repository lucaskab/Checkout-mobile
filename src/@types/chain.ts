// Rede de supermercados (the last expansion): the chain's brand, its distribution centre with the player's own
// truck fleet, the city's delivery contracts and the branch stores on the city map. Rules in src/services/chain.ts,
// numbers in src/data/chain.ts.

export type ChainEmblemId =
	| "cesta"
	| "carrinho"
	| "folha"
	| "estrela"
	| "coroa"
	| "sol"
	| "coracao"
	| "sacola"
	| "maca"
	| "trigo"
	| "toldo"
	| "diamante";

export type ChainBrand = {
	/** The chain's name, as the player typed it (trimmed). Empty until the chain is named. */
	name: string;
	emblem: ChainEmblemId;
	/** When the player first named the chain (null = not yet: the naming card is still due). */
	namedAt: number | null;
	/** How many times it was renamed after the first (free) naming. */
	renames: number;
};

export type FleetTruckKind = "seco" | "refrigerado";

/** What a fleet truck is doing: bringing stock to the market, a city contract or a branch's cargo. */
export type FleetJobKind = "abastecer" | "contrato" | "filial";

export type FleetJob = {
	kind: FleetJobKind;
	/** The supplier order id (abastecer), the contract id or the branch id. */
	refId: string;
	departAt: number;
	/** When it reaches the destination (the market's dock, the client or the branch). */
	arriveAt: number;
	/** When it is back at the distribution centre and free again. */
	returnAt: number;
};

export type FleetTruck = {
	id: string;
	kind: FleetTruckKind;
	job: FleetJob | null;
	/** Trips done (statistics, the card shows it). */
	trips: number;
};

export type ChainFleet = {
	trucks: FleetTruck[];
	/** Engine upgrades 0..3: every level makes the trips shorter. */
	speedLevel: number;
};

export type ChainClientId = "restaurante" | "hotel" | "escola" | "hospital" | "lanchonete" | "buffet";

export type ChainContractLine = { productId: number; units: number };

export type ChainContract = {
	id: string;
	client: ChainClientId;
	lines: ChainContractLine[];
	/** Needs a refrigerated truck (cold products on it). */
	cold: boolean;
	reward: number;
	xp: number;
	/** Diamonds on top (rare offers). */
	diamonds: number;
	tripMs: number;
	/** The offer leaves the board at this time if nobody took it. */
	expiresAt: number;
	/** Set when a truck took it; the reward is paid when the truck reaches the client. */
	acceptedAt: number | null;
	truckId: string | null;
};

export type ChainContracts = {
	offers: ChainContract[];
	/** Next time new offers come in. */
	refreshAt: number;
	completed: number;
	earned: number;
	/** Running counter for ids and the offers' dice. */
	serial: number;
};

export type ChainBranchId = "centro" | "praia" | "universitario" | "nobre" | "vila";

export type ChainBranch = {
	id: ChainBranchId;
	/** 0 = not bought; 1..3 = the store's level. */
	level: number;
	/** Works of the purchase or of an upgrade: the level it becomes and when. */
	works: { level: number; endsAt: number } | null;
	/** Shelves of the branch, 0..1: 1 right after a cargo arrives, falls to 0 in BRANCH_SUPPLY_HOURS. */
	supply: number;
	/** When supply was last brought up to date. */
	supplyAt: number;
	/** Coins earned and not collected yet (capped, see BRANCH_PENDING_HOURS). */
	pending: number;
	/** A cargo truck on its way (its arrival refills the shelves). */
	cargo: { truckId: string; arriveAt: number; supply: number } | null;
	earned: number;
};

export type ChainState = {
	brand: ChainBrand;
	fleet: ChainFleet;
	autoOrder: { enabled: boolean; lastAt: number };
	contracts: ChainContracts;
	branches: Record<ChainBranchId, ChainBranch>;
};

/** What Unity draws in the world (and the HUD reads): the brand and where every fleet truck is. */
export type ChainSnapshot = {
	unlocked: boolean;
	named: boolean;
	/** The chain's name (not translated). */
	brand: string;
	emblem: ChainEmblemId;
	trucks: { id: string; kind: FleetTruckKind; job: FleetJobKind | null; phase: "patio" | "indo" | "voltando"; departAt: number; arriveAt: number; returnAt: number }[];
	branches: { id: ChainBranchId; level: number; building: boolean }[];
};
