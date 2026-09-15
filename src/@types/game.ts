export type GameInventory = Record<number, number>;

export type GameInventoryCapacityLevels = Record<number, number>;

export type GameShelfStock = Record<string, number>;

export type GameShelfAssignments = Record<string, number | null>;

export type GameShelfPrices = Record<string, number>;

export type GameShelfUpgradeLevels = Record<string, number>;

export type GameMarketCustomer = {
	purchases?: {
		shelfId: string;
		productId: number;
		quantity: number;
		revenue: number;
	}[];
	id: string;
	item: string;
	mood: "calmo" | "com-pressa" | "feliz" | "estressado";
	name: string;
	satisfaction: number;
	spent: number;
	status: "pagou" | "saiu sem comprar";
};

export type GameMarketState = {
	customerSatisfaction: number;
	customersServed: number;
	customersWhoBought: number;
	experience: number;
	isOpen: boolean;
	lastExperienceGain: number;
	lastShiftSummary: GameShiftSummary | null;
	level: number;
	nextCustomerAt: number | null;
	recentUnlockProductIds: number[];
	recentCustomers: GameMarketCustomer[];
	randomSeed: number;
	soldByProduct: Record<number, number>;
	currentShift: GameShiftState | null;
	todayRevenue: number;
	totalExperience: number;
	totalRevenue: number;
	unitsSold: number;
	unlockedProductIds: number[];
};

export type GameShiftState = {
	startedAt: number;
	startingCustomersServed: number;
	startingExperience: number;
	startingSatisfaction: number;
	startingTotalRevenue: number;
	startingUnitsSold: number;
};

export type GameShiftSummary = {
	closedAt: number;
	customersServed: number;
	durationMs: number;
	experienceGained: number;
	revenue: number;
	satisfactionChange: number;
	satisfaction: number;
	unitsSold: number;
};

export type GameDailyState = {
	claimed: boolean;
	customersServed: number;
	goal: number;
	goalReached: boolean;
	lastCompletedDayKey: string | null;
	streak: number;
	unitsSold: number;
	dayKey: string;
	revenue: number;
};

export type OfflineRewardSummary = {
	coins: number;
	customers: number;
	durationMs: number;
};

export type ExperienceProgress = {
	experience: number;
	level: number;
	levelsGained: number;
};

import type { GameStatistics } from "./achievement";
import type {
	CurrencyPurchaseState,
	GrantCurrencyPurchaseInput,
} from "./currency-purchase";
import type { EmployeeRole, GameEmployeesState } from "./employee";
import type { GameEventsState } from "./game-event";
import type { GameInventoryLots, GameShelfLots } from "./inventory-lot";
import type { LogisticsState, PlaceSupplierOrderInput } from "./logistics";
import type { MarketExpansionId } from "./market-expansion";
import type { GameMissionsState } from "./mission";
import type { GameProductionState, StartProductionInput } from "./production";
import type { ShelfUpgradeCurrency } from "./shelf-capacity";
import type { GameShopState, ShopCurrency } from "./shop";
import type { SupplierOrderSlotCurrency } from "./supplier-capacity";

export type RestockShelfInput = {
	amount?: number;
	productId: number;
	shelfId: string;
};

export type GameState = {
	coins: number;
	currencyPurchases: CurrencyPurchaseState;
	daily: GameDailyState;
	events: GameEventsState;
	employees: GameEmployeesState;
	inventory: GameInventory;
	inventoryLots: GameInventoryLots;
	inventoryCapacityLevels: GameInventoryCapacityLevels;
	logistics: LogisticsState;
	market: GameMarketState;
	offlineSummary: OfflineRewardSummary | null;
	lastSessionAt: number;
	unlockedMarketExpansionIds: MarketExpansionId[];
	missions: GameMissionsState;
	production: GameProductionState;
	shop: GameShopState;
	shelfAssignments: GameShelfAssignments;
	shelfLots: GameShelfLots;
	shelfStock: GameShelfStock;
	shelfPrices: GameShelfPrices;
	unlockedShelfSlots: number;
	shelfUpgradeLevels: GameShelfUpgradeLevels;
	statistics: GameStatistics;
};

export type GameActions = {
	activateLogisticsBoost: () => boolean;
	claimDailyGoal: () => boolean;
	completeOrderFinalStage: (orderId: string) => boolean;
	claimMission: (missionId: string) => boolean;
	deliverOrderInstantly: (orderId: string) => boolean;
	devAdjustCoins: (amount: number) => void;
	devAdjustDiamonds: (amount: number) => void;
	devAdjustInventory: (productId: number, amount: number) => void;
	devActivateGameEvent: (eventId: string) => boolean;
	finishProductionNow: (jobId: string) => boolean;
	hireEmployee: (role: EmployeeRole) => boolean;
	grantCurrencyPurchase: (input: GrantCurrencyPurchaseInput) => boolean;
	placeSupplierOrder: (input: PlaceSupplierOrderInput) => boolean;
	processGameEvents: () => boolean;
	processEmployeeWork: () => boolean;
	processEmployeePayroll: () => boolean;
	processProductionJobs: () => boolean;
	processInventorySpoilage: () => boolean;
	processSupplierOrders: () => boolean;
	purchaseShopItem: (itemId: string, currency: ShopCurrency) => boolean;
	processNextCustomer: () => boolean;
	processSessionResume: () => boolean;
	dismissOfflineSummary: () => void;
	resetGame: () => void;
	assignProductToShelf: (
		shelfId: string,
		productId: number,
		replace?: boolean,
	) => boolean;
	clearShelf: (shelfId: string) => boolean;
	restockShelf: (input: RestockShelfInput) => boolean;
	setMarketLevel: (level: number) => void;
	setEmployeeWorking: (employeeId: string, isWorking: boolean) => boolean;
	trainEmployee: (employeeId: string) => boolean;
	setMarketOpen: (isOpen: boolean) => void;
	setShelfPrice: (shelfId: string, price: number) => boolean;
	startProduction: (input: StartProductionInput) => boolean;
	upgradeSupplierOrderSlots: (currency: SupplierOrderSlotCurrency) => boolean;
	upgradeInventoryCapacity: (productId: number) => boolean;
	unlockNextShelfSlot: () => boolean;
	unlockMarketExpansion: (expansionId: MarketExpansionId) => boolean;
	unlockProduct: (productId: number) => void;
	upgradeShelfCapacity: (
		shelfId: string,
		currency: ShelfUpgradeCurrency,
	) => boolean;
};

export type GameStore = GameActions & GameState;
