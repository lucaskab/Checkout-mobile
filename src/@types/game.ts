export type GameInventory = Record<number, number>;

export type GameShelfStock = Record<string, number>;

export type GameMarketCustomer = {
	emoji: string;
	id: string;
	item: string;
	name: string;
	spent: number;
	status: "pagou" | "saiu sem comprar";
};

export type GameMarketState = {
	customersServed: number;
	customersWhoBought: number;
	experience: number;
	isOpen: boolean;
	lastExperienceGain: number;
	level: number;
	nextCustomerAt: number | null;
	recentUnlockProductIds: number[];
	recentCustomers: GameMarketCustomer[];
	randomSeed: number;
	soldByProduct: Record<number, number>;
	todayRevenue: number;
	totalExperience: number;
	unitsSold: number;
	unlockedProductIds: number[];
};

export type ExperienceProgress = {
	experience: number;
	level: number;
	levelsGained: number;
};

import type { LogisticsState, PlaceSupplierOrderInput } from "./logistics";

export type RestockShelfInput = {
	amount?: number;
	productId: number;
	shelfId: string;
};

export type GameState = {
	coins: number;
	inventory: GameInventory;
	logistics: LogisticsState;
	market: GameMarketState;
	shelfStock: GameShelfStock;
};

export type GameActions = {
	activateLogisticsBoost: () => boolean;
	activateVip: () => void;
	addPremiumEntitlement: (productId: string) => void;
	completeOrderFinalStage: (orderId: string) => boolean;
	deliverOrderInstantly: (orderId: string) => boolean;
	placeSupplierOrder: (input: PlaceSupplierOrderInput) => boolean;
	processSupplierOrders: () => boolean;
	processNextCustomer: () => boolean;
	resetGame: () => void;
	restockShelf: (input: RestockShelfInput) => boolean;
	setMarketLevel: (level: number) => void;
	setMarketOpen: (isOpen: boolean) => void;
	unlockProduct: (productId: number) => void;
};

export type GameStore = GameActions & GameState;
