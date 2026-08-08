export type UnityShelfSnapshot = {
	id: string;
	displayName: string;
	productId: string;
	productName: string;
	stock: number;
	capacity: number;
	sellingPrice: number;
	unlocked: boolean;
	x: number;
	z: number;
};

export type UnityGameSnapshot = {
	coins: number;
	premiumCurrency: number;
	level: number;
	experience: number;
	experienceToNextLevel: number;
	customersServed: number;
	unitsSold: number;
	todayRevenue: number;
	customerSatisfaction: number;
	marketOpen: boolean;
	employeeHired: boolean;
	shelves: UnityShelfSnapshot[];
	inventory: Array<{
		productId: string;
		productName: string;
		quantity: number;
	}>;
	deliveries: Array<{
		productId: string;
		productName: string;
		quantity: number;
		remainingSeconds: number;
	}>;
	production: {
		recipeId: string;
		recipeName: string;
		outputQuantity: number;
		remainingSeconds: number;
		running: boolean;
	};
};

export type UnityGameAction =
	| { type: "toggle_market" }
	| { type: "restock"; targetId: string; amount: number }
	| { type: "order"; targetId: string; amount: number }
	| { type: "produce"; targetId: string }
	| { type: "build"; targetId: string; x: number; z: number };

export type UnityGameEvent = {
	type: string;
	targetId: string;
	amount: number;
	coins: number;
	level: number;
	message: string;
};

/**
 * Host-side adapter shape for a future Unity-as-a-Library native module.
 * The implementation belongs in the RN native wrapper, not in the game store.
 */
export type CheckoutUnityHost = {
	applySnapshot(snapshot: UnityGameSnapshot): void;
	requestAction(action: UnityGameAction): void;
	onEvent(listener: (event: UnityGameEvent) => void): () => void;
};
