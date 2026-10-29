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
	| "grantCurrencyPack"
	| "dismissDiamondShortfall"
	| "claimRewardedAd"
	| "claimDailyLoginBonus"
	| "claimContractConsolation"
	| "unlockProduct"
	| "setMarketLevel"
	| "dismissOfflineSummary"
	| "dismissLevelUp"
	| "dismissCelebration"
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
	/** Supplier trucks: every product on the truck in boxes (`lines`), and the boxes in all. */
	orders: Array<
		Omit<GameState["logistics"]["orders"][number], "lines"> & {
			productCategory: string;
			boxes: number;
			lines: SimulatorOrderLine[];
		}
	>;
	/** The supplier catalog of the shop (src/services/supplier-cart.ts): every product the player can order now. */
	supplierCatalog: SimulatorSupplierProduct[];
	supplierInfo: SimulatorSupplierInfo;
	jobs: GameState["production"]["jobs"];
	/** The Delivery app (src/services/delivery.ts): online orders, the rating and the streak. */
	delivery: SimulatorDelivery;
	customers: GameState["market"]["recentCustomers"];
	expansions: string[];
	era: {
		id: string;
		index: number;
		name: string;
		/** The market building on the lots (mercadinho on); false = a stall on the sidewalk. */
		building: boolean;
		grid: { x0: number; z0: number; width: number; depth: number; columns: number; rows: number };
		/** Every lot of the block as a rectangle (src/data/market-lots.ts). */
		lotRects: {
			id: string;
			label: string;
			x0: number;
			z0: number;
			x1: number;
			z1: number;
			price: number;
			ruin: string;
			ruinName: string;
			status: string;
			clearCost: number;
			clearDurationMs: number;
			clearStartedAt: number;
			clearEndsAt: number;
			skipCost: number;
			occupied: boolean;
			neededBy: string;
		}[];
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
		zone: "inside" | "outside" | "both";
		/** A "melhoria": it does something while placed (the shop marks it). */
		upgrade: boolean;
		/** Machines that pay only up to this many placed copies (0: no limit); the build tray shows "2/3". */
		limit: number;
	}[];
	/** Coins the placed machines just took (newest first): Unity floats them over the machine. */
	decorPlays: { itemId: string; decorId: string; coins: number; at: number }[];
	ownedItems: string[];
	/** Boosters running now (Melhorias → Boosters) and the seconds each has left: the map plays their effects. */
	boosts: string[];
	boostSeconds: number[];
	day: SimulatorDay;
	checkouts: SimulatorCheckout[];
	incidents: SimulatorIncident[];
	// Trucks waiting at the dock to be unloaded, and the shelf slots the stockroom can refill.
	dock: SimulatorDockDelivery[];
	restockSlots: SimulatorRestockSlot[];
	stockroom: SimulatorStockroomEntry[];
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
		/** "inspection" | "window-sales" | "" (src/services/event-interactions.ts). */
		interaction: string;
		/** Vigilância sanitária: the inspector's stops (the open one is where he stands). */
		stops: SimulatorInspectionStop[];
		/** The approval seal hangs on the door for the rest of the turn. */
		seal: boolean;
		/** Engarrafamento: drivers asking for a drink through the window. */
		windowRequests: SimulatorWindowRequest[];
		windowServed: number;
		windowGoal: number;
	};
};

export type SimulatorDelivery = {
	unlocked: boolean;
	/** Name of the era that opens the app (minimercado). */
	unlockEraName: string;
	/** Accepted orders the player can carry at once. */
	slots: number;
	/** Accepted orders on the way through the packing, the motoboy and the trip. */
	active: number;
	rating: number;
	streak: number;
	bestStreak: number;
	delivered: number;
	orders: SimulatorDeliveryOrder[];
};

