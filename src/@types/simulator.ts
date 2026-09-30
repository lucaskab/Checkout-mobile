import type { GameActions, GameState } from "./game";
export type SimulatorPanel =
	| "store"
	| "storage"
	| "products"
	| "suppliers"
	| "sectors"
	| "team"
	| "shop"
	| "expansions"
	| "missions"
	| "achievements"
	| "currency";

export type SimulatorUnlock = {
	id: string;
	label: string;
	panel: SimulatorPanel;
	requiredLevel: number;
	type: "employee" | "expansion" | "product" | "sector" | "shelf" | "shop";
};
export type SimulatorAction = Exclude<
	keyof GameActions,
	| `dev${string}`
	| `process${string}`
	| "resetGame"
	| "grantCurrencyPurchase"
	| "unlockProduct"
	| "setMarketLevel"
	| "dismissOfflineSummary"
>;
export type SimulatorCommand = {
	protocol: 1;
	session: string;
	id: string;
	revision: number;
	action: SimulatorAction;
	args: unknown[];
};
export type SimulatorReceipt = {
	kind: "receipt";
	protocol: 1;
	session: string;
	id: string;
	ok: boolean;
	reason?: string;
	revision: number;
};
export type SimulatorSnapshot = {
	layout: SimulatorLayout;
	kind: "snapshot";
	protocol: 1;
	session: string;
	revision: number;
	sentAt: number;
	coins: number;
	diamonds: number;
	experience: number;
	experienceToNextLevel: number;
	level: number;
	isOpen: boolean;
	satisfaction: number;
	served: number;
	dailyRevenue: number;
	dailyGoal: number;
	dailyClaimable: boolean;
	claimableMissions: number;
	shelves: {
		id: string;
		name: string;
		productId: number;
		productName: string;
		category: string;
		stock: number;
		reserve: number;
		capacity: number;
		price: number;
		unlocked: boolean;
		building: boolean;
		requiredLevel: number;
		expiresAt: number;
	}[];
	sectors: {
		id: string;
		name: string;
		unlocked: boolean;
		building: boolean;
		requiredLevel: number;
		jobs: number;
	}[];
	employees: GameState["employees"]["employees"];
	orders: Array<
		GameState["logistics"]["orders"][number] & { productCategory: string }
	>;
	jobs: GameState["production"]["jobs"];
	customers: GameState["market"]["recentCustomers"];
	expansions: string[];
	era: {
		id: string;
		index: number;
		name: string;
		grid: { x0: number; z0: number; width: number; depth: number; columns: number; rows: number };
		lots: string[];
		nextLots: string[];
		nextName: string;
		plazaLots: string[];
		construction: {
			eraId: string;
			index: number;
			name: string;
			startedAt: number;
			endsAt: number;
			skipCost: number;
		} | null;
	};
	builds: SimulatorBuild[];
	expansionStates: {
		id: string;
		name: string;
		requiredLevel: number;
		unlocked: boolean;
		building: boolean;
	}[];
	construction: SimulatorConstruction | null;
	/** Build mode: where every piece of furniture stands, and the decorations owned. */
	interior: {
		items: { id: string; type: string; x: number; z: number; rot: number; stored: boolean; outside: boolean }[];
		owned: { type: string; count: number }[];
	};
	decorCatalog: {
		id: string;
		name: string;
		description: string;
		coinPrice: number;
		diamondPrice: number;
		requiredLevel: number;
		zone: "inside" | "outside";
	}[];
	ownedItems: string[];
	day: SimulatorDay;
	checkouts: SimulatorCheckout[];
	incidents: SimulatorIncident[];
	// Trucks waiting at the dock to be unloaded, and the shelf slots the stockroom can refill.
	dock: SimulatorDockDelivery[];
	restockSlots: SimulatorRestockSlot[];
	checkoutResults: SimulatorCheckoutResult[];
	staffTasks: SimulatorStaffTask[];
	event: {
		id: string;
		name: string;
		description: string;
		effectLabel: string;
		kind: string;
		endsAt: number;
		arrivalMultiplier: number;
		productionMultiplier: number;
	};
};

/** A shelf, sector or fixture paid for and still being built inside the market. */
export type SimulatorBuild = {
	id: string;
	kind: "shelf" | "sector" | "shop";
	targetId: string;
	name: string;
	startedAt: number;
	endsAt: number;
	skipCost: number;
};

export type SimulatorLayout = {
	stage: number;
	widthScale: number;
	depthScale: number;
	storage: boolean;
	parking: boolean;
	loadingYard: boolean;
	premium: boolean;
	/** The central warehouse replaces the small depot and moves the truck yard. */
	storageLarge: boolean;
	sectorIds: string[];
};

export type SimulatorDayRequest = {
	id: string;
	customerId: string;
	customerName: string;
	kind: string;
	message: string;
	productId: number;
	productName: string;
	createdAt: number;
	expiresAt: number;
	status: string;
};

export type SimulatorDay = {
	phase: string;
	dayNumber: number;
	startedAt: number;
	endsAt: number;
	loyalty: number;
	contractTitle: string;
	contractLabel: string;
	contractProgress: number;
	contractCompleted: boolean;
	grade: string;
	requests: SimulatorDayRequest[];
};

export type SimulatorCheckout = {
	id: string;
	customerId: string;
	customerName: string;
	mood: string;
	method: string;
	total: number;
	cashGiven: number;
	readyAt: number;
	expiresAt: number;
	items: { productId: number; name: string; quantity: number; unitPrice: number }[];
};

export type SimulatorCheckoutResult = {
	id: string;
	customerId: string;
	status: string;
	mistake: string;
	charged: number;
	tip: number;
};

export type SimulatorDockDelivery = {
	id: string;
	productId: number;
	productName: string;
	category: string;
	zone: string;
	quantity: number;
	unloaded: number;
	boxUnits: number;
	room: number;
	arrivedAt: number;
};
export type SimulatorRestockSlot = {
	slotId: string;
	shelfId: string;
	shelfName: string;
	productId: number;
	productName: string;
	zone: string;
	stock: number;
	capacity: number;
	reserve: number;
};
// One job of a stock clerk or cleaner: restock trips carry a box (box) for a shelf or sector counter
// (shelfId); incident jobs go to a mishap (incidentId, incidentKind) at its shelf.
export type SimulatorStaffTask = {
	id: string;
	employeeId: string;
	role: string;
	kind: "restock" | "incident";
	startedAt: number;
	endsAt: number;
	shelfId: string;
	slotId: string;
	productId: number;
	productName: string;
	units: number;
	box: string;
	incidentId: string;
	incidentKind: string;
};

export type SimulatorIncident = {
	id: string;
	kind: string;
	shelfId: string;
	shelfName: string;
	productId: number;
	productName: string;
	createdAt: number;
	fixCost: number;
	tagPrice: number;
	price: number;
};

export type SimulatorConstruction = {
	expansionId: string;
	startedAt: number;
	endsAt: number;
	skipCost: number;
	/** The market layout once this expansion opens (the building site is drawn around it). */
	targetLayout: SimulatorLayout;
};
