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
	level: number;
	isOpen: boolean;
	satisfaction: number;
	served: number;
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
		expiresAt: number;
	}[];
	sectors: { id: string; name: string; unlocked: boolean; jobs: number }[];
	employees: GameState["employees"]["employees"];
	orders: GameState["logistics"]["orders"];
	jobs: GameState["production"]["jobs"];
	customers: GameState["market"]["recentCustomers"];
	expansions: string[];
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
