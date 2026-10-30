import type { GameEraState, MarketEraId } from "@/@types/economy";
export type GameInventory = Record<number, number>;

export type GameInventoryCapacityLevels = Record<number, number>;

export type GameShelfStock = Record<string, number>;

export type GameShelfAssignments = Record<string, number | null>;

export type GameShelfPrices = Record<string, number>;
export type GameShelfSlotCounts = Record<string, number>;

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
	status: "pagou" | "no caixa" | "saiu sem comprar";
	/**
	 * The event that brought this customer (its id, e.g. "quinto-dia-util"): Unity starts their visit in the
	 * event's scene (the ATM queue, the bus stop, the street fair…) before they walk in and shop. Absent = a
	 * normal walk-in or car customer.
	 */
	origin?: string;
};

export type GameMarketState = {
	/** Customers who left products behind because no basket or cart was big enough (lifetime count; drives a tip). */
	cartShortfall?: number;
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
	/** The last coins the placed machines (gumball, claw machine) took: Unity shows them over the machine. */
	decorPlays?: { itemId: string; decorId: string; coins: number; at: number }[];
	/** Coins the machines earned in all, by decoration id. */
	decorEarnings?: Record<string, number>;
	randomSeed: number;
	soldByProduct: Record<number, number>;
	currentShift: GameShiftState | null;
	todayRevenue: number;
	totalExperience: number;
	totalRevenue: number;
	unitsSold: number;
	unlockedProductIds: number[];
	/** Levels gained since the player last saw the level-up celebration (desktop/pages/level-up.ts). */
	levelUp?: GameLevelUp | null;
};

/** A conquest waiting to be celebrated on screen (src/services/celebrations.ts). */
export type GameCelebrationKind = "lot" | "era" | "sector" | "shelf" | "shop" | "tier";
export type GameCelebration = {
	id: string;
	kind: GameCelebrationKind;
	/** Lot id, expansion id, sector id, fixture id or shop item id. */
	targetId: string;
	at: number;
};