export type SimulatorDeliveryOrder = {
	id: string;
	/** oferta | aceito | aguardando-moto | moto-na-porta | a-caminho | entregue | expirado | recusado | cancelado */
	status: string;
	customerName: string;
	neighborhood: string;
	avatar: number;
	/** The customer's note; "" when there is none. */
	note: string;
	items: { productId: number; productName: string; category: string; quantity: number; packed: number }[];
	distanceKm: number;
	fee: number;
	itemsValue: number;
	/** Packed units / ordered units; null before packing. */
	fillRatio: number;
	quality: number;
	stars: number;
	tip: number;
	bonus: number;
	/** Coins paid on arrival (null until delivered). */
	paid: number;
	courier: {
		id: string;
		name: string;
		color: string;
		/** Radio lines of this motoboy: one is picked when he arrives, leaves and delivers. */
		phrases: { arrive: string[]; leave: string[]; delivered: string[] };
	} | null;
	/** Absolute times in epoch ms (null when not reached yet): Unity counts the seconds left. */
	createdAt: number;
	expiresAt: number;
	acceptedAt: number;
	packBy: number;
	packedAt: number;
	arriveAt: number;
	doorSince: number;
	deliverAt: number;
};

export type SimulatorInspectionStop = {
	id: string;
	/** waiting | open | fixed | failed */
	status: string;
	shelfId: string;
	incidentId: string;
	kind: string;
	at: number;
	deadline: number;
};

export type SimulatorWindowRequest = {
	id: string;
	/** Lane of the jam (0 = next to the sidewalk) and car in it. */
	lane: number;
	slot: number;
	productId: number;
	productName: string;
	/** waiting | served | missed */
	status: string;
	expiresAt: number;
	/** The market has the drink (shelf or storeroom): otherwise the bubble shows it greyed out. */
	inStock: boolean;
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

export type SimulatorDay = {
	phase: string;
	/** Turn of the day ("noite" from the Späti on). */
	shift: "dia" | "noite";
	dayNumber: number;
	startedAt: number;
	endsAt: number;
	contractTitle: string;
	contractLabel: string;
	contractProgress: number;
	contractCompleted: boolean;
	grade: string;
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

export type SimulatorOrderLine = {
	productId: number;
	productName: string;
	boxes: number;
};

export type SimulatorSupplierInfo = {
	/** Trucks the player has (supplier slots), trucks on the road, and most boxes one truck takes. */
	slots: number;
	active: number;
	maxBoxes: number;
	freightCoupons: number;
};

export type SimulatorSupplierProduct = {
	productId: number;
	name: string;
	category: string;
	categoryLabel: string;
	/** Units in one box, and the price of one box now (events and shop items included). */
	caseSize: number;
	boxPrice: number;
	/** Cost of one unit (boxPrice / caseSize) and the shelf price now. */
	unitCost: number;
	salePrice: number;
	/** Units in the stockroom and on the shelves. */
	stockUnits: number;
	shelfUnits: number;
	/** Boxes the stockroom takes, the places free now (after what is on the road) and boxes on the road or at the dock. */
	capacityBoxes: number;
	freeBoxes: number;
	incomingBoxes: number;
	/** The stockroom is below LOW_STOCK_SHARE of its room. */
	low: boolean;
	/** Not unlocked yet (only products of this or the next expansion are listed as locked). */
	locked: boolean;
	unlockLevel: number;
	/** Delivery time of a truck with this product now. */
	deliverySeconds: number;
};

export type SimulatorDockDelivery = {
	id: string;
	/** The supplier order whose truck brought it ("" for older deliveries). */
	orderId: string;
	productId: number;
	productName: string;
	category: string;
	zone: string;
	quantity: number;
	unloaded: number;
	/** Units in each supplier box, and the boxes still in the truck. */
	boxUnits: number;
	boxes: number;
	room: number;
	arrivedAt: number;
};
/** What the stockroom holds of a product, in its supplier boxes (the receiving game draws them on the racks). */
export type SimulatorStockroomEntry = {
	productId: number;
	productName: string;
	category: string;
	zone: string;
	units: number;
	caseSize: number;
	/** Boxes on the racks (a box opened for the shelves still counts) and the most the stockroom takes. */
	boxes: number;
	capacityBoxes: number;
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
	/** Units in one supplier box of the product (REPOR boxes come out of the stockroom whole). */
	caseSize: number;
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
