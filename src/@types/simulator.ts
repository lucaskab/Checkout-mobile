import type { GameActions, GameState } from "./game";
export type SimulatorPanel =
	| "store"
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
