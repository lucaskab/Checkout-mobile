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
		requiredLevel: number;
		expiresAt: number;
	}[];
	sectors: {
		id: string;
		name: string;
		unlocked: boolean;
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
	expansionStates: {
		id: string;
		name: string;
		requiredLevel: number;
		unlocked: boolean;
	}[];
	ownedItems: string[];
	day: SimulatorDay;
	checkouts: SimulatorCheckout[];
	incidents: SimulatorIncident[];
	// Trucks waiting at the dock to be unloaded, and the shelf slots the stockroom can refill.
	dock: SimulatorDockDelivery[];
	restockSlots: SimulatorRestockSlot[];
	checkoutResults: SimulatorCheckoutResult[];
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

export type SimulatorLayout = {
	stage: number;
	widthScale: number;
	depthScale: number;
	storage: boolean;
	parking: boolean;
	loadingYard: boolean;
	premium: boolean;
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