export type GameLevelUp = {
	/** Level before the first of these level-ups. */
	from: number;
	/** Level reached. */
	to: number;
	at: number;
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
import type { MarketPaintCurrency, MarketPaintState } from "./market-paint";
import type { OnboardingState } from "./onboarding";
import type { RewardedAdsState } from "@/services/rewarded-ads";
import type { CheckoutCounterState } from "./checkout-counter";
import type {
	CurrencyPackGrant,
	CurrencyPurchaseState,
	GrantCurrencyPurchaseInput,
} from "./currency-purchase";
import type { EmployeeRole, GameEmployeesState } from "./employee";
import type { DeliveryPackResult, DeliveryState } from "./delivery";
import type { GameEventsState } from "./game-event";
import type { InteriorState } from "./interior";
import type { InteriorConstruction } from "./interior-construction";
import type { GameInventoryLots, GameShelfLots } from "./inventory-lot";
import type {
	LogisticsState,
	PlaceSupplierCartInput,
	PlaceSupplierOrderInput,
} from "./logistics";
import type {
	MarketExpansionConstruction,
	MarketExpansionCurrency,
	MarketExpansionId,
} from "./market-expansion";
import type { GameDayState } from "./market-day";
import type { GameMissionsState } from "./mission";
import type {
	GameProductionState,
	ProductionSectorId,
	StartProductionInput,
} from "./production";
import type { ShelfUpgradeCurrency } from "./shelf-capacity";
import type { GameShopState, ShopCurrency } from "./shop";
import type { ReceivingState } from "./receiving";
import type { StoreIncidentKind, StoreIncidentsState } from "./store-incident";
import type { SupplierOrderSlotCurrency } from "./supplier-capacity";

export type RestockShelfInput = {
	amount?: number;
	productId: number;
	shelfId: string;
};

export type GameState = {
	/** Stage of the market (mesinha → rede) and the evolution being built. */
	era: GameEraState;
	/** Level of each product (productId → 1…10): more profit per sale and more attractive. */
	productLevels: Record<number, number>;
	/** Daily login gift: last calendar day claimed and the streak (1–7). */
	dailyLogin: { lastClaimDay: string; streak: number };
	/** Product album: collections whose reward was claimed. */
	albumClaimedIds: string[];
	/** Weekly event: the week being counted, the theme's sales when it started and whether its prize was paid. */
	weeklyEvent: { weekKey: string; baseline: number; claimed: boolean };
	/** Land around the market: lots bought, lots cleared and the one being cleared. */
	lots: {
		owned: string[];
		cleared: string[];
		clearing: { lotId: string; startedAt: number; endsAt: number } | null;
	};
	checkout: CheckoutCounterState;
	coins: number;
	currencyPurchases: CurrencyPurchaseState;
	daily: GameDailyState;
	day: GameDayState;
	events: GameEventsState;
	employees: GameEmployeesState;
	incidents: StoreIncidentsState;
	receiving: ReceivingState;
	inventory: GameInventory;
	inventoryLots: GameInventoryLots;
	inventoryCapacityLevels: GameInventoryCapacityLevels;
	logistics: LogisticsState;
	market: GameMarketState;
	offlineSummary: OfflineRewardSummary | null;
	/** Rewarded videos watched (daily count and cap: src/services/rewarded-ads.ts). */
	rewardedAds: RewardedAdsState;
	/**
	 * The last time the player tried to spend more diamonds than they have (not saved): the HUD / app opens the
	 * diamond store on it and clears it (dismissDiamondShortfall).
	 */
	diamondShortfall?: { needed: number; missing: number; at: number } | null;
	lastSessionAt: number;
	unlockedMarketExpansionIds: MarketExpansionId[];
	/** The paid expansion still being built (it joins the market when it finishes). */
	marketExpansionConstruction: MarketExpansionConstruction | null;
	/** Furniture layout inside the market (build mode) and the decorations bought. */
	interior: InteriorState;
	/** Shelves, sectors and fixtures paid for and still being built inside the market. */
	interiorConstructions: InteriorConstruction[];
	/** Production sectors already built (the level only lets the player build them). */
	builtSectorIds: ProductionSectorId[];
	missions: GameMissionsState;
	production: GameProductionState;
	shop: GameShopState;
	shelfAssignments: GameShelfAssignments;
	shelfLots: GameShelfLots;
	shelfStock: GameShelfStock;
	shelfPrices: GameShelfPrices;
	shelfSlotCounts: GameShelfSlotCounts;
	unlockedShelfSlots: number;
	shelfUpgradeLevels: GameShelfUpgradeLevels;
	/** Condition 0–100 of each fixture (src/services/shelf-care.ts); missing = spotless. */
	shelfCare: GameShelfCare;
	statistics: GameStatistics;
	/** Conquests still to be celebrated on screen, oldest first. */
	celebrations?: GameCelebration[];
	/** First-time tutorial and one-off tips (src/services/onboarding.ts). */
	onboarding: OnboardingState;
	/** The Delivery app: online orders waiting, packed and on their way (src/services/delivery.ts). */
	delivery: DeliveryState;
	/** "Cores do mercado": the two colours the market is painted in (src/data/market-paint.ts). */
	marketPaint: MarketPaintState;
};

/** Condition 0–100 of each physical fixture (shelf or sector counter). */
export type GameShelfCare = Record<string, number>;

export type GameActions = {
	activateLogisticsBoost: () => boolean;
	claimDailyGoal: () => boolean;
	claimDayResult: () => boolean;
	closeDay: () => boolean;
	completeCheckout: (checkoutId: string, charged: number) => boolean;
	/** The customer's walker reached the register: their basket can be rung up from now. */
	checkoutArrived: (customerId: string) => boolean;
	completeOrderFinalStage: (orderId: string) => boolean;
	claimMission: (missionId: string) => boolean;
	/** Claims every finished mission at once (the "Resgatar todas" button). */
	claimAllMissions: () => boolean;
	deliverOrderInstantly: (orderId: string) => boolean;
	devAdjustCoins: (amount: number) => void;
	/** DEV: jump straight to an era (no cost, no obra). */
	devSetMarketEra: (eraId: MarketEraId) => boolean;
	/** DEV: pretend the player was away this many hours (obras advance, offline sales are paid). */
	devPassTime: (hours: number) => boolean;
	/** Pays the next era and starts its obra. */
	evolveMarketEra: () => boolean;
	/** Pays the next level of a product (price set by the current expansion). */
	upgradeProduct: (productId: number) => boolean;
	/** Claims today's login gift (once per calendar day). */
	claimDailyLogin: () => boolean;
	/** The daily gift again, after a video watched to the end (once a day; desktop/ads.ts checks the video). */
	claimDailyLoginBonus: (adId: string) => { coins: number; diamonds: number } | null;
	/** The missed contract's consolation, after a video watched to the end (once per day result). */
	claimContractConsolation: (adId: string) => { coins: number; diamonds: number; experience: number; label: string } | null;
	/** Pays a completed collection of the product album (once). */
	claimAlbumCollection: (collectionId: string) => boolean;
	/** Pays the prize of this week's event once its goal is reached. */
	claimWeeklyEvent: () => boolean;
	/** Buys a lot (lot 1 first, then lots next to owned land or to the square). */
	buyLot: (lotId: string) => boolean;
	/** Pays the crew that clears a bought lot (abandoned house, rubble…). */
	clearLot: (lotId: string) => boolean;
	/** Finishes the clearing with diamonds. */
	finishLotClearingNow: () => boolean;
	/** Ends the clearing whose time has come (tick). */
	processLotClearing: (now?: number) => boolean;
	/** Finishes the era obra with diamonds. */
	finishMarketEraNow: () => boolean;
	processMarketEraConstruction: (now?: number) => boolean;
	devAdjustDiamonds: (amount: number) => void;
	devAdjustInventory: (productId: number, amount: number) => void;
	devActivateGameEvent: (eventId: string) => boolean;
	devArriveDelivery: (productId: number, quantity?: number) => boolean;
	devTriggerIncident: (kind: StoreIncidentKind) => boolean;
	devClearDock: () => boolean;
	/** DEV: finishes the running expansion works for free. */
	devFinishMarketExpansion: () => boolean;
	finishProductionNow: (jobId: string) => boolean;
	/** Pays diamonds to complete the expansion under construction right away. */
	finishMarketExpansionNow: () => boolean;
	/** Pays for a production sector: the builders need some time before it opens. */
	buildSector: (sectorId: string, currency?: "coins" | "diamonds") => boolean;
	/** Pays diamonds to finish a shelf, sector or fixture under construction right away. */
	finishInteriorConstructionNow: (constructionId: string) => boolean;
	/** Opens every shelf, sector and fixture whose building time has passed. */
	processInteriorConstructions: (now?: number) => boolean;
	/** DEV: finishes every build inside the market for free. */
	devFinishInteriorConstructions: () => boolean;
	/** Build mode: stores where every piece of furniture stands. */
	saveInteriorLayout: (items: unknown) => boolean;
	/** Build mode shop: buys one decoration (it waits in the inventory until placed). */
	purchaseDecor: (decorId: string, currency?: "coins" | "diamonds") => boolean;
	/** Evolving decorations (ATM, gumball, claw machine): every piece of the kind takes the next tier. */
	upgradeDecorTier: (decorId: string, currency?: "coins" | "diamonds") => boolean;
	/** "Cores do mercado": repaints the market in `primary` + `accent` (hex) for coins or diamonds; classic is free. */
	applyMarketPaint: (primary: string, accent: string, currency?: MarketPaintCurrency) => boolean;
	/** "Voltar ao clássico": the brand navy and gold again, free. */
	resetMarketPaint: () => boolean;
	fixIncident: (incidentId: string) => boolean;
	/** Engarrafamento: hand a drink through the window of the driver who asked (src/services/event-interactions.ts). */
	serveWindowSale: (requestId: string) => boolean;
	hireEmployee: (role: EmployeeRole) => boolean;
	grantCurrencyPurchase: (input: GrantCurrencyPurchaseInput) => boolean;
	/**
	 * A store purchase of `packIdOrProductId` (transaction `transactionId`, once): credits the pack as the catalog
	 * prices it for the player now (src/data/currency-packs.ts). Null if refused (unknown pack or a transaction already
	 * credited). A paid transaction is always credited, even a second welcome combo (the buy button checks that).
	 */
	grantCurrencyPack: (packIdOrProductId: string, transactionId: string) => CurrencyPackGrant | null;
	dismissDiamondShortfall: () => void;
	/** A rewarded video watched to the end: its diamonds (null if refused: daily cap, too soon, repeated id). */
	claimRewardedAd: (adId: string) => number | null;
	placeSupplierOrder: (input: PlaceSupplierOrderInput) => boolean;
	/** The shop's cart: one truck (one slot) carrying several products, each in boxes (src/services/supplier-cart.ts). */
	placeSupplierCart: (input: PlaceSupplierCartInput) => boolean;
	/** One truck with every product that is running out (as many boxes as the truck, room and coins allow). */
	orderLowStock: () => boolean;
	processGameEvents: () => boolean;
	processCheckoutCounter: () => boolean;
	processMarketDay: () => boolean;
	processStoreIncidents: () => boolean;
	processReceiving: () => boolean;
	/** Delivery app: offers come and expire, packed bags reach the door, motoboys leave and deliver. */
	processDelivery: (now?: number) => boolean;
	/** Accepts an offer (a free slot, before it expires); the packing gets 4 minutes. */
	acceptDeliveryOrder: (orderId: string, now?: number) => boolean;
	declineDeliveryOrder: (orderId: string) => boolean;
	/** Packs the bag from the stockroom (missing units allowed) and calls the motoboy. */
	packDeliveryOrder: (orderId: string, result: DeliveryPackResult, now?: number) => boolean;
	/** The motoboy at the door takes the bag ("a-caminho"). */
	handOverDelivery: (orderId: string, now?: number) => boolean;
	/** DEV: puts a new order in the Delivery app (QA). */
	devSpawnDeliveryOffer: (now?: number) => boolean;
	unloadAllDeliveries: () => boolean;
	unloadDelivery: (deliveryId: string, units?: number) => boolean;
	processEmployeeWork: () => boolean;
	processEmployeePayroll: () => boolean;
	processProductionJobs: () => boolean;
	/** Opens the finished expansion once its building time has passed. */
	processMarketExpansionConstruction: (now?: number) => boolean;
	processInventorySpoilage: () => boolean;
	processSupplierOrders: () => boolean;
	purchaseShopItem: (itemId: string, currency: ShopCurrency) => boolean;
	/** Starts one bought booster (Melhorias → Boosters); a running one gets the extra time. */
	activateShopBooster: (itemId: string) => boolean;
	processNextCustomer: () => boolean;
	processSessionResume: () => boolean;
	dismissOfflineSummary: () => void;
	/** The player closed the level-up celebration. */
	dismissLevelUp: () => void;
	dismissCelebration: (id: string) => void;
	/** Moves the tutorial on when the game shows the step was played (host: every second and on page changes). */
	processOnboarding: (route?: string) => boolean;
	/** "Vamos lá" / "Entendi" on a tutorial card. */
	onboardingNext: () => boolean;
	/** "Já sei jogar" on the welcome card. */
	skipOnboarding: () => boolean;
	/** Guia → "Rever tutorial". */
	restartOnboarding: () => boolean;
	/** "Entendi" on a one-off tip. */
	dismissOnboardingTip: () => boolean;
	resetGame: () => void;
	/** Opens a turn; from the Späti on it can be a night turn ("noite"). */
	startDay: (contractId: string, shift?: "dia" | "noite") => boolean;
	assignProductToShelf: (
		shelfId: string,
		productId: number,
		replace?: boolean,
	) => boolean;
	clearShelf: (shelfId: string) => boolean;
	/** Tidies a fixture up (shelf window): condition back to 100. */
	tendShelf: (shelfId: string) => boolean;
	/** DEV: makes a fixture messy (QA of the shelf care game). */
	devWearShelf: (shelfId: string, amount?: number) => boolean;
	/** Swaps two slots of the same fixture (product, stock and price move together). */
	swapShelfSlots: (firstSlotId: string, secondSlotId: string) => boolean;
	restockShelf: (input: RestockShelfInput) => boolean;
	setMarketLevel: (level: number) => void;
	setEmployeeWorking: (employeeId: string, isWorking: boolean) => boolean;
	trainEmployee: (employeeId: string) => boolean;
	/** false when nothing changed: pieces still to place, or a finished day waiting for its results. */
	setMarketOpen: (isOpen: boolean) => boolean;
	setShelfPrice: (shelfId: string, price: number) => boolean;
	startProduction: (input: StartProductionInput) => boolean;
	/** Production made by hand in the kitchen game (stars 1–3; 3 = one extra unit). */
	cookByHand: (input: { recipeId: string; sectorId: ProductionSectorId; stars: number }) => boolean;
	upgradeSupplierOrderSlots: (currency: SupplierOrderSlotCurrency) => boolean;
	upgradeInventoryCapacity: (productId: number) => boolean;
	expandShelfSlots: (shelfId: string) => boolean;
	unlockNextShelf: () => boolean;
	unlockNextShelfSlot: () => boolean;
	unlockMarketExpansion: (
		expansionId: MarketExpansionId,
		currency?: MarketExpansionCurrency,
	) => boolean;
	unlockProduct: (productId: number) => void;
	upgradeShelfCapacity: (
		shelfId: string,
		currency: ShelfUpgradeCurrency,
	) => boolean;
};

export type GameStore = GameActions & GameState;
