import { getShopItemPieceId, hasInteriorRoom } from "@/services/interior-room";
import { getDecorEffects, rollDecorPlays } from "@/services/decor-effects";
import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import { lockSave } from "@/storage/save-guard";
import type { InteriorState } from "@/@types/interior";
import type { GameStatistics } from "@/@types/achievement";
import {
	getInteriorDecor,
	createStarterInteriorState,
	normalizeInteriorState,
	sanitizeInteriorItems,
} from "@/data/interior-decor";
import type { CurrencyPurchaseState } from "@/@types/currency-purchase";
import type { CustomerArchetype } from "@/@types/customer-simulation";
import type { EmployeeRole, GameEmployeesState } from "@/@types/employee";
import type {
	GameInventory,
	GameInventoryCapacityLevels,
	GameMarketCustomer,
	GameMarketState,
	GameShelfAssignments,
	GameShelfPrices,
	GameShelfSlotCounts,
	GameShelfStock,
	GameShelfUpgradeLevels,
	GameState,
	GameStore,
	OfflineRewardSummary,
} from "@/@types/game";
import type { GameEventContext, GameEventsState } from "@/@types/game-event";
import { getGameEvent } from "@/data/game-events";
import type { GameInventoryLots, GameShelfLots } from "@/@types/inventory-lot";
import type {
	LogisticsState,
	PlaceSupplierCartInput,
	SupplierOrder,
} from "@/@types/logistics";
import type { GameMissionsState } from "@/@types/mission";
import type { GameProductionState, ProductionJob } from "@/@types/production";
import type { GameShopState } from "@/@types/shop";
import type { SupplierOrderSlotCurrency } from "@/@types/supplier-capacity";
import { getEmployeeDefinition, isEmployeeEraReached } from "@/data/employees";
import {
	getInventoryCapacity,
	getNextInventoryCapacityUpgrade,
	normalizeInventoryCapacityLevel,
} from "@/data/inventory-capacity";
import { getBoxCount, getCaseSize } from "@/data/case-sizes";
import { getFreeBoxPlaces, getStockroomRoom } from "@/services/stockroom";
import {
	getMarketExpansion,
	getMarketExpansionSkipCost,
	getMissingMarketExpansionPrerequisites,
	normalizeMarketExpansionConstruction,
	normalizeMarketExpansionIds,
} from "@/data/market-expansions";
import {
	getEraOrder,
	getUnlockedProductIds,
	initialShelfAssignments,
	itemCatalog,
	shelves,
	starterShelfIds,
} from "@/data/market-products";
import { getMission, missions as missionList } from "@/data/missions";
import {
	getProductionSector,
	productionRecipes,
	productionSectors,
} from "@/data/production-sectors";
import {
	getNextShelfCapacityUpgrade,
	getNextShelfSlotUpgrade,
	getNextShelfUnlockUpgrade,
	initialUnlockedShelfSlots,
} from "@/data/shelf-capacity";
import {
	getPhysicalShelfId,
	getShelfSlotCount,
	getShelfSlotIds,
	getTotalUnlockedShelfSlots,
	getUnlockedPhysicalShelfCount,
	isShelfSlotUnlocked,
	maximumSlotsPerShelf,
	normalizeShelfSlotCounts,
	resolveShelfSlotCounts,
	shelfProductSlots,
} from "@/data/shelf-slots";
import { retiredShopItemIds, shopItems } from "@/data/shop-items";
import { getCheckoutCount, getKioskCount, KIOSK_INTERVAL_MS } from "@/data/checkout-lanes";
import {
	getNextSupplierOrderSlotUpgrade,
	initialSupplierOrderSlots,
	normalizeSupplierOrderSlots,
} from "@/data/supplier-capacity";
import {
	getCustomerArrivalDelay,
	simulateMarketVisit,
} from "@/services/customer-simulation";
import {
	createInitialDailyState,
	markDailySale,
	normalizeDailyState,
} from "@/services/daily-progress";
import type { PendingCheckout } from "@/@types/checkout-counter";
import {
	type CheckoutPayment,
	completeCheckout as completeCheckoutRule,
	createCheckoutCounterState,
	createPendingCheckout,
	enqueueCheckout,
	expireCheckouts,
	markCheckoutArrived,
	nextAutoCheckouts,
	AUTO_CASHIER_INTERVAL_MS,
	normalizeCheckoutCounterState,
} from "@/services/checkout-counter";
import {
	createStoreIncident,
	createStoreIncidentsState,
	fixStoreIncident,
	freezerSpoilage,
	getIncidentEffects,
	normalizeStoreIncidentsState,
	spawnFloorDirt,
	spawnStoreIncident,
} from "@/services/store-incidents";
import { getIncidentShelves } from "@/services/store-incidents-context";
import {
	WINDOW_CATEGORIES,
	advanceInspection,
	advanceWindowSales,
	createInspectionRun,
	createWindowSales,
	getWindowSalePrice,
	getWindowSalesBonus,
	openInspectionStop,
	pickInspectionKind,
	scoreInspection,
	serveWindowRequest,
} from "@/services/event-interactions";
import {
	acceptsCustomers,
	advanceMarketDay,
	closeMarketDay,
	createInitialDayState,
	DAY_OFFERS_REVISION,
	FREE_DAY_CONTRACT_ID,
	getLoyaltyArrivalMultiplier,
	isDayOver,
	isClosing,
	normalizeDayState,
	recordDayCheckoutLost,
	recordDayCustomer,
	recordDayIncidentFixed,
	recordDaySale,
	refreshDayOffers,
	startDay as startMarketDay,
} from "@/services/market-day";
import { type DayForecast, forecastDay, getFallbackDayForecast } from "@/services/day-forecast";
import {
	getDayProduct,
	getDayStoreContext,
} from "@/services/market-day-context";
import {
	getEmployeeTrainingCost,
	grantEmployeeExperience,
	trainEmployee as promoteEmployee,
} from "@/services/employee-progression";
import {
	EMPLOYEE_PAYROLL_INTERVAL_MS,
	getEmployeeEffects,
	getEmployeePayrollCost,
} from "@/services/employees";
import {
	activateGameEvent,
	advanceGameEvents,
	applyPassiveEventWear,
	type EventFixture,
	getAvailableGameEvents,
	getEventDemandMultiplier,
	getReferencePrice,
	pickFeaturedProduct,
	createInitialGameEventsState,
	getTurnEventKey,
	getActiveGameEventEffects,
	getEventCustomerOrigin,
	normalizeGameEventsState,
} from "@/services/game-events";
import {
	appendInventoryLots,
	createInventoryLots,
	discardExpiredInventoryLots,
	reconcileInventoryLots,
	takeInventoryLots,
} from "@/services/inventory-lots";
import { getOrderSkipCost, getSupplierOrderStatus } from "@/services/logistics";
import { getSkipDiamondCost } from "@/data/diamond-skip";
import { createRewardedAdsState, creditPlacementAd, normalizeRewardedAdsState, rewardAd } from "@/services/rewarded-ads";
import { canClaimConsolation, rollConsolation } from "@/services/contract-pressure";
import { getCurrencyPack, getCurrencyPackCoins } from "@/data/currency-packs";
import { getMissionProgress, getMissionRewardPlan, getNewlyReachedMissionIds } from "@/services/missions";
import { getProductionDiamondCost } from "@/services/production";
import {
	applyExperience,
	getExperienceFromSales,
} from "@/services/progression";
import {
	addDockDelivery,
	createReceivingState,
	nextStaffUnload,
	normalizeReceivingState,
	unloadDock,
} from "@/services/receiving";
import { getShopEffects } from "@/services/shop-effects";
import { getSimulatorLayout } from "@/services/simulator-layout";
import {
	getShiftPayroll,
	getStaffStorageKind,
	planStaffTasks,
	type RestockCandidate,
	takeFinishedStaffTasks,
} from "@/services/staff-work";
import { mmkvStorage } from "@/storage/mmkv";
import type { MarketEraId } from "@/@types/economy";
import { getMarketEra, marketEras, STARTING_COINS } from "@/data/economy";
import { canFixtureSell } from "@/data/fixture-products";
import { enqueueEvolution, findEvolution, getEvolutionDurationMs, getEvolutionProgress, normalizeEvolutions, scheduleEvolutions } from "@/data/fixture-evolution";
import type { FixtureEvolution } from "@/@types/fixture-evolution";
import { getFixtureAttraction, getFixtureRestockBonus, getSlotCapacity, isExclusiveAllowed, withTierRewards } from "@/services/tier-rewards";
import { getSectorCounter, getSectorCounterFor, getShelfType, isSectorShelfId, shelfTypes } from "@/data/shelf-types";
import {
	canBuyCapacityTier,
	checkoutItemTiers,
	coldRoomTierItemIds,
	getCapacityTier,
	getCheckoutTier,
	getSectorBatchOutput,
	getColdRoomTier,
	getColdRoomUpgradeCap,
	getNextDecorTier,
	getSectorSlotCount,
	getSectorTier,
	getSectorTierDefinition,
	getSectorTierPrice,
	getShelfFixtureTier,
	isChilledCategory,
	normalizeSectorTiers,
	SECTOR_MAX_TIER,
	isStallEra,
	withCheckoutRegister,
} from "@/data/fixture-tiers";
import { getShelfSlotLimit } from "@/services/fixture-tiers";
import {
	getShelfCondition,
	getSlotPositionFactor,
	normalizeShelfCare,
} from "@/services/shelf-care";
import { albumCollections, getCollectionProgress } from "@/data/product-album";
import { ERA_LOTS, getMarketLot, migrateDepotLot } from "@/data/market-lots";
import { applyInboxItems, createSocialState, normalizeSocialState, openMailPatch, sendProductPatch, utcDay } from "@/services/social";
import { getSocialRewards } from "@/data/social";
import { LEAGUE_POINTS } from "@/data/rankings";
import {
	addLeaguePoints,
	applyWrongWeek,
	createRankingsState,
	dayLeaguePoints,
	markPointsSent,
	normalizeRankingsState,
} from "@/services/rankings";
import {
	checkBuyLot,
	checkClearLot,
	createLotsState,
	finishLotClearing,
	getLotClearCost,
	getLotClearExperience,
	normalizeLotsState,
	startLotClearing,
} from "@/services/market-lots";
import { normalizeCelebrations, pushCelebration } from "@/services/celebrations";
import {
	createWeeklyEventState,
	getWeeklyNecessityMultiplier,
	getWeeklyProgress,
	getWeeklyReward,
	normalizeWeeklyEventState,
	syncWeeklyEvent,
} from "@/services/weekly-event";
import {
	canClaimDailyLogin,
	createDailyLoginState,
	getDayKey,
	getLoginReward,
	getNextLoginDay,
	normalizeDailyLoginState,
} from "@/services/daily-login";
import {
	applyProductLevel,
	ATTRACTIVENESS_PER_LEVEL,
	getProductLevel,
	getProductUpgradeCost,
	normalizeProductLevels,
} from "@/services/product-levels";
import {
	checkEraEvolution,
	createInitialEraState,
	finishEraConstruction,
	getEraEffects,
	getEraForExpansions,
	ERA_BUILDING_EXPANSIONS,
	getOfflineEraIncome,
	canOpenAtNight,
	getPiecesToPlaceBeforeOpening,
	getTurnEffects,
	getWingsForEra,
	isMarketBuilding,
	normalizeEraState,
	recordFinishedTurn,
	startEraEvolution,
} from "@/services/market-era";
import type { ProductionSectorId } from "@/@types/production";
import {
	constructionDuration,
	createPendingConstruction,
	findInteriorConstruction,
	getInteriorSkipCost,
	getShelfBuildDurationMs,
	interiorPieceIds,
	placeInteriorConstruction,
	scheduleInteriorConstructions,
	getShopItemPlaceEra,
	isBuiltShopItem,
	normalizeBuiltSectorIds,
	normalizeInteriorConstructions,
	sectorBuildPlans,
	shopItemBuildDurations,
} from "@/data/interior-construction";
import { getMaxBoxesPerOrder } from "@/data/supplier-capacity";
import {
	getOrderLines,
	getSupplierCartQuote,
	getSupplierIncoming,
	LOW_STOCK_SHARE,
} from "@/services/supplier-cart";
import type { DeliveryItem, DeliveryOrder, DeliveryState } from "@/@types/delivery";
import {
	continueOnboarding,
	createOnboardingState,
	dismissOnboardingTip as dismissOnboardingTipRule,
	normalizeOnboardingState,
	restartOnboarding as restartOnboardingRule,
	skipOnboarding as skipOnboardingRule,
	stepOnboarding,
} from "@/services/onboarding";
import {
	CLASSIC_ACCENT,
	CLASSIC_PRIMARY,
	createMarketPaintState,
	getMarketPaintCoinPrice,
	MARKET_PAINT_DIAMONDS,
	normalizeHex,
	normalizeMarketPaintState,
	withAppliedPaint,
} from "@/data/market-paint";
import {
	advanceDeliveryOrder,
	applyLateCancelToRating,
	applyStarsToRating,
	assignCourier,
	clampPackedItems,
	createDeliveryOffer,
	createDeliveryRandom,
	createInitialDeliveryState,
	getDeliverySlots,
	getFillRatio,
	getItemsValue,
	getNextOrderId,
	getOfferIntervalMs,
	getPackStars,
	handOverOrder,
	isActiveDeliveryOrder,
	isDeliveryArrived,
	isDeliveryUnlocked,
	MAX_WAITING_OFFERS,
	normalizeDeliveryState,
	PACK_WINDOW_MS,
	pushRating,
	replaceDeliveryOrder,
	settleDelivery,
	trimDeliveryOrders,
} from "@/services/delivery";
import type { ChainBranchId, FleetTruckKind } from "@/@types/chain";
import {
	addTruck,
	checkChainName,
	chooseBranchCargo,
	createChainState,
	getBranchNextStep,
	getBranchTripMs,
	getContractShortfall,
	getNextSpeedPrice,
	getNextTruckPrice,
	getTripFactor,
	isChainEmblem,
	isChainUnlocked,
	normalizeChainState,
	pickTruck,
	refreshContracts,
	releaseTrucks,
	updateBranch,
	updateBranches,
	withTruckJob,
} from "@/services/chain";
import {
	AUTO_ORDER_EVERY_MS,
	AUTO_ORDER_RESERVE,
	CHAIN_RENAME_DIAMONDS,
	DC_MAX_BOXES,
	FLEET_RETURN_SHARE,
	privateLabelProducts,
} from "@/data/chain";

// A new game: a few crates of what the sidewalk table sells (tomato, lettuce, banana, water, soda).
const initialInventory: GameInventory = {
	1: 6,
	47: 4,
	46: 6,
	21: 6,
	14: 4,
};

const initialInventoryCapacityLevels: GameInventoryCapacityLevels = {};

const initialInventoryLots: GameInventoryLots = {};

const initialShelfStock: GameShelfStock = {
	drinks: 3,
	produce: 3,
};

const initialShelfLots: GameShelfLots = {};

const initialAssignments: GameShelfAssignments = initialShelfAssignments;

const initialShelfPrices: GameShelfPrices = Object.fromEntries(
	Object.entries(initialShelfAssignments).flatMap(([shelfId, productId]) => {
		const product = itemCatalog.find((item) => item.id === productId);
		return product ? [[shelfId, product.sellingPrice]] : [];
	}),
);

// The produce crates and the styrofoam cooler come with the sidewalk table (see starterShelfIds).
const initialShelfSlotCounts = normalizeShelfSlotCounts(
	undefined,
	initialUnlockedShelfSlots * starterShelfIds.length,
);

const initialShelfUpgradeLevels: GameShelfUpgradeLevels = {};

const initialShopState: GameShopState = {
	activeBoosts: {},
	consumableAmounts: {},
	ownedItemIds: [],
};

const initialUnlockedMarketExpansionIds: GameState["unlockedMarketExpansionIds"] =
	[];

const initialProductionState: GameProductionState = {
	jobs: [],
	totalCrafted: 0,
};

const initialEmployeesState: GameEmployeesState = {
	employees: [],
	lastPayroll: null,
	nextHireNumber: 1,
	nextPayrollAt: Date.now() + EMPLOYEE_PAYROLL_INTERVAL_MS,
	nextTaskNumber: 1,
	tasks: [],
	totalSalariesPaid: 0,
};

const initialMissionsState: GameMissionsState = {
	claimedMissionIds: [],
	reachedMissionIds: [],
};

const initialStatistics: GameStatistics = {
	instantDeliveries: 0,
	instantProductionFinishes: 0,
	marketOpenings: 0,
	priceChanges: 0,
	productionJobsStarted: 0,
	restockedUnits: 0,
	shopPurchases: 0,
	spoiledUnits: 0,
	supplierOrdersPlaced: 0,
};

const initialCurrencyPurchaseState: CurrencyPurchaseState = {
	processedTransactionIds: [],
};

const initialLogisticsState: LogisticsState = {
	emergencyTokens: 1,
	freightCoupons: 1,
	logisticsBoostExpiresAt: null,
	orders: [],
	premiumCurrency: 10,
	supplierOrderSlots: initialSupplierOrderSlots,
};

const initialMarketState: GameMarketState = {
	customerSatisfaction: 55,
	customersServed: 0,
	customersWhoBought: 0,
	experience: 0,
	isOpen: false,
	lastExperienceGain: 0,
	lastShiftSummary: null,
	level: 1,
	nextCustomerAt: null,
	recentUnlockProductIds: [],
	recentCustomers: [],
	randomSeed: 1,
	soldByProduct: {},
	currentShift: null,
	todayRevenue: 0,
	totalExperience: 0,
	totalRevenue: 0,
	unitsSold: 0,
	unlockedProductIds: getUnlockedProductIds(1, "mesinha"),
};

const initialGameState: GameState = {
	era: createInitialEraState(),
	productLevels: {},
	dailyLogin: createDailyLoginState(),
	rewardedAds: createRewardedAdsState(),
	albumClaimedIds: [],
	weeklyEvent: createWeeklyEventState(),
	lots: createLotsState(),
	checkout: createCheckoutCounterState(),
	// A new game starts at the table on the sidewalk with a little change (src/data/economy.ts).
	coins: STARTING_COINS,
	currencyPurchases: initialCurrencyPurchaseState,
	daily: createInitialDailyState(1),
	day: createInitialDayState(1),
	events: createInitialGameEventsState(),
	employees: initialEmployeesState,
	incidents: createStoreIncidentsState(),
	receiving: createReceivingState(),
	inventory: initialInventory,
	inventoryLots: initialInventoryLots,
	inventoryCapacityLevels: initialInventoryCapacityLevels,
	logistics: initialLogisticsState,
	market: initialMarketState,
	offlineSummary: null,
	lastSessionAt: Date.now(),
	unlockedMarketExpansionIds: initialUnlockedMarketExpansionIds,
	marketExpansionConstruction: null,
	interior: createStarterInteriorState(),
	interiorConstructions: [],
	evolutions: [],
	builtSectorIds: [],
	sectorTiers: {},
	missions: initialMissionsState,
	production: initialProductionState,
	shop: initialShopState,
	shelfAssignments: initialAssignments,
	shelfLots: initialShelfLots,
	shelfStock: initialShelfStock,
	shelfPrices: initialShelfPrices,
	shelfSlotCounts: initialShelfSlotCounts,
	unlockedShelfSlots: initialUnlockedShelfSlots * starterShelfIds.length,
	shelfUpgradeLevels: initialShelfUpgradeLevels,
	shelfCare: {},
	statistics: initialStatistics,
	celebrations: [],
	delivery: createInitialDeliveryState(),
	onboarding: createOnboardingState(),
	marketPaint: createMarketPaintState(),
	social: createSocialState(),
	rankings: createRankingsState(),
	chain: createChainState(),
};

function getInitialGameState(): GameState {
	return {
		era: createInitialEraState(),
		productLevels: {},
		dailyLogin: createDailyLoginState(),
		rewardedAds: createRewardedAdsState(),
		albumClaimedIds: [],
		weeklyEvent: createWeeklyEventState(),
		lots: createLotsState(),
		checkout: createCheckoutCounterState(),
		coins: initialGameState.coins,
		currencyPurchases: {
			processedTransactionIds: [
				...initialGameState.currencyPurchases.processedTransactionIds,
			],
		},
		daily: createInitialDailyState(1),
		day: createInitialDayState(1),
		events: createInitialGameEventsState(),
		employees: {
			employees: initialGameState.employees.employees.map((employee) => ({
				...employee,
			})),
			lastPayroll: null,
			nextHireNumber: initialGameState.employees.nextHireNumber,
			nextPayrollAt: Date.now() + EMPLOYEE_PAYROLL_INTERVAL_MS,
			nextTaskNumber: 1,
			tasks: [],
			totalSalariesPaid: 0,
		},
		incidents: createStoreIncidentsState(),
		receiving: createReceivingState(),
		inventory: { ...initialGameState.inventory },
		inventoryLots: { ...initialGameState.inventoryLots },
		inventoryCapacityLevels: {
			...initialGameState.inventoryCapacityLevels,
		},
		logistics: {
			...initialGameState.logistics,
			orders: [...initialGameState.logistics.orders],
			supplierOrderSlots: initialGameState.logistics.supplierOrderSlots,
		},
		market: {
			...initialGameState.market,
			recentUnlockProductIds: [
				...initialGameState.market.recentUnlockProductIds,
			],
			recentCustomers: [...initialGameState.market.recentCustomers],
			soldByProduct: { ...initialGameState.market.soldByProduct },
			lastShiftSummary: initialGameState.market.lastShiftSummary,
			currentShift: initialGameState.market.currentShift,
			unlockedProductIds: [...initialGameState.market.unlockedProductIds],
		},
		offlineSummary: null,
		lastSessionAt: Date.now(),
		unlockedMarketExpansionIds: [
			...initialGameState.unlockedMarketExpansionIds,
		],
		marketExpansionConstruction: null,
		interior: createStarterInteriorState(),
		interiorConstructions: [],
		evolutions: [],
		builtSectorIds: [],
		sectorTiers: {},
		missions: {
			claimedMissionIds: [...initialGameState.missions.claimedMissionIds],
			reachedMissionIds: [],
		},
		production: {
			...initialGameState.production,
			jobs: [...initialGameState.production.jobs],
		},
		shop: {
			activeBoosts: {},
			consumableAmounts: { ...initialGameState.shop.consumableAmounts },
			ownedItemIds: [...initialGameState.shop.ownedItemIds],
		},
		shelfAssignments: { ...initialGameState.shelfAssignments },
		shelfLots: { ...initialGameState.shelfLots },
		shelfStock: { ...initialGameState.shelfStock },
		shelfPrices: { ...initialGameState.shelfPrices },
		shelfSlotCounts: { ...initialGameState.shelfSlotCounts },
		unlockedShelfSlots: initialGameState.unlockedShelfSlots,
		shelfUpgradeLevels: { ...initialGameState.shelfUpgradeLevels },
		shelfCare: {},
		statistics: { ...initialGameState.statistics },
		celebrations: [],
		delivery: createInitialDeliveryState(),
		onboarding: createOnboardingState(),
		marketPaint: createMarketPaintState(),
		social: createSocialState(),
		rankings: createRankingsState(),
		chain: createChainState(),
	};
}

/** What the retired products (Bolo artesanal, Café colecionável) were worth: old saves get coins back. */
const retiredProductRefunds: Record<number, number> = { 11: 72, 42: 350 };

/**
 * Version 40, the new catalog: retired products become coins, and the products the player can sell are
 * the ones of the expansion and level reached (plus whatever is already on a shelf or in the depot).
 */
function migrateCatalog40(persistedState: unknown) {
	const state = { ...(persistedState as Partial<GameState>) };
	let refund = 0;
	const inventory = { ...(state.inventory ?? {}) } as GameInventory;
	const shelfStock = { ...(state.shelfStock ?? {}) } as GameShelfStock;
	const shelfAssignments = { ...(state.shelfAssignments ?? {}) } as GameShelfAssignments;
	for (const [id, price] of Object.entries(retiredProductRefunds)) {
		const productId = Number(id);
		refund += (inventory[productId] ?? 0) * price;
		delete inventory[productId];
		for (const [slotId, assigned] of Object.entries(shelfAssignments)) {
			if (assigned !== productId) continue;
			refund += (shelfStock[slotId] ?? 0) * price;
			shelfStock[slotId] = 0;
			shelfAssignments[slotId] = null;
		}
	}
	const market = state.market as Partial<GameMarketState> | undefined;
	const eraId = state.era?.id ?? "mesinha";
	const inUse = [
		...Object.entries(inventory).filter(([, quantity]) => (quantity ?? 0) > 0).map(([id]) => Number(id)),
		...Object.values(shelfAssignments).filter((id): id is number => typeof id === "number"),
	].filter((id) => itemCatalog.some((item) => item.id === id));
	return {
		...state,
		coins: (state.coins ?? 0) + refund,
		inventory,
		shelfStock,
		shelfAssignments,
		market: market
			? {
					...market,
					unlockedProductIds: Array.from(
						new Set([...getUnlockedProductIds(Math.max(1, market.level ?? 1), eraId), ...inUse]),
					),
					recentUnlockProductIds: [],
				}
			: market,
	} as Partial<GameState>;
}

/**
 * Version 41: fixtures open with the expansion that has room for them (src/data/shelf-types.ts). A save
 * whose market is smaller than a fixture loses it (its stock goes back to the depot, its price is kept),
 * and the products it can sell are the ones its expansion and level open, plus whatever is on a shelf it
 * still has.
 */
function migrateFixtures41(persistedState: unknown) {
	const state = { ...(persistedState as Partial<GameState>) };
	const eraId = state.era?.id ?? "mesinha";
	const counts = { ...(state.shelfSlotCounts ?? {}) } as GameShelfSlotCounts;
	const inventory = { ...(state.inventory ?? {}) } as GameInventory;
	const shelfStock = { ...(state.shelfStock ?? {}) } as GameShelfStock;
	const shelfAssignments = { ...(state.shelfAssignments ?? {}) } as GameShelfAssignments;
	const hasCounts = Object.keys(counts).length > 0;
	for (const shelf of shelfTypes) {
		const fits = getEraOrder(shelf.eraId) <= getEraOrder(eraId);
		if (fits) {
			// The starter fixtures always exist; the others keep what the save had.
			if (shelf.coinCost === 0 && hasCounts && !(counts[shelf.id] > 0)) counts[shelf.id] = initialUnlockedShelfSlots;
			continue;
		}
		if (hasCounts) counts[shelf.id] = 0;
		for (const slotId of getShelfSlotIds(shelf.id, maximumSlotsPerShelf)) {
			const productId = shelfAssignments[slotId];
			if (productId) inventory[productId] = (inventory[productId] ?? 0) + (shelfStock[slotId] ?? 0);
			shelfStock[slotId] = 0;
			shelfAssignments[slotId] = null;
		}
	}
	// A fixture the market does not have yet cannot wait in the build inventory either.
	const closed = new Set(
		shelfTypes.filter((shelf) => getEraOrder(shelf.eraId) > getEraOrder(eraId)).map((shelf) => `shelf:${shelf.id}`),
	);
	const interior = state.interior
		? { ...state.interior, items: (state.interior.items ?? []).filter((item) => !closed.has(item.id)) }
		: state.interior;
	const market = state.market as Partial<GameMarketState> | undefined;
	const onShelves = Object.values(shelfAssignments).filter((id): id is number => typeof id === "number");
	return {
		...state,
		interior,
		shelfSlotCounts: hasCounts ? counts : state.shelfSlotCounts,
		unlockedShelfSlots: hasCounts ? getTotalUnlockedShelfSlots(counts) : state.unlockedShelfSlots,
		inventory,
		shelfStock,
		shelfAssignments,
		market: market
			? {
					...market,
					unlockedProductIds: Array.from(
						new Set([...getUnlockedProductIds(Math.max(1, market.level ?? 1), eraId), ...onShelves]),
					),
				}
			: market,
	} as Partial<GameState>;
}

/** v49: the rewards of the tiers an old save already has, with one celebration when anything new opened. */
export function withMigratedTierRewards(state: GameState): GameState {
	const rewards = withTierRewards(state);
	if (rewards.newProducts.length === 0 && rewards.grantedPlaces.length === 0) return state;
	return {
		...state,
		shelfSlotCounts: rewards.shelfSlotCounts,
		unlockedShelfSlots: rewards.unlockedShelfSlots,
		market: { ...state.market, unlockedProductIds: rewards.unlockedProductIds },
		celebrations: rewards.newProducts.length
			? pushCelebration(state.celebrations, "tier", `unlocks:${rewards.newProducts.join(",")}`)
			: state.celebrations,
	};
}

function migrateGameState(persistedState: unknown): GameState {
	const state = persistedState as Partial<GameState>;
	const market = state.market as Partial<GameMarketState> | undefined;
	const normalizedLevel = Math.max(1, Math.floor(market?.level ?? 1));
	const shelfUpgradeLevels = {
		...initialGameState.shelfUpgradeLevels,
		...state.shelfUpgradeLevels,
	};
	const inventoryCapacityLevels = normalizeInventoryCapacityLevels(
		state.inventoryCapacityLevels,
	);
	const events = normalizeGameEventsState(
		state.events as Partial<GameEventsState> | undefined,
	);
	const employees = normalizeEmployeesState(state.employees);
	const shelfSlotCounts = normalizeShelfSlotCounts(
		state.shelfSlotCounts,
		state.unlockedShelfSlots,
	);
	// Every built sector sells at its own counter.
	for (const sectorId of state.builtSectorIds ?? []) {
		const counter = getSectorCounterFor(sectorId);
		if (counter && getShelfSlotCount(counter.id, shelfSlotCounts) <= 0)
			shelfSlotCounts[counter.id] = initialUnlockedShelfSlots;
	}
	const unlockedShelfSlots = getTotalUnlockedShelfSlots(shelfSlotCounts);
	const shelfAssignments = normalizeShelfAssignments(state.shelfAssignments);
	const normalizedShelfState = normalizeShelfState(
		{
			...initialGameState.shelfStock,
			...state.shelfStock,
		},
		{
			...initialGameState.inventory,
			...state.inventory,
		},
		{
			shelfUpgradeLevels,
			sectorTiers: normalizeSectorTiers(state.sectorTiers, productionSectors.map((sector) => sector.id)),
		},
		shelfSlotCounts,
		shelfAssignments,
	);
	const inventoryLots = normalizeInventoryLots(
		state.inventoryLots,
		normalizedShelfState.inventory,
	);
	const shelfLots = normalizeShelfLots(
		state.shelfLots,
		normalizedShelfState.shelfStock,
		shelfAssignments,
	);
	// Upgrades removed from the shop (src/data/shop-items.ts retiredShopItemIds) leave old saves.
	const knownShopItem = (id: string) => !retiredShopItemIds.includes(id);
	const shop = {
		...initialGameState.shop,
		...state.shop,
		activeBoosts: Object.fromEntries(
			Object.entries(state.shop?.activeBoosts ?? {}).filter(([id]) => knownShopItem(id)),
		),
		consumableAmounts: Object.fromEntries(
			Object.entries({
				...initialGameState.shop.consumableAmounts,
				...state.shop?.consumableAmounts,
			}).filter(([id]) => knownShopItem(id)),
		),
		ownedItemIds: withCheckoutRegister(
			(state.shop?.ownedItemIds ?? initialGameState.shop.ownedItemIds).filter(knownShopItem),
			(state as Partial<GameState>).era?.id ?? "mesinha",
		),
	};
	const shelfPrices = normalizeShelfPrices(state.shelfPrices, shelfAssignments);
	const production = {
		...initialGameState.production,
		...state.production,
		jobs: state.production?.jobs ?? initialGameState.production.jobs,
	};
	const missionsState = state.missions as
		| Partial<GameMissionsState>
		| undefined;
	const missions = {
		...initialGameState.missions,
		claimedMissionIds:
			missionsState?.claimedMissionIds ??
			initialGameState.missions.claimedMissionIds,
		reachedMissionIds: missionsState?.reachedMissionIds ?? [],
	};
	const statistics = {
		...initialGameState.statistics,
		...state.statistics,
	};
	const unlockedMarketExpansionIds = normalizeMarketExpansionIds(
		state.unlockedMarketExpansionIds,
	);
	const pendingConstruction = normalizeMarketExpansionConstruction(
		state.marketExpansionConstruction,
	);
	const marketExpansionConstruction =
		pendingConstruction &&
		!unlockedMarketExpansionIds.includes(pendingConstruction.expansionId)
			? pendingConstruction
			: null;
	const builtSectorIds = normalizeBuiltSectorIds(
		state.builtSectorIds,
		normalizedLevel,
	);
	// (v48: every sector built so far is T1; tiers only above it)
	const sectorTiers = normalizeSectorTiers(state.sectorTiers, productionSectors.map((sector) => sector.id));
	// (49: evolutions take time; the queue of the evolution crew)
	const evolutions = normalizeEvolutions(state.evolutions);
	const persistedShop = state.shop?.ownedItemIds ?? [];
	// Works that already finished (or whose target exists) are dropped.
	const interiorConstructions = normalizeInteriorConstructions(
		state.interiorConstructions,
	).filter((item) =>
		item.kind === "sector"
			? !builtSectorIds.includes(item.targetId as ProductionSectorId)
			: item.kind === "shop"
				? !persistedShop.includes(item.targetId)
				: getShelfSlotCount(item.targetId, shelfSlotCounts) <= 0,
	);
	const supplierOrderSlots = normalizeSupplierOrderSlots(
		state.logistics?.supplierOrderSlots,
	);
	const daily = normalizeDailyState(state.daily, normalizedLevel);
	const day = normalizeDayState(
		state.day,
		normalizedLevel,
		market?.isOpen === true,
	);
	const previousTotalRevenue =
		market?.totalRevenue ?? market?.todayRevenue ?? 0;
	const lastSessionAt =
		typeof state.lastSessionAt === "number" &&
		Number.isFinite(state.lastSessionAt)
			? state.lastSessionAt
			: Date.now();

	return {
		// Saves from before the eras (no "era" field) already have the market building.
		era: normalizeEraState(
			state.era,
			state.era ? "mesinha" : getEraForExpansions(unlockedMarketExpansionIds),
		),
		productLevels: normalizeProductLevels(state.productLevels),
		dailyLogin: normalizeDailyLoginState(state.dailyLogin),
		rewardedAds: normalizeRewardedAdsState(state.rewardedAds),
		weeklyEvent: normalizeWeeklyEventState(state.weeklyEvent),
		// Saves from before the land get the lots their expansion already stands on.
		lots: normalizeLotsState(
			state.lots,
			normalizeEraState(state.era, state.era ? "mesinha" : getEraForExpansions(unlockedMarketExpansionIds)).id,
		),
		celebrations: normalizeCelebrations(state.celebrations),
		albumClaimedIds: Array.isArray(state.albumClaimedIds)
			? state.albumClaimedIds.filter((id): id is string => typeof id === "string")
			: [],
		checkout: normalizeCheckoutCounterState(state.checkout),
		coins: state.coins ?? initialGameState.coins,
		currencyPurchases: {
			processedTransactionIds:
				state.currencyPurchases?.processedTransactionIds ??
				initialGameState.currencyPurchases.processedTransactionIds,
		},
		daily,
		day,
		events,
		employees,
		incidents: normalizeStoreIncidentsState(state.incidents),
		receiving: normalizeReceivingState(state.receiving),
		inventory: normalizedShelfState.inventory,
		inventoryLots,
		inventoryCapacityLevels,
		logistics: {
			emergencyTokens:
				state.logistics?.emergencyTokens ??
				initialGameState.logistics.emergencyTokens,
			freightCoupons:
				state.logistics?.freightCoupons ??
				initialGameState.logistics.freightCoupons,
			logisticsBoostExpiresAt:
				state.logistics?.logisticsBoostExpiresAt ??
				initialGameState.logistics.logisticsBoostExpiresAt,
			orders: state.logistics?.orders ?? initialGameState.logistics.orders,
			premiumCurrency:
				state.logistics?.premiumCurrency ??
				initialGameState.logistics.premiumCurrency,
			supplierOrderSlots,
		},
		market: {
			...initialGameState.market,
			...market,
			currentShift: market?.currentShift ?? null,
			lastShiftSummary: market?.lastShiftSummary ?? null,
			level: normalizedLevel,
			recentCustomers:
				market?.recentCustomers ?? initialGameState.market.recentCustomers,
			recentUnlockProductIds:
				market?.recentUnlockProductIds ??
				initialGameState.market.recentUnlockProductIds,
			experience: market?.experience ?? initialGameState.market.experience,
			customerSatisfaction:
				typeof market?.customerSatisfaction === "number"
					? Math.min(100, Math.max(0, market.customerSatisfaction))
					: initialGameState.market.customerSatisfaction,
			lastExperienceGain:
				market?.lastExperienceGain ??
				initialGameState.market.lastExperienceGain,
			todayRevenue: daily.revenue,
			totalRevenue: previousTotalRevenue,
			soldByProduct: {
				...initialGameState.market.soldByProduct,
				...market?.soldByProduct,
			},
			unlockedProductIds: Array.from(
				new Set([
					...getUnlockedProductIds(market?.level ?? 1, (state as Partial<GameState>).era?.id ?? "mesinha"),
					...(market?.unlockedProductIds ?? []),
				]),
			),
		},
		offlineSummary: state.offlineSummary ?? null,
		lastSessionAt,
		unlockedMarketExpansionIds,
		marketExpansionConstruction,
		interior: withCartStations(withCartsFromShop(normalizeInteriorState(state.interior), state.shop?.ownedItemIds), state.shop?.ownedItemIds),
		interiorConstructions,
		evolutions,
		builtSectorIds,
		sectorTiers,
		missions,
		production,
		shop,
		shelfAssignments,
		shelfLots,
		shelfStock: normalizedShelfState.shelfStock,
		shelfPrices,
		shelfSlotCounts,
		unlockedShelfSlots,
		shelfUpgradeLevels,
		shelfCare: normalizeShelfCare(state.shelfCare),
		statistics,
		delivery: normalizeDeliveryState(state.delivery),
		onboarding: normalizeOnboardingState(state.onboarding, {
			level: market?.level ?? 1,
			dayNumber: state.day?.dayNumber ?? 1,
			served: state.checkout?.served ?? 0,
		}),
		// 47: "Cores do mercado". Older saves (no field) keep the classic navy and gold.
		marketPaint: normalizeMarketPaintState(state.marketPaint),
		// 50: social v1. Older saves (no field) start with an empty slice; nothing else changes.
		social: normalizeSocialState(state.social),
		// Rankings v1 (no version bump): older saves (no field) start this week with no league points.
		rankings: normalizeRankingsState(state.rankings),
		// 51: Rede de supermercados (brand, distribution centre, fleet, contracts, branches). Older saves (no field)
		// get a fresh chain; a save already in the rede is asked to name it the next time the game opens.
		chain: normalizeChainState(state.chain),
	};
}

export const useGameStore = create<GameStore>()(
	persist(
		(rawSet, get) => {
			// Every level gained (sales, contracts, missions, the day's result...) leaves a celebration for the
			// HUD: the levels since the player last closed it (dismissLevelUp).
			const set = ((partial: unknown, replace?: boolean) => {
				const before = get().market.level;
				const phaseBefore = get().day?.phase;
				(rawSet as (partial: unknown, replace?: boolean) => void)(partial, replace);
				// Rankings v1: a day that just ended (closed by the clock or the button) gives its league points once:
				// the contract kept and the day's rating stars (docs/rankings-api.md).
				const ended = get().day;
				if (!replace && phaseBefore === "open" && ended?.phase === "results" && ended.result)
					rawSet({ rankings: addLeaguePoints(get().rankings, dayLeaguePoints(ended.result), Date.now()) });
				const market = get().market;
				if (!replace && market.level > before)
					rawSet({
						market: {
							...market,
							levelUp: {
								from: Math.min(market.levelUp?.from ?? before, before),
								to: market.level,
								at: Date.now(),
							},
						},
					});
			}) as typeof rawSet;
			// Spending diamonds: when the player has too few, the HUD opens the diamond store (Lucas 12/10) — the
			// shortfall is left here (not saved) for the host / app to react to (desktop/host.ts, use-simulator.ts).
			const enoughDiamonds = (needed: number) => {
				const have = get().logistics.premiumCurrency;
				if (have >= needed) return true;
				rawSet({ diamondShortfall: { needed, missing: needed - have, at: Date.now() } });
				return false;
			};

			return {
			...getInitialGameState(),
			dismissLevelUp: () => {
				if (get().market.levelUp) set({ market: { ...get().market, levelUp: null } });
			},
			// First-time onboarding (src/services/onboarding.ts): the host calls processOnboarding with the page on screen.
			processOnboarding: (route = "") => {
				const update = stepOnboarding(get(), route, Date.now());
				if (update) set(update);
				return Boolean(update);
			},
			onboardingNext: () => {
				const update = continueOnboarding(get(), Date.now());
				if (update) set(update);
				return Boolean(update);
			},
			skipOnboarding: () => {
				const update = skipOnboardingRule(get());
				if (update) set(update);
				return Boolean(update);
			},
			restartOnboarding: () => {
				set(restartOnboardingRule(get(), Date.now()));
				return true;
			},
			dismissOnboardingTip: () => {
				const update = dismissOnboardingTipRule(get());
				if (update) set(update);
				return Boolean(update);
			},
			dismissCelebration: (id) => {
				const list = get().celebrations ?? [];
				if (list.some((item) => item.id === id)) set({ celebrations: list.filter((item) => item.id !== id) });
			},
			claimDailyGoal: () => {
				const { coins, daily, market } = get();
				const normalizedDaily = normalizeDailyState(daily, market.level);

				if (!normalizedDaily.goalReached || normalizedDaily.claimed) {
					if (normalizedDaily.dayKey !== daily.dayKey) {
						set({ daily: normalizedDaily });
					}

					return false;
				}

				set({
					coins: coins + 300 + market.level * 75,
					daily: { ...normalizedDaily, claimed: true },
				});

				return true;
			},
			processSessionResume: () => {
				const state = get();
				const now = Date.now();
				const elapsedMs = Math.min(
					Math.max(0, now - state.lastSessionAt),
					8 * 60 * 60_000,
				);

				if (elapsedMs < 60_000) {
					set({ lastSessionAt: now });
					return false;
				}

				const daily = normalizeDailyState(state.daily, state.market.level, now);
				const shopEffects = getShopEffects(state.shop);
				// Obras keep going while the player is away.
				get().processMarketEraConstruction(now);
				// So does the evolution crew: what ended while away is applied now (its reveal waits for the player).
				get().processFixtureEvolutions(now);
				// The market keeps selling while the player is away (if it was left open): every hour
				// is worth part of a played turn, more in bigger eras (see data/economy.ts).
				const averageTicket =
					state.market.customersWhoBought > 0
						? state.market.totalRevenue / state.market.customersWhoBought
						: 18;
				// Only what is on the shelves sells: each offline customer takes one unit, so empty shelves sell
				// nothing (QA 16/10).
				const away = state.market.isOpen
					? getOfflineEraIncome(get().era, elapsedMs, averageTicket)
					: { coins: 0, customers: 0 };
				const shelfStock = { ...(state.shelfStock ?? {}) } as GameShelfStock;
				const stocked = Object.values(shelfStock).reduce((total, units) => total + Math.max(0, units ?? 0), 0);
				const customers = Math.min(away.customers, stocked);
				const soldShare = away.customers > 0 ? customers / away.customers : 0;
				const offlineCoins = Math.floor(
					away.coins * soldShare * shopEffects.offlineRevenueMultiplier,
				);
				// the units leave the fullest shelves first, one at a time
				for (let left = customers; left > 0; ) {
					const slots = Object.keys(shelfStock).filter((slot) => (shelfStock[slot] ?? 0) > 0);
					if (slots.length === 0) break;
					slots.sort((a, b) => (shelfStock[b] ?? 0) - (shelfStock[a] ?? 0));
					for (const slot of slots) {
						if (left <= 0) break;
						shelfStock[slot] = (shelfStock[slot] ?? 0) - 1;
						left--;
					}
				}
				const progression = applyExperience(
					state.market.level,
					state.market.experience,
					customers * 2,
				);
				const nextDaily = markDailySale(
					daily,
					offlineCoins,
					customers,
					customers,
				);

				set({
					coins: state.coins + offlineCoins,
					daily: nextDaily,
					shelfStock,
					// Offline sales stay out of the turn's stats: the contract counts what the player played.
					lastSessionAt: now,
					market: {
						...state.market,
						customersServed: state.market.customersServed + customers,
						customersWhoBought: state.market.customersWhoBought + customers,
						experience: progression.experience,
						level: progression.level,
						todayRevenue: nextDaily.revenue,
						totalExperience: state.market.totalExperience + customers * 2,
						totalRevenue: state.market.totalRevenue + offlineCoins,
						unitsSold: state.market.unitsSold + customers,
					},
					offlineSummary:
						customers > 0 || offlineCoins > 0
							? ({
									coins: offlineCoins,
									customers,
									durationMs: elapsedMs,
								} satisfies OfflineRewardSummary)
							: null,
				});

				get().processSupplierOrders();
				get().processProductionJobs();
				get().processInventorySpoilage();

				return customers > 0 || offlineCoins > 0;
			},
			dismissOfflineSummary: () => set({ offlineSummary: null }),
			activateLogisticsBoost: () => {
				const { logistics } = get();

				if (!enoughDiamonds(3)) {
					return false;
				}

				set({
					logistics: {
						...logistics,
						logisticsBoostExpiresAt: Date.now() + 15 * 60_000,
						premiumCurrency: logistics.premiumCurrency - 3,
					},
				});

				return true;
			},
			upgradeSupplierOrderSlots: (currency: SupplierOrderSlotCurrency) => {
				const { coins, logistics, market } = get();
				const nextUpgrade = getNextSupplierOrderSlotUpgrade(
					logistics.supplierOrderSlots,
				);

				if (!nextUpgrade || market.level < nextUpgrade.playerLevel) {
					return false;
				}

				if (
					(currency === "coins" && coins < nextUpgrade.coinCost) ||
					(currency === "diamonds" && !enoughDiamonds(nextUpgrade.diamondCost))
				) {
					return false;
				}

				set({
					coins: currency === "coins" ? coins - nextUpgrade.coinCost : coins,
					logistics: {
						...logistics,
						premiumCurrency:
							currency === "diamonds"
								? logistics.premiumCurrency - nextUpgrade.diamondCost
								: logistics.premiumCurrency,
						supplierOrderSlots: nextUpgrade.slots,
					},
				});

				return true;
			},
			// "Finalizar": the truck parks at the dock now, paid in diamonds for the time it still had to go (the same
			// price as every other speed-up, src/data/diamond-skip.ts).
			completeOrderFinalStage: (orderId) => {
				const { logistics, statistics } = get();
				const order = logistics.orders.find((item) => item.id === orderId);
				const now = Date.now();
				const cost = order ? getOrderSkipCost(order, now) : 0;

				if (!order || order.status === "entregue" || cost <= 0 || !enoughDiamonds(cost)) {
					return false;
				}

				set({
					logistics: {
						...logistics,
						orders: logistics.orders.map((item) =>
							item.id === orderId
								? { ...item, createdAt: now - item.deliveryDurationMs }
								: item,
						),
						premiumCurrency: logistics.premiumCurrency - cost,
					},
					statistics: {
						...statistics,
						instantDeliveries: statistics.instantDeliveries + 1,
					},
				});
				get().processSupplierOrders();

				return true;
			},
			claimAllMissions: () => {
				let claimed = false;
				for (const mission of missionList) claimed = get().claimMission(mission.id) || claimed;
				return claimed;
			},
			claimMission: (missionId) => {
				const state = get();
				const mission = getMission(missionId);

				if (
					!mission ||
					state.market.level < mission.requiredLevel ||
					state.missions.claimedMissionIds.includes(mission.id) ||
					(getMissionProgress(mission, state) < mission.goal &&
						!(state.missions.reachedMissionIds ?? []).includes(mission.id))
				) {
					return false;
				}

				// Products that don't fit in the stockroom (or aren't sold yet) come as coins instead: the
				// mission never gets stuck behind a full stockroom.
				const plan = getMissionRewardPlan(mission, state);
				const inventory = { ...state.inventory };
				const inventoryLots = { ...state.inventoryLots };
				for (const item of plan.stored) {
					inventory[item.productId] = (inventory[item.productId] ?? 0) + item.quantity;
					inventoryLots[item.productId] = appendInventoryLots(
						inventoryLots[item.productId],
						createInventoryLots(item.productId, item.quantity),
					);
				}

				set({
					coins: state.coins + plan.coins,
					inventory,
					inventoryLots,
					missions: {
						...state.missions,
						claimedMissionIds: [
							...state.missions.claimedMissionIds,
							mission.id,
						],
					},
				});

				return true;
			},
			// "Chegar já": the truck (every product of the order) parks at the dock right now, like a normal
			// arrival, so the boxes still go through the stockroom (unloadDelivery / the receiving mini-game).
			deliverOrderInstantly: (orderId) => {
				const { logistics, statistics } = get();
				const order = logistics.orders.find((item) => item.id === orderId);
				const now = Date.now();

				if (!order || order.status === "entregue") {
					return false;
				}

				// An emergency token first; otherwise diamonds for the time the truck still had to go.
				const canUseToken = logistics.emergencyTokens > 0;
				const cost = getOrderSkipCost(order, now);

				if (cost <= 0 || (!canUseToken && !enoughDiamonds(cost))) {
					return false;
				}

				set({
					logistics: {
						...logistics,
						emergencyTokens: canUseToken
							? logistics.emergencyTokens - 1
							: logistics.emergencyTokens,
						orders: logistics.orders.map((item) =>
							item.id === orderId
								? { ...item, createdAt: now - item.deliveryDurationMs }
								: item,
						),
						premiumCurrency: canUseToken
							? logistics.premiumCurrency
							: logistics.premiumCurrency - cost,
					},
					statistics: {
						...statistics,
						instantDeliveries: statistics.instantDeliveries + 1,
					},
				});
				get().processSupplierOrders();

				return true;
			},
			devAdjustCoins: (amount) => {
				if (!__DEV__) {
					return;
				}

				const { coins } = get();

				if (!Number.isFinite(amount)) {
					return;
				}

				set({ coins: Math.max(0, Math.floor(coins + amount)) });
			},
			devAdjustDiamonds: (amount) => {
				if (!__DEV__) {
					return;
				}

				const { logistics } = get();

				if (!Number.isFinite(amount)) {
					return;
				}

				set({
					logistics: {
						...logistics,
						premiumCurrency: Math.max(
							0,
							Math.floor(logistics.premiumCurrency + amount),
						),
					},
				});
			},
			devAdjustInventory: (productId, amount) => {
				if (!__DEV__) {
					return;
				}

				const product = itemCatalog.find((item) => item.id === productId);

				if (!product || !Number.isFinite(amount)) {
					return;
				}

				set((state) => ({
					inventory: {
						...state.inventory,
						[productId]: Math.max(
							0,
							Math.min(
								getInventoryCapacity(
									product,
									state.inventoryCapacityLevels[productId],
								),
								Math.floor((state.inventory[productId] ?? 0) + amount),
							),
						),
					},
				}));
			},
			devActivateGameEvent: (eventId) => {
				if (!__DEV__) {
					return false;
				}

				const { employees, events, market, shop } = get();
				const now = Date.now();
				const activated = activateGameEvent(events, eventId, now);

				if (!activated) {
					return false;
				}
				const nextEvents = withFeaturedProduct(activated, get());

				const eventEffects = getActiveGameEventEffects(nextEvents, now);
				const shopEffects = getShopEffects(shop);
				const employeeEffects = getEmployeeEffects(employees);

				set({
					events: nextEvents,
					market: market.isOpen
						? {
								...market,
								nextCustomerAt:
									now +
									getCustomerArrivalDelay(
										market.level,
										market.unlockedProductIds.length,
										market.randomSeed,
										shopEffects.customerArrivalMultiplier *
											eventEffects.customerArrivalMultiplier *
											employeeEffects.customerArrivalMultiplier *
								getTurnEffects(get().era.id, get().day.shift).customerArrivalMultiplier,
										getTurnEffects(get().era.id, get().day.shift).minArrivalDelayMs / shopEffects.customerCapacityMultiplier /
									// a busy event (payday, rush hour) brings more people than the shop's usual cap
									Math.max(1, eventEffects.customerArrivalMultiplier),
									),
							}
						: market,
				});

				return true;
			},
			// Test helpers: a truck at the dock right now, or a given mishap on a fitting shelf.
			devArriveDelivery: (productId, quantity = 30) => {
				if (!__DEV__) return false;
				const product = itemCatalog.find((item) => item.id === productId);
				if (!product || !Number.isFinite(quantity) || quantity <= 0) return false;
				const now = Date.now();
				// As much as the stockroom still takes (a full stockroom still gets the whole load).
				const room =
					getInventoryCapacity(product, get().inventoryCapacityLevels[productId]) -
					(get().inventory[productId] ?? 0);
				const units = Math.floor(room > 0 ? Math.min(quantity, room) : quantity);
				set({
					receiving: addDockDelivery(
						get().receiving,
						// Whole boxes, like a real order.
						{ id: `dev-${now}`, productId, quantity: Math.max(1, Math.round(units / product.caseSize)) * product.caseSize },
						{ category: product.category, name: product.name, caseSize: product.caseSize },
						now,
					),
				});
				return true;
			},
			// Sends away the test trucks (devArriveDelivery); real orders stay at the dock.
			evolveMarketEra: () => {
				const { coins, era } = get();
				const check = checkEraEvolution(era, coins, get().lots);
				if (!check.ok) return false;
				const now = Date.now();
				set({ coins: coins - check.next.coinCost, era: startEraEvolution(era, now) });
				get().processMarketEraConstruction(now);
				return true;
			},
			processMarketEraConstruction: (now = Date.now()) => {
				const { era } = get();
				const next = finishEraConstruction(era, now);
				if (next === era) return false;
				// Supermercado and hipermercado grow the building: their wings open with the obra.
				const unlockedMarketExpansionIds = getWingsForEra(next.id, get().unlockedMarketExpansionIds);
				const works = get().marketExpansionConstruction;
				const market = get().market;
				set({
					era: next,
					celebrations: pushCelebration(get().celebrations, "era", next.id),
					rankings: addLeaguePoints(get().rankings, LEAGUE_POINTS.build, Date.now()),
					// From the minimercado on the checkout the player places is already the register (T2).
					shop: { ...get().shop, ownedItemIds: withCheckoutRegister(get().shop.ownedItemIds, next.id) },
					// The new expansion brings its own products.
					market: {
						...market,
						unlockedProductIds: Array.from(
							new Set([...market.unlockedProductIds, ...getUnlockedProductIds(market.level, next.id)]),
						),
					},
					unlockedMarketExpansionIds,
					marketExpansionConstruction:
						works && unlockedMarketExpansionIds.includes(works.expansionId) ? null : works,
				});
				return true;
			},
			finishMarketEraNow: () => {
				const { era, logistics } = get();
				if (!era.construction) return false;
				const cost = getSkipDiamondCost(era.construction.endsAt - Date.now());
				if (!enoughDiamonds(cost)) return false;
				set({
					logistics: { ...logistics, premiumCurrency: logistics.premiumCurrency - cost },
				});
				return get().processMarketEraConstruction(Number.MAX_SAFE_INTEGER);
			},
			buyLot: (lotId: string) => {
				const lots = get().lots ?? createLotsState();
				const check = checkBuyLot(lots, get().coins, lotId);
				if (!check.ok) return false;
				set({ coins: get().coins - check.lot.price, lots: { ...lots, owned: [...lots.owned, lotId] } });
				return true;
			},
			clearLot: (lotId: string) => {
				const lots = get().lots ?? createLotsState();
				const check = checkClearLot(lots, get().coins, lotId);
				if (!check.ok) return false;
				const now = Date.now();
				set({ coins: get().coins - getLotClearCost(check.lot), lots: startLotClearing(lots, check.lot, now) });
				get().processLotClearing(now);
				return true;
			},
			finishLotClearingNow: () => {
				const lots = get().lots;
				if (!lots?.clearing) return false;
				const cost = getSkipDiamondCost(lots.clearing.endsAt - Date.now());
				if (!enoughDiamonds(cost)) return false;
				set({
					logistics: { ...get().logistics, premiumCurrency: get().logistics.premiumCurrency - cost },
				});
				return get().processLotClearing(Number.MAX_SAFE_INTEGER);
			},
			processLotClearing: (now = Date.now()) => {
				const lots = get().lots;
				if (!lots?.clearing) return false;
				const lot = getMarketLot(lots.clearing.lotId);
				const next = finishLotClearing(lots, now === Number.MAX_SAFE_INTEGER ? Number.MAX_SAFE_INTEGER : now);
				if (next === lots) return false;
				set({
					lots: next,
					celebrations: pushCelebration(get().celebrations, "lot", lots.clearing.lotId),
					rankings: addLeaguePoints(get().rankings, LEAGUE_POINTS.build, Date.now()),
				});
				// The crew sells the scrap: the cleared lot pays some experience.
				if (lot) {
					const xp = getLotClearExperience(lot);
					const market = get().market;
					const progression = applyExperience(market.level, market.experience, xp);
					set({
						market: {
							...market,
							experience: progression.experience,
							level: progression.level,
							lastExperienceGain: xp,
							totalExperience: market.totalExperience + xp,
							unlockedProductIds: Array.from(
								new Set([...market.unlockedProductIds, ...getUnlockedProductIds(progression.level, get().era.id)]),
							),
						},
					});
				}
				return true;
			},
			claimWeeklyEvent: () => {
				const now = Date.now();
				const weekly = syncWeeklyEvent(get().weeklyEvent, get().market.soldByProduct, now);
				const progress = getWeeklyProgress(weekly, get().market.soldByProduct, now);
				if (!progress.done || weekly.claimed) return false;
				const reward = getWeeklyReward(get().era.id);
				set({
					coins: get().coins + reward.coins,
					logistics: {
						...get().logistics,
						premiumCurrency: get().logistics.premiumCurrency + reward.diamonds,
					},
					weeklyEvent: { ...weekly, claimed: true },
				});
				return true;
			},
			claimAlbumCollection: (collectionId: string) => {
				const collection = albumCollections.find((item) => item.id === collectionId);
				const claimed = get().albumClaimedIds ?? [];
				if (!collection || claimed.includes(collectionId)) return false;
				if (!getCollectionProgress(collection, get().market.soldByProduct).complete) return false;
				set({
					coins: get().coins + collection.reward.coins,
					logistics: {
						...get().logistics,
						premiumCurrency: get().logistics.premiumCurrency + collection.reward.diamonds,
					},
					albumClaimedIds: [...claimed, collectionId],
				});
				return true;
			},
			claimDailyLoginBonus: (adId) => {
				const now = Date.now();
				const login = get().dailyLogin ?? createDailyLoginState();
				// The claimed gift not doubled yet (also when the video ends just after midnight).
				if (!login.lastClaimDay || login.bonusDay === login.lastClaimDay) return null;
				const ads = creditPlacementAd(get().rewardedAds, adId, now);
				if (!ads) return null;
				const reward = getLoginReward(login.streak || 1, get().era.id);
				set({
					coins: get().coins + reward.coins,
					logistics: { ...get().logistics, premiumCurrency: get().logistics.premiumCurrency + reward.diamonds },
					dailyLogin: { ...login, bonusDay: login.lastClaimDay },
					rewardedAds: ads,
				});
				return reward;
			},
			claimContractConsolation: (adId) => {
				const { day } = get();
				if (day.phase !== "results" || !canClaimConsolation(day.result) || !day.result) return null;
				const prize = rollConsolation(day.result, Math.random());
				const ads = prize ? creditPlacementAd(get().rewardedAds, adId) : null;
				if (!prize || !ads) return null;
				// Coins and diamonds now; the XP goes with the day's own XP when the result is collected.
				set({
					coins: get().coins + prize.coins,
					logistics: { ...get().logistics, premiumCurrency: get().logistics.premiumCurrency + prize.diamonds },
					rewardedAds: ads,
					day: {
						...day,
						result: {
							...day.result,
							consolation: prize,
							total: { ...day.result.total, experience: day.result.total.experience + prize.experience },
						},
					},
				});
				return prize;
			},
			claimDailyLogin: () => {
				const now = Date.now();
				const login = get().dailyLogin ?? createDailyLoginState();
				if (!canClaimDailyLogin(login, now)) return false;
				const day = getNextLoginDay(login, now);
				const reward = getLoginReward(day, get().era.id);
				set({
					coins: get().coins + reward.coins,
					logistics: {
						...get().logistics,
						premiumCurrency: get().logistics.premiumCurrency + reward.diamonds,
					},
					dailyLogin: { lastClaimDay: getDayKey(now), streak: day },
				});
				return true;
			},
			upgradeProduct: (productId: number) => {
				const product = itemCatalog.find((item) => item.id === productId);
				if (!product || !get().market.unlockedProductIds.includes(productId)) return false;
				const level = getProductLevel(get().productLevels, productId);
				const cost = getProductUpgradeCost(get().era.id, level);
				if (cost == null || get().coins < cost) return false;
				set({
					coins: get().coins - cost,
					productLevels: { ...(get().productLevels ?? {}), [productId]: level + 1 },
				});
				return true;
			},
			devSetMarketEra: (eraId: MarketEraId) => {
				if (getMarketEra(eraId).id !== eraId) return false;
				// DEV jumps also set the building wings of that expansion exactly (up or down), and give the
				// lots it stands on (bought and cleared).
				const lots = get().lots ?? createLotsState();
				const needed = ERA_LOTS[eraId] ?? [];
				set({
					lots: {
						owned: Array.from(new Set([...lots.owned, ...needed])),
						cleared: Array.from(new Set([...lots.cleared, ...needed])),
						clearing: lots.clearing && needed.includes(lots.clearing.lotId) ? null : lots.clearing,
					},
					era: { ...get().era, id: eraId, construction: null },
					shop: { ...get().shop, ownedItemIds: withCheckoutRegister(get().shop.ownedItemIds, eraId) },
					market: {
						...get().market,
						unlockedProductIds: Array.from(
							new Set([
								...get().market.unlockedProductIds,
								...getUnlockedProductIds(get().market.level, eraId),
							]),
						),
					},
					unlockedMarketExpansionIds: [...ERA_BUILDING_EXPANSIONS[eraId]],
					marketExpansionConstruction: null,
				});
				return true;
			},
			devAdvanceOrders: (progress: number) => {
				if (!Number.isFinite(progress) || progress <= 0 || progress >= 1) return false;
				const { logistics } = get();
				const now = Date.now();
				set({
					logistics: {
						...logistics,
						orders: logistics.orders.map((order) =>
							order.deliveredAt || (now - order.createdAt) / order.deliveryDurationMs >= progress
								? order
								: { ...order, createdAt: now - order.deliveryDurationMs * progress },
						),
					},
				});
				get().processSupplierOrders();
				return true;
			},
			devPassTime: (hours: number) => {
				if (!Number.isFinite(hours) || hours <= 0) return false;
				const shift = hours * 60 * 60_000;
				const { era, lastSessionAt } = get();
				// Everything that counts time from a timestamp moves back by the same amount.
				set({
					lastSessionAt: lastSessionAt - shift,
					era: era.construction
						? {
								...era,
								construction: {
									...era.construction,
									startedAt: era.construction.startedAt - shift,
									endsAt: era.construction.endsAt - shift,
								},
							}
						: era,
				});
				get().processSessionResume();
				get().processMarketEraConstruction();
				const lots = get().lots;
				if (lots?.clearing)
					set({ lots: { ...lots, clearing: { ...lots.clearing, endsAt: lots.clearing.endsAt - shift } } });
				get().processLotClearing();
				return true;
			},
			devFinishMarketExpansion: () => {
				if (!__DEV__) return false;
				return get().processMarketExpansionConstruction(Number.MAX_SAFE_INTEGER);
			},
			devClearDock: () => {
				if (!__DEV__) return false;
				const { receiving } = get();
				const dock = receiving.dock.filter((item) => !item.orderId?.startsWith("dev-"));
				if (dock.length === receiving.dock.length) return false;
				set({ receiving: { ...receiving, dock } });
				return true;
			},
			devTriggerIncident: (kind) => {
				if (!__DEV__) return false;
				const state = get().incidents;
				const shelves = getIncidentShelves(get());
				const now = Date.now();
				const level = get().market.level;
				// A fitting shelf when there is one (a cooler for cooler mishaps), else any shelf.
				const incident =
					createStoreIncident(state, shelves, now, level, kind) ??
					createStoreIncident(state, shelves, now, level, kind, true);
				if (!incident) return false;
				set({
					incidents: { ...state, active: [...state.active, incident], seed: state.seed + 1 },
				});
				return true;
			},
			finishProductionNow: (jobId) => {
				const {
					inventory,
					inventoryCapacityLevels,
					inventoryLots,
					logistics,
					production,
					statistics,
				} = get();
				const job = production.jobs.find((item) => item.id === jobId);

				if (!job) {
					return false;
				}

				const diamondCost = getProductionDiamondCost(job.endsAt - Date.now());

				if (
					!canAddToInventory(
						job.outputProductId,
						job.outputQuantity,
						inventory,
						inventoryCapacityLevels,
					) ||
					!enoughDiamonds(diamondCost)
				) {
					return false;
				}

				set({
					inventory: {
						...inventory,
						[job.outputProductId]:
							(inventory[job.outputProductId] ?? 0) + job.outputQuantity,
					},
					inventoryLots: {
						...inventoryLots,
						[job.outputProductId]: appendInventoryLots(
							inventoryLots[job.outputProductId],
							createInventoryLots(job.outputProductId, job.outputQuantity),
						),
					},
					logistics: {
						...logistics,
						premiumCurrency: logistics.premiumCurrency - diamondCost,
					},
					production: {
						jobs: production.jobs.filter((item) => item.id !== jobId),
						totalCrafted: production.totalCrafted + job.outputQuantity,
					},
					statistics: {
						...statistics,
						instantProductionFinishes: statistics.instantProductionFinishes + 1,
					},
				});

				return true;
			},
			hireEmployee: (role) => {
				const { coins, employees, market } = get();
				const definition = getEmployeeDefinition(role);

				if (
					!definition ||
					market.level < definition.level ||
					!isEmployeeEraReached(definition, get().era.id) ||
					coins < definition.hireCost
				) {
					return false;
				}

				const sameRoleCount = employees.employees.filter(
					(employee) => employee.role === role,
				).length;
				// One cashier per checkout (src/data/checkout-lanes.ts): a new cashier needs a counter to stand at.
				if (role === "cashier" && sameRoleCount >= getCheckoutCount(get().shop.ownedItemIds)) return false;

				set({
					coins: coins - definition.hireCost,
					employees: {
						employees: [
							...employees.employees,
							{
								efficiency: definition.efficiency,
								experience: 0,
								id: `${role}-${employees.nextHireNumber}`,
								isWorking: true,
								level: 1,
								name: `${definition.name} ${sameRoleCount + 1}`,
								role,
								salary: definition.salary,
							},
						],
						lastPayroll: employees.lastPayroll,
						nextHireNumber: employees.nextHireNumber + 1,
						nextPayrollAt: employees.nextPayrollAt,
						nextTaskNumber: employees.nextTaskNumber,
						tasks: employees.tasks,
						totalSalariesPaid: employees.totalSalariesPaid,
					},
				});

				return true;
			},
			// A rewarded video watched to the end (desktop/ads.ts checks it was the one the game asked for).
			claimRewardedAd: (adId) => {
				const result = rewardAd(get().rewardedAds, adId);
				if (result.diamonds <= 0) return null;
				set((current) => ({
					rewardedAds: result.state,
					logistics: { ...current.logistics, premiumCurrency: current.logistics.premiumCurrency + result.diamonds },
				}));
				return result.diamonds;
			},
			applySocialInbox: (items, now = Date.now()) => {
				const state = get();
				const { patch, outcomes, ack } = applyInboxItems(state, Array.isArray(items) ? items : [], now);
				if (Object.keys(patch).length) set(patch);
				return { outcomes, ack };
			},
			claimSocialHelperReward: (kind) => {
				const state = get();
				const reward = getSocialRewards(state.era.id)[kind === "help" ? "help" : "like"];
				const social = normalizeSocialState(state.social);
				const today = utcDay(Date.now());
				const daily = social.daily.day === today ? social.daily : { day: today, helps: 0 };
				set({
					coins: state.coins + reward,
					social:
						kind === "help"
							? { ...social, totals: { ...social.totals, helpsGiven: social.totals.helpsGiven + 1 }, daily: { day: today, helps: daily.helps + 1 } }
							: social,
					// Rankings v1: a help counted by the friends' server is a few league points.
					...(kind === "help" ? { rankings: addLeaguePoints(state.rankings, LEAGUE_POINTS.help, Date.now()) } : {}),
				});
				return reward;
			},
			openSocialMail: (ids) => {
				const result = openMailPatch(get(), ids);
				if (!result) return null;
				set(result.patch);
				return { coins: result.coins, count: result.count };
			},
			completeSocialDelivery: (productId, qty) => {
				// The friend already has it (server OK): whatever is in the stock room leaves, never refused now. The
				// page checked the stock before asking the server (canSendProduct).
				const result = sendProductPatch(get(), productId, qty);
				if (!result) return null;
				set(result.patch);
				return result.reward;
			},
			rememberSocialProfile: (profile) => {
				const social = normalizeSocialState(get().social);
				const next = {
					code: typeof profile.code === "string" ? profile.code : social.profile.code,
					marketName: typeof profile.marketName === "string" ? profile.marketName : profile.marketName === null ? "" : social.profile.marketName,
					avatar: typeof profile.avatar === "string" ? profile.avatar : social.profile.avatar,
				};
				if (next.code === social.profile.code && next.marketName === social.profile.marketName && next.avatar === social.profile.avatar) return false;
				set({ social: { ...social, profile: next } });
				return true;
			},
			rememberSocialRequests: (requests) => {
				const social = normalizeSocialState(get().social);
				const next = normalizeSocialState({ ...social, requests }).requests;
				if (JSON.stringify(next) === JSON.stringify(social.requests)) return false;
				set({ social: { ...social, requests: next } });
				return true;
			},
			setRankingSeenRanks: (seen) => {
				const rankings = normalizeRankingsState(get().rankings);
				const next = normalizeRankingsState({ ...rankings, seenRanks: seen }).seenRanks;
				if (JSON.stringify(next) === JSON.stringify(rankings.seenRanks)) return false;
				set({ rankings: { ...rankings, seenRanks: next } });
				return true;
			},
			setRankingOptOut: (optOut) => {
				const rankings = normalizeRankingsState(get().rankings);
				if (rankings.optOut === optOut) return false;
				set({ rankings: { ...rankings, optOut } });
				return true;
			},
			markLeaguePointsSent: (week, points, now = Date.now()) => {
				set({ rankings: markPointsSent(get().rankings, week, points, now) });
				return true;
			},
			applyLeagueWrongWeek: (week, now = Date.now()) => {
				set({ rankings: applyWrongWeek(get().rankings, week, now) });
				return true;
			},
			rolloverLeagueWeek: (now = Date.now()) => {
				const before = normalizeRankingsState(get().rankings);
				const next = addLeaguePoints(before, 0, now);
				if (next.week === before.week && get().rankings) return false;
				set({ rankings: next });
				return true;
			},
			dismissLeagueCard: (id) => {
				const rankings = normalizeRankingsState(get().rankings);
				const cards = id === "all" ? [] : rankings.cards.filter((card) => card.id !== id);
				if (cards.length === rankings.cards.length) return false;
				set({ rankings: { ...rankings, cards } });
				return true;
			},
			dismissDiamondShortfall: () => {
				if (get().diamondShortfall) rawSet({ diamondShortfall: null });
			},
			grantCurrencyPack: (packIdOrProductId, transactionId) => {
				const state = get();
				const pack = getCurrencyPack(packIdOrProductId);
				// A paid transaction is always credited (once): the welcome combo's "only once" is checked before the
				// store sheet opens (desktop/iap.ts requestPackPurchase), never after the player has paid.
				if (
					!pack ||
					!transactionId ||
					state.currencyPurchases.processedTransactionIds.includes(transactionId)
				) {
					return null;
				}
				const coins = getCurrencyPackCoins(pack, state.era?.id);
				const diamonds = pack.diamonds;
				set((current) => ({
					coins: current.coins + coins,
					currencyPurchases: {
						processedTransactionIds: [
							...current.currencyPurchases.processedTransactionIds.slice(-199),
							transactionId,
						],
						purchasedPackIds: [...(current.currencyPurchases.purchasedPackIds ?? []).slice(-499), pack.id],
					},
					logistics: {
						...current.logistics,
						premiumCurrency: current.logistics.premiumCurrency + diamonds,
					},
					// Whatever the player was short of is sorted: no store popping up again.
					diamondShortfall: null,
				}));
				return { packId: pack.id, coins, diamonds };
			},
			grantCurrencyPurchase: ({ coins, diamonds, transactionId }) => {
				const { currencyPurchases, logistics } = get();

				if (
					!transactionId ||
					currencyPurchases.processedTransactionIds.includes(transactionId) ||
					!Number.isFinite(coins) ||
					!Number.isFinite(diamonds) ||
					coins < 0 ||
					diamonds < 0
				) {
					return false;
				}

				set((state) => ({
					coins: state.coins + Math.floor(coins),
					currencyPurchases: {
						processedTransactionIds: [
							...currencyPurchases.processedTransactionIds.slice(-199),
							transactionId,
						],
					},
					logistics: {
						...logistics,
						premiumCurrency: logistics.premiumCurrency + Math.floor(diamonds),
					},
				}));

				return true;
			},
			// One truck carries a cart: several products, each in boxes (src/services/supplier-cart.ts).
			placeSupplierCart: (input) => {
				const now = Date.now();
				const { coins, logistics, statistics } = get();
				const quote = getSupplierCartQuote(get(), input, now);
				if (quote.reason) return false;
				const productId = quote.lines[0].productId;
				const order: SupplierOrder = {
					createdAt: now,
					deliveryDurationMs: quote.deliveryDurationMs,
					deliveredAt: null,
					// Two orders of the same product in the same millisecond still get their own truck.
					id: logistics.orders.some((item) => item.id === `${productId}-${now}`)
						? `${productId}-${now}-${logistics.orders.length}`
						: `${productId}-${now}`,
					productId,
					quantity: quote.units,
					boxes: quote.boxes,
					// A truck with one product keeps the unit size it always had.
					...(quote.lines.length === 1 ? { caseSize: quote.lines[0].caseSize } : {}),
					lines: quote.lines,
					status: "em-producao",
					totalCost: quote.total,
					...(quote.fleetTruckId ? { fleetTruckId: quote.fleetTruckId } : {}),
				};
				// Rede: the fleet truck is out until it unloads at the market and drives back to the centre.
				const chain = quote.fleetTruckId
					? withTruckJob(get().chain, quote.fleetTruckId, {
							kind: "abastecer",
							refId: order.id,
							departAt: now,
							arriveAt: now + quote.deliveryDurationMs,
							returnAt: now + Math.round(quote.deliveryDurationMs * (1 + FLEET_RETURN_SHARE)),
						})
					: get().chain;

				set({
					chain,
					coins: coins - quote.total,
					logistics: {
						...logistics,
						freightCoupons: quote.couponUsed
							? logistics.freightCoupons - 1
							: logistics.freightCoupons,
						orders: [order, ...logistics.orders].slice(0, 20),
					},
					statistics: {
						...statistics,
						supplierOrdersPlaced: statistics.supplierOrdersPlaced + 1,
					},
				});

				return true;
			},
			// The stepper pages order one product: a cart of one line.
			placeSupplierOrder: ({
				productId,
				boxes: requestedBoxes,
				quantity: requestedUnits,
				useFreightCoupon = false,
			}) => {
				const product = itemCatalog.find((item) => item.id === productId);
				// Suppliers sell whole boxes (src/data/case-sizes.ts): `boxes`, or the boxes that hold `quantity` units.
				const caseSize = product ? getCaseSize(product) : 1;
				const boxes = Math.floor(
					requestedBoxes ?? (requestedUnits !== undefined ? getBoxCount(requestedUnits, caseSize) : 0),
				);
				return get().placeSupplierCart({
					lines: [{ productId, boxes }],
					useFreightCoupon,
				});
			},
			purchaseShopItem: (itemId, currency) => {
				const { coins, logistics, market, shop, statistics } = get();
				const item = shopItems.find((shopItem) => shopItem.id === itemId);

				if (!item || market.level < item.level) {
					return false;
				}

				if (!item.isConsumable && shop.ownedItemIds.includes(item.id)) {
					return false;
				}

				if (item.requiresItemId && !shop.ownedItemIds.includes(item.requiresItemId)) {
					return false;
				}
				if (item.requiresExpansionId && !get().unlockedMarketExpansionIds.includes(item.requiresExpansionId)) {
					return false;
				}

				// Fixtures (second checkout, self-checkout) are installed by the builders, and only once the
				// market has room to place them.
				const roomEra = getShopItemPlaceEra(item.id);
				if (roomEra && getEraOrder(get().era.id) < getEraOrder(roomEra)) {
					return false;
				}
				const piece = getShopItemPieceId(item.id);
				if (piece && !hasInteriorRoom(piece)) {
					return false;
				}
				const installed = isBuiltShopItem(item.id);
				const interiorConstructions = get().interiorConstructions;
				// The checkout's steps evolve over time like every fixture (Lucas 01/11): the item joins when the crew is done.
				const checkoutTier = checkoutItemTiers[item.id] ?? 0;
				const evolvesCheckout = checkoutTier > getCheckoutTier(shop.ownedItemIds, get().era.id);
				if (evolvesCheckout && findEvolution(get().evolutions, "checkout", "checkout")) {
					return false;
				}
				if (installed && findInteriorConstruction(interiorConstructions, "shop", item.id)) {
					return false;
				}

				if (
					(currency === "coins" &&
						(!item.coinPrice || coins < item.coinPrice)) ||
					(currency === "diamonds" &&
						(!item.diamondPrice || !enoughDiamonds(item.diamondPrice)))
				) {
					return false;
				}

				set({
					coins: currency === "coins" ? coins - (item.coinPrice ?? 0) : coins,
					logistics:
						currency === "diamonds"
							? {
									...logistics,
									premiumCurrency:
										logistics.premiumCurrency - (item.diamondPrice ?? 0),
								}
							: logistics,
					shop: {
						...shop,
						consumableAmounts: item.isConsumable
							? {
									...shop.consumableAmounts,
									[item.id]: (shop.consumableAmounts[item.id] ?? 0) + 1,
								}
							: shop.consumableAmounts,
						ownedItemIds:
							item.isConsumable || installed || evolvesCheckout
								? shop.ownedItemIds
								: [...shop.ownedItemIds, item.id],
					},
					...(evolvesCheckout
						? {
								evolutions: enqueueEvolution(get().evolutions, {
									kind: "checkout",
									targetId: "checkout",
									toTier: checkoutTier,
									itemId: item.id,
									durationMs: getEvolutionDurationMs("checkout", "checkout", checkoutTier),
								}),
							}
						: {}),
					// Bought fixtures wait in the inventory until the player places them; works with no piece to
					// place (the cold room, outside the depot) start right away in the builders' queue.
					interiorConstructions: installed
						? (() => {
								const pending = createPendingConstruction("shop", item.id, shopItemBuildDurations[item.id]);
								const list = [...interiorConstructions, pending];
								return interiorPieceIds("shop", item.id).length > 0 ? list : placeInteriorConstruction(list, pending.id);
							})()
						: interiorConstructions,
					statistics: {
						...statistics,
						shopPurchases: statistics.shopPurchases + 1,
					},
				});

				return true;
			},
			activateShopBooster: (itemId) => {
				const { shop } = get();
				const item = shopItems.find((shopItem) => shopItem.id === itemId);
				if (!item?.isConsumable || !item.durationMs) return false;
				if ((shop.consumableAmounts[item.id] ?? 0) <= 0) return false;
				const now = Date.now();
				// Using one more while it runs adds its time to what is left. With the market closed it waits for the doors
				// to open (it only runs while customers come in).
				if (!get().market.isOpen) {
					set({
						shop: {
							...shop,
							pausedBoosts: { ...(shop.pausedBoosts ?? {}), [item.id]: (shop.pausedBoosts?.[item.id] ?? 0) + item.durationMs },
							consumableAmounts: { ...shop.consumableAmounts, [item.id]: (shop.consumableAmounts[item.id] ?? 0) - 1 },
						},
					});
					return true;
				}
				const endsAt = Math.max(now, shop.activeBoosts?.[item.id] ?? 0) + item.durationMs;
				set({
					shop: {
						...shop,
						activeBoosts: { ...shop.activeBoosts, [item.id]: endsAt },
						consumableAmounts: {
							...shop.consumableAmounts,
							[item.id]: (shop.consumableAmounts[item.id] ?? 0) - 1,
						},
					},
				});
				return true;
			},
			processGameEvents: () => {
				const state = get();
				const { day, events } = state;
				const now = Date.now();
				// Only events that make sense for this market are drawn (expansion, team, fridges).
				const scheduled = advanceGameEvents(
					events,
					now,
					{
						endsAt: day.endsAt ?? 0,
						key: getTurnEventKey(day),
						open: day.phase === "open" && day.endsAt !== null,
						startedAt: day.startedAt ?? now,
					},
					getAvailableGameEvents(getGameEventContext(state)),
				);
				let nextEvents = scheduled ?? events;
				let shelfCare = state.shelfCare;
				let coins = state.coins;
				let market = state.market;

				// A new event: Viralizou! picks the product in the video.
				if (nextEvents.activeEvent && nextEvents.activeEvent !== events.activeEvent)
					nextEvents = withFeaturedProduct(nextEvents, state);

				// Time-based wear while the event runs (wilting produce, thawing freezers), every few seconds.
				const running = nextEvents.activeEvent;
				const runningEffects = getActiveGameEventEffects(nextEvents, now);
				if (running && runningEffects.passiveWear) {
					const elapsed = Math.min(now, running.endsAt) - (nextEvents.wearTickAt ?? running.startedAt);
					if (elapsed >= PASSIVE_WEAR_TICK_MS) {
						shelfCare = applyPassiveEventWear(
							shelfCare,
							runningEffects,
							getEventFixtures(state, runningEffects.powerOutage),
							elapsed,
						);
						nextEvents = { ...nextEvents, wearTickAt: now };
					}
				}

				// What the player does during the event: the inspector's checklist (each stop is a real mishap to fix
				// in time) and drinks asked through car windows in the jam (src/services/event-interactions.ts).
				let incidents = state.incidents;
				const interaction = running ? runningEffects.interaction : null;
				if (running && interaction === "inspection") {
					let run =
						nextEvents.inspection && nextEvents.inspection.startedAt === running.startedAt
							? nextEvents.inspection
							: createInspectionRun(running.startedAt, running.endsAt);
					const step = advanceInspection(run, now, incidents.active);
					run = step.run;
					if (step.needsIncident) {
						const shelves = getIncidentShelves(state);
						let incident = null;
						for (const kind of pickInspectionKind(run, true, nextEvents.randomSeed + run.stops.length + incidents.seed)) {
							incident = createStoreIncident(incidents, shelves, now, state.market.level, kind);
							if (incident) break;
						}
						if (incident) incidents = { ...incidents, active: [...incidents.active, incident], seed: incidents.seed + 1 };
						run = openInspectionStop(run, step.needsIncident.id, incident, now);
					}
					if (run !== nextEvents.inspection) nextEvents = { ...nextEvents, inspection: run };
				}
				if (running && interaction === "window-sales") {
					const sales = nextEvents.windowSales ?? createWindowSales(running.startedAt);
					const drinks = state.market.unlockedProductIds.filter((productId) =>
						WINDOW_CATEGORIES.includes(itemCatalog.find((item) => item.id === productId)?.category ?? ""),
					);
					const advanced = advanceWindowSales(sales, now, drinks, running.endsAt);
					if (advanced !== nextEvents.windowSales) nextEvents = { ...nextEvents, windowSales: advanced };
				}

				// The event that just ended may leave something behind: the inspector's verdict, the jam's sales.
				const ended = events.activeEvent && !nextEvents.activeEvent ? events.activeEvent : null;
				const endedInteraction = ended ? (getGameEvent(ended.eventId)?.effects.interaction ?? null) : null;
				if (ended && endedInteraction === "inspection" && events.inspection) {
					const run = advanceInspection(events.inspection, now, incidents.active).run;
					const result = scoreInspection(run, state.daily.goal);
					coins = Math.max(0, coins + result.coins);
					market = {
						...market,
						customerSatisfaction: Math.max(0, Math.min(100, market.customerSatisfaction + result.reputation)),
					};
					nextEvents = {
						...nextEvents,
						inspection: null,
						sealTurnKey: result.grade === "approved" ? (ended.turnKey ?? getTurnEventKey(day)) : nextEvents.sealTurnKey ?? null,
						outcome: {
							at: now,
							eventId: ended.eventId,
							kind: result.grade === "fined" ? "negative" : "positive",
							text:
								result.grade === "approved"
									? `Fiscal aprovou o mercado: ${result.passed}/${result.total} resolvidos (+${result.coins} moedas, +${result.reputation} de reputação)`
									: result.grade === "warning"
										? `Advertência do fiscal: ${result.passed}/${result.total} resolvidos`
										: `Multa do fiscal: ${result.passed}/${result.total} resolvidos (${result.coins} moedas)`,
						},
					};
				} else if (ended && endedInteraction === "window-sales" && events.windowSales) {
					const sold = events.windowSales.served;
					nextEvents = {
						...nextEvents,
						windowSales: null,
						outcome: {
							at: now,
							eventId: ended.eventId,
							kind: "positive",
							text:
								sold === 0
									? "Nenhuma bebida vendida pela janela desta vez"
									: sold === 1
										? "Você vendeu 1 bebida pela janela"
										: `Você vendeu ${sold} bebidas pela janela`,
						},
					};
				}

				if (nextEvents === events && shelfCare === state.shelfCare && incidents === state.incidents) return false;

				// Starting or ending an event changes how often customers come.
				if (scheduled && market.isOpen) {
					const eventEffects = getActiveGameEventEffects(nextEvents, now);
					const shopEffects = getShopEffects(state.shop);
					const employeeEffects = getEmployeeEffects(state.employees);
					const turnEffects = getTurnEffects(state.era.id, state.day.shift);
					market = {
						...market,
						nextCustomerAt:
							now +
							getCustomerArrivalDelay(
								market.level,
								market.unlockedProductIds.length,
								market.randomSeed,
								shopEffects.customerArrivalMultiplier *
									eventEffects.customerArrivalMultiplier *
									employeeEffects.customerArrivalMultiplier *
									turnEffects.customerArrivalMultiplier,
								turnEffects.minArrivalDelayMs / shopEffects.customerCapacityMultiplier /
									// a busy event (payday, rush hour) brings more people than the shop's usual cap
									Math.max(1, eventEffects.customerArrivalMultiplier),
							),
					};
				}

				set({ coins, events: nextEvents, incidents, market, shelfCare });

				return true;
			},
			// Stock clerks and cleaners work job by job (src/services/staff-work.ts): a finished trip puts its
			// box on the shelf, a finished fix clears the mishap; then everyone free gets the next job.
			processEmployeeWork: () => {
				const now = Date.now();
				let changed = false;
				const finished = takeFinishedStaffTasks(get().employees.tasks ?? [], now);
				if (finished.done.length > 0) {
					set({ employees: { ...get().employees, tasks: finished.tasks } });
					changed = true;
					for (const task of finished.done) {
						let worked = false;
						if (task.kind === "restock") {
							const state = get();
							const capacity = getSlotCapacity(state, task.slotId);
							const amount = Math.min(
								task.units,
								state.inventory[task.productId] ?? 0,
								capacity - (state.shelfStock[task.slotId] ?? 0),
							);
							worked =
								amount > 0 &&
								get().restockShelf({
									amount,
									productId: task.productId,
									shelfId: task.slotId,
								});
						} else {
							const fixed = fixStoreIncident(
								get().incidents,
								task.incidentId,
								now,
								"staff",
							);
							if (fixed) {
								set({ incidents: fixed.state });
								worked = true;
							}
						}
						if (worked)
							set({
								employees: {
									...get().employees,
									employees: get().employees.employees.map((employee) =>
										employee.id === task.employeeId
											? grantEmployeeExperience(employee, 1)
											: employee,
									),
								},
							});
					}
				}
				const state = get();
				const plan = planStaffTasks({
					employees: state.employees.employees,
					incidents: state.incidents.active,
					isOpen: state.market.isOpen && state.day.phase === "open",
					nextTaskNumber: state.employees.nextTaskNumber ?? 1,
					now,
					restockMultiplier: getShopEffects(state.shop).restockMultiplier,
					speedMultiplier: getActiveGameEventEffects(state.events, now).staffSpeedMultiplier,
					slots: getRestockCandidates(state),
					storage: getStaffStorageKind(
						getSimulatorLayout(state.unlockedMarketExpansionIds),
					),
					tasks: state.employees.tasks ?? [],
				});
				if (
					plan.started.length > 0 ||
					plan.tasks.length !== (state.employees.tasks ?? []).length
				) {
					set({
						employees: {
							...state.employees,
							nextTaskNumber: plan.nextTaskNumber,
							tasks: plan.tasks,
						},
					});
					changed = true;
				}
				return changed;
			},
			// Salaries are paid per shift when the market closes (setMarketOpen). Kept for old callers.
			processEmployeePayroll: () => false,
			processInventorySpoilage: () => {
				const {
					inventory,
					inventoryLots,
					shelfAssignments,
					shelfLots,
					shelfStock,
					statistics,
				} = get();
				const now = Date.now();
				const nextInventory = { ...inventory };
				const nextInventoryLots: GameInventoryLots = { ...inventoryLots };
				const nextShelfStock = { ...shelfStock };
				const nextShelfLots: GameShelfLots = { ...shelfLots };
				let spoiledUnits = 0;
				let hasLotChanges = false;

				for (const [productId, quantity] of Object.entries(inventory)) {
					const numericProductId = Number(productId);
					const lots = reconcileInventoryLots(
						numericProductId,
						quantity,
						inventoryLots[numericProductId],
						now,
					);
					const discarded = discardExpiredInventoryLots(lots, now);
					nextInventoryLots[numericProductId] = discarded.remainingLots;
					hasLotChanges ||=
						JSON.stringify(inventoryLots[numericProductId] ?? []) !==
						JSON.stringify(discarded.remainingLots);

					if (discarded.expiredQuantity > 0) {
						nextInventory[numericProductId] = Math.max(
							0,
							quantity - discarded.expiredQuantity,
						);
						spoiledUnits += discarded.expiredQuantity;
					}
				}

				for (const [shelfId, quantity] of Object.entries(shelfStock)) {
					const productId = shelfAssignments[shelfId];
					if (!productId || quantity <= 0) {
						continue;
					}

					const lots = reconcileInventoryLots(
						productId,
						quantity,
						shelfLots[shelfId],
						now,
					);
					const discarded = discardExpiredInventoryLots(lots, now);
					nextShelfLots[shelfId] = discarded.remainingLots;
					hasLotChanges ||=
						JSON.stringify(shelfLots[shelfId] ?? []) !==
						JSON.stringify(discarded.remainingLots);

					if (discarded.expiredQuantity > 0) {
						nextShelfStock[shelfId] = Math.max(
							0,
							quantity - discarded.expiredQuantity,
						);
						spoiledUnits += discarded.expiredQuantity;
					}
				}

				if (spoiledUnits === 0 && !hasLotChanges) {
					return false;
				}

				set({
					inventory: nextInventory,
					inventoryLots: nextInventoryLots,
					shelfLots: nextShelfLots,
					shelfStock: nextShelfStock,
					statistics: {
						...statistics,
						spoiledUnits: statistics.spoiledUnits + spoiledUnits,
					},
				});

				return true;
			},
			processProductionJobs: () => {
				const {
					inventory,
					inventoryCapacityLevels,
					inventoryLots,
					production,
				} = get();
				const now = Date.now();
				const nextInventory = { ...inventory };
				const nextInventoryLots: GameInventoryLots = { ...inventoryLots };
				let craftedQuantity = 0;
				const remainingJobs: ProductionJob[] = [];

				for (const job of production.jobs) {
					if (
						job.endsAt > now ||
						!canAddToInventory(
							job.outputProductId,
							job.outputQuantity,
							nextInventory,
							inventoryCapacityLevels,
						)
					) {
						remainingJobs.push(job);
						continue;
					}

					nextInventory[job.outputProductId] =
						(nextInventory[job.outputProductId] ?? 0) + job.outputQuantity;
					nextInventoryLots[job.outputProductId] = appendInventoryLots(
						nextInventoryLots[job.outputProductId],
						createInventoryLots(job.outputProductId, job.outputQuantity, now),
					);
					craftedQuantity += job.outputQuantity;
				}

				if (craftedQuantity === 0) {
					return false;
				}

				set({
					inventory: nextInventory,
					inventoryLots: nextInventoryLots,
					production: {
						jobs: remainingJobs,
						totalCrafted: production.totalCrafted + craftedQuantity,
					},
				});

				return true;
			},
			processSupplierOrders: () => {
				const { logistics } = get();
				const now = Date.now();
				let hasChanges = false;
				// A delivered order parks its truck at the dock; the goods only become stock once
				// someone unloads them (unloadDelivery / a stock clerk).
				let nextReceiving = get().receiving;
				const orders = logistics.orders.map((order) => {
					if (order.status === "entregue") {
						return order;
					}

					const status = getSupplierOrderStatus(order, now);

					if (status === "entregue") {
						hasChanges = true;
						// The truck parks with one dock delivery per product on it. Orders from before carts keep
						// their old delivery (its units split as before, see getDeliveryBoxUnits).
						const cart = (order.lines?.length ?? 0) > 0;
						for (const line of getOrderLines(order)) {
							const product = itemCatalog.find((item) => item.id === line.productId);
							nextReceiving = addDockDelivery(
								nextReceiving,
								{
									id: order.id,
									productId: line.productId,
									quantity: line.quantity,
									caseSize: cart ? line.caseSize : order.caseSize,
								},
								{ category: product?.category ?? "", name: product?.name ?? "Produto" },
								now,
								cart ? `${order.id}:${line.productId}` : undefined,
							);
						}
						return { ...order, deliveredAt: now, status };
					}

					if (status !== order.status) {
						hasChanges = true;
						return { ...order, status };
					}

					return order;
				});

				if (!hasChanges) {
					return false;
				}

				set({
					logistics: { ...logistics, orders },
					receiving: nextReceiving,
				});

				return true;
			},
			// Moves up to `units` from a truck at the dock into the stockroom (as much as fits).
			unloadDelivery: (deliveryId, units) => {
				const state = get();
				const delivery = state.receiving.dock.find((item) => item.id === deliveryId);
				const product = delivery
					? itemCatalog.find((item) => item.id === delivery.productId)
					: undefined;
				if (!delivery || !product) return false;
				// Boxes go onto free places on the racks; older deliveries (no boxes) only need units of room.
				const room = delivery.caseSize
					? getStockroomRoom(product, state.inventory[product.id] ?? 0, state.inventoryCapacityLevels[product.id])
					: getInventoryCapacity(product, state.inventoryCapacityLevels[product.id]) -
						(state.inventory[product.id] ?? 0);
				const now = Date.now();
				const result = unloadDock(
					state.receiving,
					deliveryId,
					units ?? delivery.quantity,
					room,
				);
				if (!result) return false;
				set({
					inventory: {
						...state.inventory,
						[product.id]: (state.inventory[product.id] ?? 0) + result.moved,
					},
					inventoryLots: {
						...state.inventoryLots,
						[product.id]: appendInventoryLots(
							state.inventoryLots[product.id],
							createInventoryLots(product.id, result.moved, now),
						),
					},
					lastSessionAt: now,
					receiving: result.state,
				});
				return true;
			},
			orderLowStock: (via) => {
				// Emptiest first, so the products about to run out get the trucks.
				const fleet = via === "frota";
				const state = get();
				const now = Date.now();
				const low = itemCatalog
					.filter(
						(product) =>
							product.acquisition === "supplier" &&
							(fleet || !product.privateLabel) &&
							state.market.unlockedProductIds.includes(product.id),
					)
					.map((product) => ({
						product,
						share:
							(state.inventory[product.id] ?? 0) /
							Math.max(1, getInventoryCapacity(product, state.inventoryCapacityLevels[product.id])),
					}))
					.filter((item) => item.share < LOW_STOCK_SHARE)
					.sort((a, b) => a.share - b.share);
				// One truck: every low product gets the most boxes that still fit the truck, the racks and the coins.
				const maxBoxes = fleet ? DC_MAX_BOXES : getMaxBoxesPerOrder(state.logistics.supplierOrderSlots);
				const lines: PlaceSupplierCartInput["lines"] = [];
				let boxes = 0;
				for (const { product } of low) {
					if (boxes >= maxBoxes) break;
					const fits = (count: number) =>
						getSupplierCartQuote(
							state,
							{ lines: [...lines, { productId: product.id, boxes: count }], ...(fleet ? { via: "frota" as const } : {}) },
							now,
						).reason === null;
					const free = getFreeBoxPlaces(
						product,
						state.inventory[product.id] ?? 0,
						state.inventoryCapacityLevels[product.id],
						getSupplierIncoming(state, product.id, now).units,
					);
					// Binary search: the most boxes of this product that the cart still takes.
					let most = 0;
					let high = Math.min(free, maxBoxes - boxes);
					while (most < high) {
						const next = Math.ceil((most + high) / 2);
						if (fits(next)) most = next;
						else high = next - 1;
					}
					if (most > 0) {
						lines.push({ productId: product.id, boxes: most });
						boxes += most;
					}
				}
				return lines.length > 0 && get().placeSupplierCart({ lines, ...(fleet ? { via: "frota" as const } : {}) });
			},
			unloadAllDeliveries: () => {
				let moved = false;
				for (const delivery of [...get().receiving.dock])
					moved = get().unloadDelivery(delivery.id, delivery.quantity) || moved;
				return moved;
			},
			// Working stock clerks unload the trucks box by box on their own.
			processReceiving: () => {
				const efficiency = get()
					.employees.employees.filter(
						(employee) => employee.isWorking && employee.role === "stock_clerk",
					)
					.reduce((total, employee) => total + employee.efficiency, 0);
				const step = nextStaffUnload(get().receiving, Date.now(), efficiency);
				if (step.state !== get().receiving) set({ receiving: step.state });
				if (!step.box) return false;
				return get().unloadDelivery(step.box.deliveryId, step.box.units);
			},
			// Delivery (src/services/delivery.ts): online orders the player packs and hands to a motoboy.
			processDelivery: (now = Date.now()) => {
				const state = get();
				const start = state.delivery;
				let coins = state.coins;
				let market = state.market;
				let streak = start.streak;
				let bestStreak = start.bestStreak;
				let rating = start.rating;
				let ratings = start.ratings;
				let delivered = start.delivered;
				let earnings = start.earnings;
				let ordersChanged = false;
				const orders: DeliveryOrder[] = start.orders.map((order) => {
					let next = advanceDeliveryOrder(order, now);
					if (order.status === "aceito" && next.status === "cancelado") {
						rating = applyLateCancelToRating(rating);
						streak = 0;
					}
					if (isDeliveryArrived(next, now)) {
						const settlement = settleDelivery(next, streak);
						coins += settlement.total;
						earnings += settlement.total;
						delivered += 1;
						streak = settlement.stars >= 5 ? streak + 1 : 0;
						bestStreak = Math.max(bestStreak, streak);
						rating = applyStarsToRating(rating, settlement.stars);
						ratings = pushRating(ratings, settlement.stars);
						market = creditDeliverySales(market, state.era.id, next.packed ?? [], settlement.goods);
						next = {
							...next,
							status: "entregue",
							tip: settlement.tip,
							bonus: settlement.bonus,
							paid: settlement.total,
						};
					}
					if (next !== order) ordersChanged = true;
					return next;
				});

				// Offers come in waves while the market is open (and the app is unlocked): one wave every
				// 75–150 s, at most MAX_WAITING_OFFERS waiting at a time.
				let seed = start.seed;
				let nextOfferAt = start.nextOfferAt;
				let all = orders;
				if (state.market.isOpen && isDeliveryUnlocked(state.era.id)) {
					const rush = getActiveGameEventEffects(state.events, now).customerArrivalMultiplier;
					if (nextOfferAt === null) {
						nextOfferAt = now + getOfferIntervalMs(rating, createDeliveryRandom(seed), rush);
						seed += 1;
					} else if (now >= nextOfferAt) {
						const random = createDeliveryRandom(seed);
						seed += 1;
						const waiting = orders.filter((order) => order.status === "oferta").length;
						if (waiting < MAX_WAITING_OFFERS) {
							const offer = createDeliveryOffer({
								id: getNextOrderId(now, orders),
								now,
								random,
								stock: getDeliveryStock(state),
							});
							if (offer) all = [...orders, offer];
						}
						nextOfferAt = now + getOfferIntervalMs(rating, random, rush);
					}
				}

				const trimmed = trimDeliveryOrders(all);
				const changed =
					ordersChanged || trimmed.length !== start.orders.length || nextOfferAt !== start.nextOfferAt;
				if (!changed) return false;
				set({
					coins,
					market,
					delivery: {
						...start,
						orders: trimmed,
						nextOfferAt,
						rating,
						ratings,
						streak,
						bestStreak,
						delivered,
						earnings,
						seed,
					},
				});
				return true;
			},
			acceptDeliveryOrder: (orderId, now = Date.now()) => {
				const state = get();
				const { delivery } = state;
				const order = delivery.orders.find((item) => item.id === orderId);
				if (!order || order.status !== "oferta" || now >= order.expiresAt) return false;
				if (!isDeliveryUnlocked(state.era.id)) return false;
				if (delivery.orders.filter(isActiveDeliveryOrder).length >= getDeliverySlots(state.era.id)) return false;
				set({
					delivery: {
						...delivery,
						orders: trimDeliveryOrders(
							replaceDeliveryOrder(delivery.orders, {
								...order,
								status: "aceito",
								acceptedAt: now,
								packBy: now + PACK_WINDOW_MS,
							}),
						),
					},
				});
				return true;
			},
			declineDeliveryOrder: (orderId) => {
				const { delivery } = get();
				const order = delivery.orders.find((item) => item.id === orderId);
				if (!order || order.status !== "oferta") return false;
				set({
					delivery: {
						...delivery,
						orders: trimDeliveryOrders(replaceDeliveryOrder(delivery.orders, { ...order, status: "recusado" })),
					},
				});
				return true;
			},
			packDeliveryOrder: (orderId, result, now = Date.now()) => {
				const state = get();
				const { delivery } = state;
				const order = delivery.orders.find((item) => item.id === orderId);
				if (!order || order.status !== "aceito") return false;
				if (order.packBy !== undefined && now >= order.packBy) {
					set({ delivery: cancelLateDelivery(delivery, order) });
					return false;
				}
				// Only what the stockroom holds leaves with the bag (missing units are allowed).
				const packed = clampPackedItems(order, result.items, (productId) => state.inventory[productId] ?? 0);
				const inventory = { ...state.inventory };
				const inventoryLots = { ...state.inventoryLots };
				for (const item of packed) {
					const stored = state.inventory[item.productId] ?? 0;
					inventory[item.productId] = stored - item.quantity;
					inventoryLots[item.productId] = takeInventoryLots(
						reconcileInventoryLots(item.productId, stored, state.inventoryLots[item.productId], now),
						item.quantity,
					).remainingLots;
				}
				const random = createDeliveryRandom(delivery.seed);
				const quality = Math.min(1, Math.max(0, Number(result.quality) || 0));
				const fillRatio = getFillRatio(order.items, packed);
				const packedOrder: DeliveryOrder = {
					...order,
					status: "aguardando-moto",
					packed,
					fillRatio,
					quality,
					stars: getPackStars({ fillRatio, quality, seconds: Math.max(0, Number(result.seconds) || 0) }),
					itemsValue: getItemsValue(order.items, (productId) => getDeliveryPrice(state, productId)),
					packedAt: now,
					courier: assignCourier(random, now),
				};
				set({
					inventory,
					inventoryLots,
					delivery: {
						...delivery,
						orders: trimDeliveryOrders(replaceDeliveryOrder(delivery.orders, packedOrder)),
						seed: delivery.seed + 1,
					},
				});
				return true;
			},
			handOverDelivery: (orderId, now = Date.now()) => {
				const { delivery } = get();
				const order = delivery.orders.find((item) => item.id === orderId);
				if (!order || order.status !== "moto-na-porta") return false;
				set({
					delivery: {
						...delivery,
						orders: trimDeliveryOrders(replaceDeliveryOrder(delivery.orders, handOverOrder(order, now))),
					},
				});
				return true;
			},
			devSpawnDeliveryOffer: (now = Date.now()) => {
				const state = get();
				const { delivery } = state;
				if (!isDeliveryUnlocked(state.era.id)) return false;
				const offer = createDeliveryOffer({
					id: getNextOrderId(now, delivery.orders),
					now,
					random: createDeliveryRandom(delivery.seed),
					stock: getDeliveryStock(state),
				});
				if (!offer) return false;
				set({
					delivery: {
						...delivery,
						orders: trimDeliveryOrders([...delivery.orders, offer]),
						seed: delivery.seed + 1,
					},
				});
				return true;
			},
			startProduction: ({ recipeId, sectorId }) => {
				const {
					events,
					inventory,
					inventoryCapacityLevels,
					market,
					production,
					statistics,
				} = get();
				const shopEffects = getShopEffects(get().shop);
				const sector = getProductionSector(sectorId);
				const recipe = productionRecipes.find(
					(item) => item.id === recipeId && item.sectorId === sectorId,
				);

				if (
					!sector ||
					!recipe ||
					!get().builtSectorIds.includes(sector.id) ||
					market.level < sector.requiredLevel ||
					market.level < recipe.requiredLevel ||
					getSectorTier(get().sectorTiers, sector.id) < (recipe.requiredSectorTier ?? 1)
				) {
					return false;
				}
				// An evolved sector makes more per batch (T2 +25%, T3 +50%, rounded up).
				const batchOutput = getSectorBatchOutput(recipe.outputQuantity, getSectorTier(get().sectorTiers, sector.id));

				const usedSlots = new Set(
					production.jobs
						.filter((job) => job.sectorId === sectorId)
						.map((job) => job.slotIndex),
				);
				const slotIndex = Array.from(
					{ length: getSectorSlotCount(sector.slotCount, get().sectorTiers, sector.id) },
					(_, index) => index,
				).find((index) => !usedSlots.has(index));

				if (slotIndex === undefined) {
					return false;
				}

				const hasIngredients = recipe.ingredients.every(
					(ingredient) =>
						(inventory[ingredient.productId] ?? 0) >= ingredient.quantity,
				);

				if (!hasIngredients) {
					return false;
				}

				const queuedOutput = production.jobs
					.filter((job) => job.outputProductId === recipe.outputProductId)
					.reduce((total, job) => total + job.outputQuantity, 0);

				if (
					!canAddToInventory(
						recipe.outputProductId,
						batchOutput + queuedOutput,
						inventory,
						inventoryCapacityLevels,
					)
				) {
					return false;
				}

				const nextInventory = { ...inventory };

				for (const ingredient of recipe.ingredients) {
					nextInventory[ingredient.productId] -= ingredient.quantity;
				}

				const now = Date.now();
				const eventEffects = getActiveGameEventEffects(events, now);
				const job: ProductionJob = {
					endsAt:
						now +
						Math.round(
							recipe.durationMs *
								eventEffects.productionDurationMultiplier *
								shopEffects.productionDurationMultiplier *
								getSectorTierDefinition(getSectorTier(get().sectorTiers, sectorId)).durationMultiplier,
						),
					id: `${sectorId}-${recipeId}-${now}`,
					outputProductId: recipe.outputProductId,
					outputQuantity: batchOutput,
					recipeId,
					sectorId,
					slotIndex,
					startedAt: now,
				};

				set({
					inventory: nextInventory,
					production: {
						...production,
						jobs: [...production.jobs, job],
					},
					statistics: {
						...statistics,
						productionJobsStarted: statistics.productionJobsStarted + 1,
					},
				});

				return true;
			},
			// Made by hand in the sector's kitchen game: no slot and no wait (the player did the work);
			// a perfect game (3 stars) makes one extra unit.
			cookByHand: ({ recipeId, sectorId, stars }) => {
				const state = get();
				const sector = getProductionSector(sectorId);
				const recipe = productionRecipes.find(
					(item) => item.id === recipeId && item.sectorId === sectorId,
				);
				if (
					!sector ||
					!recipe ||
					!state.builtSectorIds.includes(sector.id) ||
					state.market.level < sector.requiredLevel ||
					state.market.level < recipe.requiredLevel ||
					getSectorTier(state.sectorTiers, sector.id) < (recipe.requiredSectorTier ?? 1) ||
					!recipe.ingredients.every(
						(ingredient) => (state.inventory[ingredient.productId] ?? 0) >= ingredient.quantity,
					)
				) {
					return false;
				}
				const queuedOutput = state.production.jobs
					.filter((job) => job.outputProductId === recipe.outputProductId)
					.reduce((total, job) => total + job.outputQuantity, 0);
				const fits = (quantity: number) =>
					canAddToInventory(
						recipe.outputProductId,
						quantity + queuedOutput,
						state.inventory,
						state.inventoryCapacityLevels,
					);
				const batchOutput = getSectorBatchOutput(recipe.outputQuantity, getSectorTier(state.sectorTiers, sector.id));
				if (!fits(batchOutput)) {
					return false;
				}
				const bonus = stars >= 3 && fits(batchOutput + 1) ? 1 : 0;
				const made = batchOutput + bonus;
				const now = Date.now();
				const nextInventory = { ...state.inventory };
				for (const ingredient of recipe.ingredients) {
					nextInventory[ingredient.productId] -= ingredient.quantity;
				}
				nextInventory[recipe.outputProductId] = (nextInventory[recipe.outputProductId] ?? 0) + made;
				set({
					inventory: nextInventory,
					inventoryLots: {
						...state.inventoryLots,
						[recipe.outputProductId]: appendInventoryLots(
							state.inventoryLots[recipe.outputProductId],
							createInventoryLots(recipe.outputProductId, made, now),
						),
					},
					production: {
						...state.production,
						totalCrafted: state.production.totalCrafted + made,
					},
					statistics: {
						...state.statistics,
						productionJobsStarted: state.statistics.productionJobsStarted + 1,
					},
				});
				return true;
			},
			processNextCustomer: () => {
				const {
					employees,
					events,
					market,
					shelfAssignments,
					shelfLots,
					shelfPrices,
					shelfStock,
					shop,
				} = get();
				const now = Date.now();
				const daily = normalizeDailyState(get().daily, market.level, now);
				const eventEffects = getActiveGameEventEffects(events, now);
				const shopEffects = getShopEffects(shop);
				const decorEffects = getDecorEffects(get().interior);
				const employeeEffects = getEmployeeEffects(employees);
				const { day } = get();
				if (
					!market.isOpen ||
					!market.nextCustomerAt ||
					now < market.nextCustomerAt ||
					!acceptsCustomers(day, now)
				) {
					return false;
				}

				const featuredProductId =
					events.activeEvent && events.activeEvent.endsAt > now
						? events.activeEvent.featuredProductId
						: undefined;
				// "Cheap" at the end of the month means cheaper than the middle price of what is on sale.
				const referencePrice =
					eventEffects.cheapPreference > 0
						? getReferencePrice(
								shelfProductSlots.flatMap((slot) => {
									const productId = shelfAssignments[slot.id];
									if (!productId || (shelfStock[slot.id] ?? 0) <= 0) return [];
									return [
										shelfPrices[slot.id] ??
											itemCatalog.find((item) => item.id === productId)?.sellingPrice ??
											0,
									];
								}),
							)
						: 0;
				// A new week starts counting the weekly event's sales from here.
				const weekly = syncWeeklyEvent(get().weeklyEvent, market.soldByProduct, now);
				if (weekly !== get().weeklyEvent) set({ weeklyEvent: weekly });
				// Store mishaps: a broken freezer blocks its shelf, a wrong tag sells at half
				// price, and every open incident lowers the store's reputation.
				const incidentEffects = getIncidentEffects(get().incidents.active);
				// Special sectors at T3: their goods sell 10% dearer (src/data/fixture-tiers.ts sectorTiers).
				const sectorPriceMultiplier = (slotId: string) => {
					const physical = getPhysicalShelfId(slotId);
					if (!isSectorShelfId(physical)) return 1;
					const counter = getSectorCounter(physical);
					return counter ? getSectorTierDefinition(getSectorTier(get().sectorTiers, counter.sectorId)).priceMultiplier : 1;
				};
				const availableProducts = shelfProductSlots
					.filter(
						(shelf) =>
							isShelfUnlocked(shelf.id, getCurrentShelfSlotCounts(get())) &&
							!incidentEffects.blockedShelfIds.includes(
								getPhysicalShelfId(shelf.id),
							),
					)
					.flatMap((shelf) => {
						const productId = shelfAssignments[shelf.id];
						const product = itemCatalog.find((item) => item.id === productId);

						if (
							!product ||
							!market.unlockedProductIds.includes(product.id) ||
							(shelfStock[shelf.id] ?? 0) <= 0
						) {
							return [];
						}

						return [
							{
								...product,
								availableQuantity: shelfStock[shelf.id] ?? 0,
								// A sector at T3 sells dearer and its customers expect it (the suggestion follows).
								marketPrice: product.suggestedPrice * sectorPriceMultiplier(shelf.id),
								// Night customers want drinks and snacks more. A spot at eye level sells
								// more (src/services/shelf-care.ts).
								necessity: Math.min(
									100,
									product.demand *
										getTurnEffects(get().era.id, get().day.shift).necessityMultiplier(product.category) *
										getWeeklyNecessityMultiplier(product.category, now) *
										getSlotPositionFactor(shelf.id) *
										// Evolved fixtures draw more customers (+5% T2 … +25% ★, src/services/tier-rewards.ts).
										(1 + getFixtureAttraction(get(), getPhysicalShelfId(shelf.id))) *
										// Events: cold drinks in the heat, the product in the video, cheap goods at month's end.
										getEventDemandMultiplier(
											eventEffects,
											{
												category: product.category,
												productId: product.id,
												sellingPrice: shelfPrices[shelf.id] ?? product.sellingPrice,
											},
											featuredProductId,
											referencePrice,
										),
								),
								productId: product.id,
								promotionRate: 0,
								// Levelled products catch the eye of impulse buyers.
								visualAttractiveness:
									(product.visualAttractiveness ?? 0) +
									getProductLevel(get().productLevels, product.id) * ATTRACTIVENESS_PER_LEVEL,
								sellingPrice: Math.max(
									1,
									Math.round(
										(shelfPrices[shelf.id] ?? product.sellingPrice) *
											sectorPriceMultiplier(shelf.id) *
											(incidentEffects.priceMultipliers[
												getPhysicalShelfId(shelf.id)
											] ?? 1),
									),
								),
								shelfId: shelf.id,
							},
						];
					});
				// Every unlocked slot with stock is on sale, on any fixture.
				const onSale = availableProducts;
				const plainVisit = simulateMarketVisit({
					budgetMultiplier:
						(1 + Math.max(market.level - 1, 0) * 0.08) *
						shopEffects.customerBudgetMultiplier *
						decorEffects.budgetMultiplier *
						eventEffects.customerBudgetMultiplier *
						getTurnEffects(get().era.id, get().day.shift).budgetMultiplier,
					// Bigger markets: customers come with a basket, then a cart (more products each).
					maxProductsBonus:
						shopEffects.maxProductsBonus +
						decorEffects.basketItems +
						getEraEffects(get().era.id).basketBonus +
						eventEffects.extraBasketItems,
					products: onSale,
					// Baskets and carts on the map: each customer takes the smallest that holds their plan.
					carriers: decorEffects.carriers,
					// Customers pay the shelf price: the era makes them richer (budget), never the goods dearer.
					// (the ATM: customers who drew cash spend it — +15% on what they buy, +20/25% at its higher tiers; as a
					// money ceiling alone it rarely changed anything, audit 05/11)
					revenueMultiplier: shopEffects.revenueMultiplier * eventEffects.revenueMultiplier * decorEffects.spendMultiplier,
					categoryRevenueBonuses: shopEffects.categoryRevenueBonuses,
					seed: market.randomSeed,
					storeReputation:
						market.customerSatisfaction +
						shopEffects.storeReputationBonus +
						employeeEffects.storeReputationBonus -
						incidentEffects.reputationPenalty,
				});
				// Levelled products earn more profit per sale (src/services/product-levels.ts).
				const visit = {
					...plainVisit,
					purchases: plainVisit.purchases.map((purchase) =>
						applyProductLevel(
							purchase,
							itemCatalog.find((item) => item.id === purchase.productId)?.purchasePrice ?? 0,
							getProductLevel(get().productLevels, purchase.productId),
						),
					),
				};
				// The visit is counted now; money, XP and sales arrive when the customer pays at
				// the register (completeCheckout), which may be the player or a cashier.
				const nextDaily = markDailySale(daily, 0, 1, 0);
				const nextShelfStock = { ...shelfStock };
				const nextShelfLots: GameShelfLots = { ...shelfLots };
				const experienceGained = Math.round(
					getExperienceFromSales(visit.purchases, itemCatalog) *
						eventEffects.experienceMultiplier,
				);

				for (const purchase of visit.purchases) {
					const currentShelfQuantity = nextShelfStock[purchase.shelfId] ?? 0;
					const shelfLotsForProduct = reconcileInventoryLots(
						purchase.productId,
						currentShelfQuantity,
						nextShelfLots[purchase.shelfId],
						now,
					);
					const soldLots = takeInventoryLots(
						shelfLotsForProduct,
						purchase.quantity,
					);
					nextShelfStock[purchase.shelfId] -= purchase.quantity;
					nextShelfLots[purchase.shelfId] = soldLots.remainingLots;
				}
				// The cleaning/freshness mechanic was removed: fixtures never get messy.
				const nextShelfCare = get().shelfCare;

				const nextSeed = market.randomSeed + 1;
				const plainVisitor = createMarketCustomer(
					visit,
					market.randomSeed,
					shelfPrices,
					market.customerSatisfaction - incidentEffects.reputationPenalty,
				);
				// Customers the event brought (the ATM queue on payday, the bus at rush hour…): Unity starts their
				// walk in the event's scene; the visit, basket and money are the same.
				const origin = getEventCustomerOrigin(events, now, market.randomSeed);
				// Unity hands them the basket or cart they took (src/data/fixture-tiers.ts chooseCarrier).
				const carried = visit.carrier ? { ...plainVisitor, carrier: visit.carrier } : plainVisitor;
				const visitor = origin ? { ...carried, origin } : carried;
				const saleCategories: Record<string, number> = {};
				let saleProfit = 0;
				for (const purchase of visit.purchases) {
					const product = getDayProduct(purchase.productId);
					if (!product) continue;
					saleCategories[product.category] =
						(saleCategories[product.category] ?? 0) + purchase.quantity;
					saleProfit +=
						purchase.revenue - product.purchasePrice * purchase.quantity;
				}
				const checkout = createPendingCheckout(
					{
						archetype: visit.customer.archetype,
						cashOnly: eventEffects.cashOnly,
						patienceMultiplier: shopEffects.checkoutPatienceMultiplier,
						categories: saleCategories,
						customerId: visitor.id,
						customerName: visitor.name,
						experience: experienceGained,
						items: visit.purchases.map((purchase) => ({
							name:
								itemCatalog.find((item) => item.id === purchase.productId)
									?.name ?? "",
							productId: purchase.productId,
							quantity: purchase.quantity,
							shelfId: purchase.shelfId,
							unitPrice: Math.max(
								1,
								Math.round(purchase.revenue / purchase.quantity),
							),
						})),
						mood: visitor.mood,
						profit: Math.round(saleProfit),
						satisfaction: visitor.satisfaction,
						seed: market.randomSeed,
					},
					now,
				);
				const customer = checkout
					? { ...visitor, status: "no caixa" as const }
					: visitor;
				let nextDay = recordDayCustomer(day, {
					categories: {},
					profit: 0,
					revenue: 0,
					satisfaction: customer.satisfaction,
					units: 0,
				});
				// The coin machines in the market (gumball, claw machine): some customers stop and play.
				const plays = rollDecorPlays(
					decorEffects,
					createDeliveryRandom(market.randomSeed * 31 + 7),
					(1 + Math.max(market.level - 1, 0) * 0.08) * getTurnEffects(get().era.id, get().day.shift).ticketMultiplier,
				);
				const playCoins = plays.reduce((sum, play) => sum + play.coins, 0);
				let playedDaily = nextDaily;
				const decorEarnings = { ...(market.decorEarnings ?? {}) };
				if (playCoins > 0) {
					nextDay = recordDaySale(nextDay, { categories: {}, profit: Math.round(playCoins * 0.9), revenue: playCoins, units: 0 });
					playedDaily = markDailySale(nextDaily, playCoins, 0, 0);
					for (const play of plays) decorEarnings[play.decorId] = (decorEarnings[play.decorId] ?? 0) + play.coins;
				}
				set({
					...(playCoins > 0 ? { coins: get().coins + playCoins } : {}),
					checkout: checkout
						? enqueueCheckout(get().checkout, checkout)
						: get().checkout,
					daily: playedDaily,
					day: nextDay,
					lastSessionAt: now,
					employees: {
						...employees,
						employees: employees.employees.map((employee) =>
							employee.isWorking
								? grantEmployeeExperience(employee, 1)
								: employee,
						),
					},
					market: {
						...market,
						customersServed: market.customersServed + 1,
						customerSatisfaction:
							Math.round(
								(market.customerSatisfaction * 0.88 +
									customer.satisfaction * 0.12) *
									10,
							) / 10,
						nextCustomerAt:
							now +
							getCustomerArrivalDelay(
								market.level,
								market.unlockedProductIds.length,
								nextSeed,
								shopEffects.customerArrivalMultiplier *
									eventEffects.customerArrivalMultiplier *
									employeeEffects.customerArrivalMultiplier *
								getTurnEffects(get().era.id, get().day.shift).customerArrivalMultiplier *
									getLoyaltyArrivalMultiplier(day.loyalty),
								getTurnEffects(get().era.id, get().day.shift).minArrivalDelayMs / shopEffects.customerCapacityMultiplier /
									// a busy event (payday, rush hour) brings more people than the shop's usual cap
									Math.max(1, eventEffects.customerArrivalMultiplier),
							),
						recentCustomers: [customer, ...market.recentCustomers].slice(0, 3),
						...((visit.cartShortfall ?? 0) > 0 ? { cartShortfall: (market.cartShortfall ?? 0) + 1 } : {}),
						...(playCoins > 0
							? {
									decorEarnings,
									decorPlays: [
										...plays.map((play) => ({ ...play, at: now })),
										...(market.decorPlays ?? []),
									].slice(0, 6),
								}
							: {}),
						randomSeed: nextSeed,
					},
					shelfStock: nextShelfStock,
					shelfLots: nextShelfLots,
					shelfCare: nextShelfCare,
				});

				get().processEmployeeWork();
				return true;
			},
			checkoutArrived: (customerId) => {
				const checkout = markCheckoutArrived(get().checkout, customerId, Date.now());
				// Already standing at the till (a repeated report): nothing to change.
				if (checkout === get().checkout)
					return get().checkout.queue.some((item) => item.customerId === customerId);
				set({ checkout });
				return true;
			},
			completeCheckout: (checkoutId, charged) => {
				const state = get();
				const now = Date.now();
				const payment = completeCheckoutRule(
					state.checkout,
					checkoutId,
					now,
					charged,
				);
				if (!payment) return false;
				set(applyCheckoutPayment(state, payment, now));
				return true;
			},
			processCheckoutCounter: () => {
				const now = Date.now();
				let changed = false;
				// Customers who gave up leave their basket; the goods go back on the shelf.
				const expired = expireCheckouts(get().checkout, now);
				if (expired.expired.length > 0) {
					set(returnAbandonedCheckouts(get(), expired, now));
					changed = true;
				}
				// The staffed counters and the kiosks ring customers up side by side (src/data/checkout-lanes.ts): one
				// server per working cashier, as many as there are built checkouts (the best cashiers first), plus every
				// built kiosk. Without a cashier the main checkout is the player's.
				const shopEffects = getShopEffects(get().shop, now);
				const ownedItemIds = get().shop.ownedItemIds;
				const staffSpeed =
					getActiveGameEventEffects(get().events, now).staffSpeedMultiplier * shopEffects.cashierSpeedMultiplier;
				const cashierIntervals = get()
					.employees.employees.filter((employee) => employee.isWorking && employee.role === "cashier")
					.map((employee) => employee.efficiency)
					.sort((a, b) => b - a)
					.slice(0, getCheckoutCount(ownedItemIds))
					.map((efficiency) => AUTO_CASHIER_INTERVAL_MS / Math.max(0.1, efficiency * staffSpeed));
				const kioskIntervals = Array.from({ length: getKioskCount(ownedItemIds) }, () => KIOSK_INTERVAL_MS);
				const next = nextAutoCheckouts(get().checkout, now, [...cashierIntervals, ...kioskIntervals]);
				if (next.state !== get().checkout) set({ checkout: next.state });
				for (const checkoutId of next.checkoutIds) {
					const payment = completeCheckoutRule(get().checkout, checkoutId, now, undefined, true);
					if (payment) {
						set(applyCheckoutPayment(get(), payment, now));
						changed = true;
					}
				}
				return changed;
			},
			fixIncident: (incidentId) => {
				const state = get();
				const now = Date.now();
				const incident = state.incidents.active.find(
					(item) => item.id === incidentId,
				);
				if (!incident || state.coins < incident.fixCost) return false;
				const fixed = fixStoreIncident(state.incidents, incidentId, now, "player");
				if (!fixed) return false;
				set({
					coins: state.coins - incident.fixCost,
					day: recordDayIncidentFixed(state.day),
					incidents: fixed.state,
					lastSessionAt: now,
					market: {
						...state.market,
						customerSatisfaction: clampSatisfaction(
							state.market.customerSatisfaction + 1,
						),
					},
				});
				return true;
			},
			serveWindowSale: (requestId) => {
				const state = get();
				const now = Date.now();
				const sales = state.events.windowSales;
				const request = sales?.requests.find((item) => item.id === requestId);
				const product = request ? itemCatalog.find((item) => item.id === request.productId) : undefined;
				if (!sales || !request || !product) return false;
				// The bottle comes from a shelf holding the product, else from the storeroom.
				const slot = shelfProductSlots.find(
					(item) => state.shelfAssignments[item.id] === product.id && (state.shelfStock[item.id] ?? 0) > 0,
				);
				const stored = state.inventory[product.id] ?? 0;
				if (!slot && stored <= 0) return false;
				const served = serveWindowRequest(sales, requestId, now);
				if (!served) return false;
				const { price, tip } = getWindowSalePrice(
					slot ? (state.shelfPrices[slot.id] ?? product.sellingPrice) : product.sellingPrice,
				);
				const stock: Partial<GameState> = slot
					? {
							shelfLots: {
								...state.shelfLots,
								[slot.id]: takeInventoryLots(
									reconcileInventoryLots(product.id, state.shelfStock[slot.id] ?? 0, state.shelfLots[slot.id], now),
									1,
								).remainingLots,
							},
							shelfStock: { ...state.shelfStock, [slot.id]: (state.shelfStock[slot.id] ?? 0) - 1 },
						}
					: {
							inventory: { ...state.inventory, [product.id]: stored - 1 },
							inventoryLots: {
								...state.inventoryLots,
								[product.id]: takeInventoryLots(
									reconcileInventoryLots(product.id, stored, state.inventoryLots[product.id]),
									1,
								).remainingLots,
							},
						};
				const experience = Math.round(
					product.xpPerSale * getActiveGameEventEffects(state.events, now).experienceMultiplier,
				);
				const sale = applyStreetSale(state, product, price, tip, experience, now);
				set({
					...stock,
					...sale,
					coins: (sale.coins ?? state.coins) + (served.reachedGoal ? getWindowSalesBonus(state.daily.goal) : 0),
					events: { ...state.events, windowSales: served.state },
				});
				return true;
			},
			processStoreIncidents: () => {
				const now = Date.now();
				let changed = false;
				// Mishaps (broken freezer, lamps, dirt) belong to the market building: the stalls of the
				// first expansions (mesinha → minimercado) have none.
				const open =
					get().market.isOpen &&
					get().day.phase === "open" &&
					isMarketBuilding(get().era.id);
				const spawned = spawnStoreIncident(
					get().incidents,
					getIncidentShelves(get()),
					now,
					get().market.level,
					open,
				);
				if (spawned.state !== get().incidents) {
					set({ incidents: spawned.state });
					changed = Boolean(spawned.incident);
				}
				// A broken freezer loses one unit of its shelf now and then.
				const spoil = freezerSpoilage(get().incidents, now);
				if (spoil.state !== get().incidents) set({ incidents: spoil.state });
				if (spoil.shelfIds.length > 0) {
					const { shelfLots, shelfStock } = get();
					const nextStock = { ...shelfStock };
					const nextLots = { ...shelfLots };
					for (const shelfId of spoil.shelfIds) {
						const slot = shelfProductSlots.find(
							(item) =>
								getPhysicalShelfId(item.id) === shelfId &&
								(nextStock[item.id] ?? 0) > 0,
						);
						if (!slot) continue;
						nextLots[slot.id] = takeInventoryLots(
							nextLots[slot.id],
							1,
						).remainingLots;
						nextStock[slot.id] -= 1;
					}
					set({ shelfLots: nextLots, shelfStock: nextStock });
					changed = true;
				}
				// Dirt customers track in, at its own pace; the cleaners sweep it (processEmployeeWork).
				const dirt = spawnFloorDirt(get().incidents, getIncidentShelves(get()), now, open);
				if (dirt.state !== get().incidents) {
					set({ incidents: dirt.state });
					changed = changed || Boolean(dirt.incident);
				}
				return changed;
			},
			resetGame: () => {
				const { currencyPurchases } = get();

				set({ ...getInitialGameState(), currencyPurchases });
			},
			assignProductToShelf: (shelfId, productId, replace = false) => {
				const {
					inventory,
					inventoryCapacityLevels,
					inventoryLots,
					shelfLots,
					market,
					shelfAssignments,
					shelfPrices,
					shelfStock,
				} = get();
				const product = itemCatalog.find((item) => item.id === productId);
				const isAssignedElsewhere = Object.entries(shelfAssignments).some(
					([assignedShelfId, assignedProductId]) =>
						assignedShelfId !== shelfId && assignedProductId === productId,
				);

				if (
					!product ||
					!market.unlockedProductIds.includes(productId) ||
					!isShelfUnlocked(shelfId, getCurrentShelfSlotCounts(get())) ||
					!canFixtureSell(getPhysicalShelfId(shelfId), product).ok ||
					isAssignedElsewhere ||
					(!replace && (shelfStock[shelfId] ?? 0) > 0)
				) {
					return false;
				}

				const oldProductId = shelfAssignments[shelfId];
				const quantity = shelfStock[shelfId] ?? 0;
				if (oldProductId === productId) return true;
				if (
					oldProductId &&
					!canAddToInventory(
						oldProductId,
						quantity,
						inventory,
						inventoryCapacityLevels,
					)
				)
					return false;
				const returnedLots = oldProductId
					? reconcileInventoryLots(oldProductId, quantity, shelfLots[shelfId])
					: [];
				set({
					inventory: oldProductId
						? {
								...inventory,
								[oldProductId]: (inventory[oldProductId] ?? 0) + quantity,
							}
						: inventory,
					inventoryLots: oldProductId
						? {
								...inventoryLots,
								[oldProductId]: appendInventoryLots(
									inventoryLots[oldProductId],
									returnedLots,
								),
							}
						: inventoryLots,
					shelfStock: { ...shelfStock, [shelfId]: 0 },
					shelfLots: { ...shelfLots, [shelfId]: [] },
					shelfAssignments: {
						...shelfAssignments,
						[shelfId]: productId,
					},
					shelfPrices: {
						...shelfPrices,
						[shelfId]: product.sellingPrice,
					},
				});

				return true;
			},
			tendShelf: (shelfId) => {
				const physicalShelfId = getPhysicalShelfId(shelfId);
				const state = get();
				const condition = getShelfCondition(state.shelfCare, physicalShelfId);
				if (getShelfSlotCount(physicalShelfId, getCurrentShelfSlotCounts(state)) <= 0 || condition >= 100) return false;
				// Tidying up is a bit of work: a little experience for the care given.
				const progression = applyExperience(state.market.level, state.market.experience, Math.ceil((100 - condition) / 25));
				set({
					shelfCare: { ...state.shelfCare, [physicalShelfId]: 100 },
					market: {
						...state.market,
						level: progression.level,
						experience: progression.experience,
						totalExperience: state.market.totalExperience + Math.ceil((100 - condition) / 25),
						unlockedProductIds: Array.from(
							new Set([...state.market.unlockedProductIds, ...getUnlockedProductIds(progression.level, state.era.id)]),
						),
					},
				});
				return true;
			},
			devWearShelf: (shelfId, amount = 50) => {
				if (!__DEV__) return false;
				const id = getPhysicalShelfId(shelfId);
				const condition = getShelfCondition(get().shelfCare, id);
				set({ shelfCare: { ...get().shelfCare, [id]: Math.max(0, condition - amount) } });
				return true;
			},
			swapShelfSlots: (firstSlotId, secondSlotId) => {
				const state = get();
				const counts = getCurrentShelfSlotCounts(state);
				if (
					firstSlotId === secondSlotId ||
					getPhysicalShelfId(firstSlotId) !== getPhysicalShelfId(secondSlotId) ||
					!isShelfUnlocked(firstSlotId, counts) ||
					!isShelfUnlocked(secondSlotId, counts)
				)
					return false;
				// Moving products around the same fixture: product, stock, lots and price move together.
				const swap = <T,>(record: Record<string, T>) => {
					const next = { ...record };
					const first = record[firstSlotId];
					const second = record[secondSlotId];
					if (second === undefined) delete next[firstSlotId];
					else next[firstSlotId] = second;
					if (first === undefined) delete next[secondSlotId];
					else next[secondSlotId] = first;
					return next;
				};
				set({
					shelfAssignments: swap(state.shelfAssignments),
					shelfStock: swap(state.shelfStock),
					shelfLots: swap(state.shelfLots),
					shelfPrices: swap(state.shelfPrices),
				});
				return true;
			},
			clearShelf: (shelfId) => {
				const {
					inventory,
					inventoryCapacityLevels,
					inventoryLots,
					shelfAssignments,
					shelfLots,
					shelfStock,
				} = get();
				const productId = shelfAssignments[shelfId];
				const quantity = shelfStock[shelfId] ?? 0;

				if (
					!productId ||
					!isShelfUnlocked(shelfId, getCurrentShelfSlotCounts(get())) ||
					!canAddToInventory(
						productId,
						quantity,
						inventory,
						inventoryCapacityLevels,
					)
				) {
					return false;
				}

				const shelfLotsForProduct = reconcileInventoryLots(
					productId,
					quantity,
					shelfLots[shelfId],
				);
				const movedLots = takeInventoryLots(shelfLotsForProduct, quantity);

				set({
					inventory: {
						...inventory,
						[productId]: (inventory[productId] ?? 0) + quantity,
					},
					inventoryLots: {
						...inventoryLots,
						[productId]: appendInventoryLots(
							inventoryLots[productId],
							movedLots.takenLots,
						),
					},
					shelfLots: {
						...shelfLots,
						[shelfId]: movedLots.remainingLots,
					},
					shelfAssignments: {
						...shelfAssignments,
						[shelfId]: null,
					},
					shelfStock: {
						...shelfStock,
						[shelfId]: 0,
					},
				});

				return true;
			},
			restockShelf: ({ amount = 1, productId, shelfId }) => {
				const {
					inventory,
					inventoryLots,
					shelfAssignments,
					shelfLots,
					shelfStock,
					shelfUpgradeLevels,
					statistics,
				} = get();
				const availableQuantity = inventory[productId] ?? 0;
				const currentQuantity = shelfStock[shelfId] ?? 0;
				const capacity = getSlotCapacity(get(), shelfId);

				if (
					shelfAssignments[shelfId] !== productId ||
					!isShelfUnlocked(shelfId, getCurrentShelfSlotCounts(get()))
				) {
					return false;
				}

				if (
					availableQuantity < amount ||
					amount <= 0 ||
					currentQuantity + amount > capacity
				) {
					return false;
				}

				const inventoryLotsForProduct = reconcileInventoryLots(
					productId,
					availableQuantity,
					inventoryLots[productId],
				);
				const movedLots = takeInventoryLots(inventoryLotsForProduct, amount);

				set({
					inventory: {
						...inventory,
						[productId]: availableQuantity - amount,
					},
					inventoryLots: {
						...inventoryLots,
						[productId]: movedLots.remainingLots,
					},
					shelfLots: {
						...shelfLots,
						[shelfId]: appendInventoryLots(
							shelfLots[shelfId],
							movedLots.takenLots,
						),
					},
					shelfStock: {
						...shelfStock,
						[shelfId]: currentQuantity + amount,
					},
					statistics: {
						...statistics,
						restockedUnits: statistics.restockedUnits + amount,
					},
				});

				return true;
			},
			setMarketOpen: (isOpen) => {
				// The shop needs its furniture: nothing opens while owned pieces still wait to be placed.
				if (isOpen && !get().market.isOpen && getPiecesToPlaceBeforeOpening(get()) > 0)
					return false;
				// Boosters only run while the market is open (audit 05/11: they ticked away between days, so a coffee
				// used on the results screen was gone before anyone came in): closing pauses what is left, opening resumes it.
				if (isOpen !== get().market.isOpen) {
					const at = Date.now();
					const shopNow = get().shop;
					if (!isOpen) {
						const paused = { ...(shopNow.pausedBoosts ?? {}) };
						for (const [id, endsAt] of Object.entries(shopNow.activeBoosts ?? {}))
							if (endsAt > at) paused[id] = (paused[id] ?? 0) + (endsAt - at);
						set({ shop: { ...shopNow, activeBoosts: {}, pausedBoosts: paused } });
					} else if (Object.keys(shopNow.pausedBoosts ?? {}).length > 0) {
						const active = { ...(shopNow.activeBoosts ?? {}) };
						for (const [id, left] of Object.entries(shopNow.pausedBoosts ?? {}))
							active[id] = Math.max(at, active[id] ?? 0) + left;
						set({ shop: { ...shopNow, activeBoosts: active, pausedBoosts: {} } });
					}
				}
				// Closing time: the customers already in line are rung up before the doors lock.
				if (!isOpen && get().market.isOpen)
					for (const pending of [...get().checkout.queue]) {
						const payment = completeCheckoutRule(
							get().checkout,
							pending.id,
							Date.now(),
							undefined,
							true,
						);
						if (payment) set(applyCheckoutPayment(get(), payment, Date.now()));
					}
				const { employees, events, market, shop, statistics } = get();
				const now = Date.now();
				const daily = normalizeDailyState(get().daily, market.level, now);
				const eventEffects = getActiveGameEventEffects(events, now);
				const shopEffects = getShopEffects(shop);
				const employeeEffects = getEmployeeEffects(employees);
				let day = get().day;
				// Opening always happens inside a day: without a chosen contract it is a free day.
				// A finished day must be reviewed (claimDayResult) before the next one opens.
				if (isOpen && !market.isOpen) {
					if (day.phase === "results") return false;
					if (day.phase === "planning") day = startMarketDay(day, null, now) ?? day;
				}
				const isOpening = isOpen && !market.isOpen;
				const isClosing = !isOpen && market.isOpen;
				const customerSatisfaction = market.customerSatisfaction;
				if (isClosing && day.phase === "open") {
					const closed = closeMarketDay(day, now, market.level);
					if (closed) day = closed;
				}
				const firstCustomer =
					market.customersServed === 0 && market.recentCustomers.length === 0;
				// Opening the shop (every day, not only the first one) brings someone in a few seconds: a long wait
				// before the first customer made the start of each day feel like nothing was happening (Lucas 24/10).
				const nextCustomerDelay = isOpening
					? 3_000 + (Math.abs(market.randomSeed) % 2_000)
					: firstCustomer
					? 6_000
					: getCustomerArrivalDelay(
							market.level,
							market.unlockedProductIds.length,
							market.randomSeed,
							shopEffects.customerArrivalMultiplier *
								eventEffects.customerArrivalMultiplier *
								employeeEffects.customerArrivalMultiplier *
								getTurnEffects(get().era.id, get().day.shift).customerArrivalMultiplier *
								getLoyaltyArrivalMultiplier(day.loyalty),
							getTurnEffects(get().era.id, get().day.shift).minArrivalDelayMs / shopEffects.customerCapacityMultiplier /
									// a busy event (payday, rush hour) brings more people than the shop's usual cap
									Math.max(1, eventEffects.customerArrivalMultiplier),
						);
				const lastShiftSummary =
					isClosing && market.currentShift
						? {
								closedAt: now,
								customersServed:
									market.customersServed -
									market.currentShift.startingCustomersServed,
								durationMs: Math.max(0, now - market.currentShift.startedAt),
								experienceGained:
									market.totalExperience -
									market.currentShift.startingExperience,
								revenue:
									market.totalRevenue -
									market.currentShift.startingTotalRevenue,
								satisfactionChange: Number(
									(
										customerSatisfaction -
										market.currentShift.startingSatisfaction
									).toFixed(1),
								),
								satisfaction: customerSatisfaction,
								unitsSold:
									market.unitsSold - market.currentShift.startingUnitsSold,
							}
						: market.lastShiftSummary;

				// End of the shift (turno): everyone who worked it is paid; without the coins they stop working.
				let coins = get().coins;
				let nextEmployees = get().employees;
				if (isClosing) {
					const payroll = getShiftPayroll(nextEmployees.employees);
					const paid = coins >= payroll;
					if (paid) coins -= payroll;
					nextEmployees = {
						...nextEmployees,
						employees: paid
							? nextEmployees.employees
							: nextEmployees.employees.map((employee) => ({
									...employee,
									isWorking: false,
								})),
						lastPayroll:
							payroll > 0
								? { amount: payroll, dayNumber: day.dayNumber, paid, paidAt: now }
								: nextEmployees.lastPayroll,
						tasks: [],
						totalSalariesPaid: nextEmployees.totalSalariesPaid + (paid ? payroll : 0),
					};
				}
				set({
					coins,
					daily,
					day,
					employees: nextEmployees,
					lastSessionAt: now,
					market: {
						...market,
						customerSatisfaction,
						currentShift: isOpening
							? {
									startedAt: now,
									startingCustomersServed: market.customersServed,
									startingExperience: market.totalExperience,
									startingSatisfaction: market.customerSatisfaction,
									startingTotalRevenue: market.totalRevenue,
									startingUnitsSold: market.unitsSold,
								}
							: isClosing
								? null
								: market.currentShift,
						lastShiftSummary,
						isOpen,
						nextCustomerAt: isOpen ? now + nextCustomerDelay : null,
					},
					statistics:
						isOpen && !market.isOpen
							? {
									...statistics,
									marketOpenings: statistics.marketOpenings + 1,
								}
							: statistics,
				});
				return true;
			},
			startDay: (contractId, shift = "dia") => {
				const { day, market } = get();
				if (day.phase !== "planning" || market.isOpen) return false;
				if (getPiecesToPlaceBeforeOpening(get()) > 0) return false;
				const started = startMarketDay(
					day,
					contractId === FREE_DAY_CONTRACT_ID ? null : contractId,
					Date.now(),
				);
				if (!started) return false;
				// The night turn exists from the Späti on.
				set({ day: { ...started, shift: shift === "noite" && canOpenAtNight(get().era.id) ? "noite" : "dia" } });
				get().setMarketOpen(true);
				return get().market.isOpen;
			},
			closeDay: () => {
				const { day, market } = get();
				if (day.phase !== "open") return false;
				if (market.isOpen) {
					get().setMarketOpen(false);
				} else {
					// Defensive: a day left open without an open market still gets its results.
					const closed = closeMarketDay(day, Date.now(), market.level);
					if (closed) set({ day: closed });
				}
				return get().day.phase === "results";
			},
			claimDayResult: () => {
				const state = get();
				const { day, market } = state;
				if (day.phase !== "results" || !day.result) return false;
				const reward = day.result.total;
				const progression = applyExperience(
					market.level,
					market.experience,
					reward.experience,
				);
				const unlockedProductIds = Array.from(
					new Set([
						...market.unlockedProductIds,
						...getUnlockedProductIds(progression.level, state.era.id),
					]),
				);
				const recentUnlockProductIds = unlockedProductIds.filter(
					(productId) => !market.unlockedProductIds.includes(productId),
				);
				const nextMarket = {
					...market,
					experience: progression.experience,
					lastExperienceGain: reward.experience,
					level: progression.level,
					recentUnlockProductIds:
						recentUnlockProductIds.length > 0
							? recentUnlockProductIds
							: market.recentUnlockProductIds,
					totalExperience: market.totalExperience + reward.experience,
					unlockedProductIds,
				};
				const nextDay = advanceMarketDay(day, progression.level, {
					...getDayStoreContext({ ...state, market: nextMarket }),
					forecast: getDayForecastFor({ ...state, market: nextMarket }),
				});
				if (!nextDay) return false;
				set({
					coins: state.coins + reward.coins,
					day: nextDay,
					// A finished turn is what an hour away is worth (offline sales).
					era: recordFinishedTurn(state.era, {
						profit: day.stats.profit,
						customers: day.stats.customers,
					}),
					logistics: {
						...state.logistics,
						premiumCurrency: state.logistics.premiumCurrency + reward.diamonds,
					},
					market: nextMarket,
				});
				return true;
			},
			processMarketDay: () => {
				// Offers sized with older rules (or before the store could forecast its own day) are made again
				// while the day is still being planned.
				if (get().day.phase === "planning" && get().day.offersRevision !== DAY_OFFERS_REVISION) {
					const refreshed = refreshDayOffers(get().day, get().market.level, {
						...getDayStoreContext(get()),
						forecast: getDayForecastFor(get()),
					});
					if (refreshed) set({ day: refreshed });
				}
				const { day, market } = get();
				const now = Date.now();
				// Saves from before turns (or a desync) never leave an open market outside a day.
				if (market.isOpen && day.phase === "planning") {
					const started = startMarketDay(day, null, now);
					if (started) set({ day: started });
					return Boolean(started);
				}
				if (day.phase !== "open") return false;
				if (isDayOver(day, now)) {
					// customers already inside finish shopping and pay before the day closes
					if (isClosing(day, now, get().checkout.queue.length)) return false;
					return get().closeDay();
				}
				return false;
			},
			setShelfPrice: (shelfId, price) => {
				const { shelfAssignments, shelfPrices, statistics } = get();
				const product = itemCatalog.find(
					(item) => item.id === shelfAssignments[shelfId],
				);

				if (!product || !Number.isFinite(price)) {
					return false;
				}

				const nextPrice = Math.min(
					product.maxPrice,
					Math.max(product.minPrice, Math.round(price)),
				);

				if (shelfPrices[shelfId] === nextPrice) {
					return false;
				}

				set({
					shelfPrices: {
						...shelfPrices,
						[shelfId]: nextPrice,
					},
					statistics: {
						...statistics,
						priceChanges: statistics.priceChanges + 1,
					},
				});

				return true;
			},
			setMarketLevel: (level) => {
				const { market } = get();
				const nextLevel = Math.max(1, Math.floor(level));

				set({
					market: {
						...market,
						experience: 0,
						level: nextLevel,
						recentUnlockProductIds: [],
						// (exclusives came with evolutions, not with the level: they stay)
						unlockedProductIds: [
							...getUnlockedProductIds(nextLevel, get().era.id),
							...market.unlockedProductIds.filter((id) => itemCatalog.find((item) => item.id === id)?.exclusive),
						],
					},
				});
			},
			setEmployeeWorking: (employeeId, isWorking) => {
				const { employees } = get();

				if (
					!employees.employees.some((employee) => employee.id === employeeId)
				) {
					return false;
				}

				set({
					employees: {
						...employees,
						employees: employees.employees.map((employee) =>
							employee.id === employeeId
								? { ...employee, isWorking }
								: employee,
						),
					},
				});

				return true;
			},
			trainEmployee: (employeeId) => {
				const { coins, employees } = get();
				const employee = employees.employees.find(
					(item) => item.id === employeeId,
				);
				const trainedEmployee = employee ? promoteEmployee(employee) : null;

				if (!employee || !trainedEmployee) {
					return false;
				}

				const cost = getEmployeeTrainingCost(employee);
				if (coins < cost) {
					return false;
				}

				set({
					coins: coins - cost,
					employees: {
						...employees,
						employees: employees.employees.map((item) =>
							item.id === employeeId ? trainedEmployee : item,
						),
					},
				});

				return true;
			},
			unlockNextShelf: () => {
				const state = get();
				const shelfSlotCounts = getCurrentShelfSlotCounts(state);
				const unlockedShelves = getUnlockedPhysicalShelfCount(shelfSlotCounts);
				const nextUpgrade = getNextShelfUnlockUpgrade(unlockedShelves);
				const nextShelf = shelves[unlockedShelves];

				if (
					!nextUpgrade ||
					!nextShelf ||
					findInteriorConstruction(state.interiorConstructions, "shelf", nextShelf.id) ||
					// Each shelf comes with the expansion that has room for it.
					getEraOrder(state.era.id) < getEraOrder(nextUpgrade.eraId) ||
					// ...and only while the shop floor has room for it (Unity measures it).
					!hasInteriorRoom(`shelf:${nextShelf.id}`) ||
					state.market.level < nextUpgrade.playerLevel ||
					state.coins < nextUpgrade.coinCost
				) {
					return false;
				}

				// The shelf goes to the inventory: the builders start once the player places it.
				set({
					coins: state.coins - nextUpgrade.coinCost,
					interiorConstructions: [
						...state.interiorConstructions,
						createPendingConstruction("shelf", nextShelf.id, getShelfBuildDurationMs(unlockedShelves)),
					],
				});

				return true;
			},
			buildSector: (sectorId, currency = "coins") => {
				const state = get();
				const sector = getProductionSector(sectorId);
				if (!sector) return false;
				const plan = sectorBuildPlans[sector.id];
				const layout = getSimulatorLayout(state.unlockedMarketExpansionIds, state.era.id);
				const diamondCost = Math.max(1, Math.ceil(plan.coinCost / 1_500));
				if (
					state.builtSectorIds.includes(sector.id) ||
					findInteriorConstruction(state.interiorConstructions, "sector", sector.id) ||
					state.market.level < sector.requiredLevel ||
					getEraOrder(state.era.id) < getEraOrder(sector.eraId) ||
					// The sector needs the market wing that has room for it.
					!layout.sectorIds.includes(sector.id) ||
					!hasInteriorRoom(`sector:${sector.id}`) ||
					(currency === "coins" && state.coins < plan.coinCost) ||
					(currency === "diamonds" && !enoughDiamonds(diamondCost))
				) {
					return false;
				}
				const now = Date.now();
				set({
					coins: currency === "coins" ? state.coins - plan.coinCost : state.coins,
					logistics:
						currency === "diamonds"
							? {
									...state.logistics,
									premiumCurrency: state.logistics.premiumCurrency - diamondCost,
								}
							: state.logistics,
					// The sector goes to the inventory: the builders start once the player places it.
					interiorConstructions: [
						...state.interiorConstructions,
						createPendingConstruction("sector", sector.id, plan.durationMs, now),
					],
				});
				return true;
			},
			processInteriorConstructions: (now = Date.now()) => {
				const state = get();
				const done = state.interiorConstructions.filter((item) => !item.pending && item.endsAt <= now);
				if (done.length === 0) return false;
				let shelfSlotCounts = getCurrentShelfSlotCounts(state);
				let builtSectorIds = state.builtSectorIds;
				let ownedItemIds = state.shop.ownedItemIds;
				let celebrations = state.celebrations;
				for (const item of done) {
					// The cold room keeps its works, and ends with the same reveal as the evolutions.
					const coldTier = item.kind === "shop" ? Object.entries(coldRoomTierItemIds).find(([, id]) => id === item.targetId)?.[0] : undefined;
					celebrations = coldTier
						? pushCelebration(celebrations, "tier", `coldroom:coldroom:${coldTier}`, Math.min(now, Date.now()))
						: pushCelebration(celebrations, item.kind, item.targetId, Math.min(now, Date.now()));
					if (item.kind === "shelf" && getShelfSlotCount(item.targetId, shelfSlotCounts) <= 0)
						shelfSlotCounts = { ...shelfSlotCounts, [item.targetId]: initialUnlockedShelfSlots };
					else if (item.kind === "sector" && !builtSectorIds.includes(item.targetId as ProductionSectorId)) {
						builtSectorIds = [...builtSectorIds, item.targetId as ProductionSectorId];
						// The sector sells what it makes at its own counter.
						const counter = getSectorCounterFor(item.targetId);
						if (counter && getShelfSlotCount(counter.id, shelfSlotCounts) <= 0)
							shelfSlotCounts = { ...shelfSlotCounts, [counter.id]: initialUnlockedShelfSlots };
					}
					else if (item.kind === "shop" && !ownedItemIds.includes(item.targetId))
						ownedItemIds = [...ownedItemIds, item.targetId];
				}
				set({
					// The next works in the queue start right away.
					interiorConstructions: scheduleInteriorConstructions(
						state.interiorConstructions.filter((item) => item.pending || item.endsAt > now),
						Math.min(now, Date.now()),
					),
					shelfSlotCounts,
					unlockedShelfSlots: getTotalUnlockedShelfSlots(shelfSlotCounts),
					builtSectorIds,
					shop: { ...state.shop, ownedItemIds },
					celebrations,
					rankings: addLeaguePoints(state.rankings, LEAGUE_POINTS.build * done.length, Date.now()),
				});
				return true;
			},
			finishInteriorConstructionNow: (constructionId) => {
				const { interiorConstructions, logistics } = get();
				const item = interiorConstructions.find((entry) => entry.id === constructionId);
				// Bought but not placed: there is nothing to build yet.
				if (!item || item.pending) return false;
				const now = Date.now();
				// Queued works cost their own building time, not the wait for the ones before.
				const diamondCost = getInteriorSkipCost(
					item.startedAt > now ? constructionDuration(item) : item.endsAt - now,
				);
				if (!enoughDiamonds(diamondCost)) return false;
				set({
					logistics: { ...logistics, premiumCurrency: logistics.premiumCurrency - diamondCost },
					interiorConstructions: interiorConstructions.map((entry) =>
						entry.id === constructionId
							? { ...entry, startedAt: Math.min(entry.startedAt, now), endsAt: Math.min(entry.endsAt, now) }
							: entry,
					),
				});
				return get().processInteriorConstructions(now);
			},
			devFinishInteriorConstructions: () => {
				if (!__DEV__) return false;
				return get().processInteriorConstructions(Number.MAX_SAFE_INTEGER);
			},
			unlockNextShelfSlot: () => get().unlockNextShelf(),
			// The separate "Mais um produto" purchase is gone (Lucas 01/11): places come with the evolutions
			// (src/services/tier-rewards.ts). Kept for old buttons and the protocol, it never buys anything now.
			expandShelfSlots: (_shelfId) => false,
			unlockMarketExpansion: (expansionId, currency = "coins") => {
				const {
					coins,
					logistics,
					market,
					marketExpansionConstruction,
					unlockedMarketExpansionIds,
				} = get();
				const expansion = getMarketExpansion(expansionId);

				if (
					!expansion ||
					marketExpansionConstruction ||
					unlockedMarketExpansionIds.includes(expansionId) ||
					getMissingMarketExpansionPrerequisites(
						expansion,
						unlockedMarketExpansionIds,
					).length > 0 ||
					market.level < expansion.requiredLevel ||
					(currency === "coins" && coins < expansion.coinCost) ||
					(currency === "diamonds" && !enoughDiamonds(expansion.diamondCost))
				) {
					return false;
				}

				set({
					coins: currency === "coins" ? coins - expansion.coinCost : coins,
					logistics: {
						...logistics,
						premiumCurrency:
							currency === "diamonds"
								? logistics.premiumCurrency - expansion.diamondCost
								: logistics.premiumCurrency,
					},
					// Paying starts the works; the area opens when the construction finishes.
					marketExpansionConstruction: {
						expansionId,
						startedAt: Date.now(),
						endsAt: Date.now() + expansion.buildDurationMs,
					},
				});
				return true;
			},
			processMarketExpansionConstruction: (now = Date.now()) => {
				const { marketExpansionConstruction, unlockedMarketExpansionIds } =
					get();
				if (
					!marketExpansionConstruction ||
					marketExpansionConstruction.endsAt > now
				) {
					return false;
				}
				set({
					marketExpansionConstruction: null,
					unlockedMarketExpansionIds: unlockedMarketExpansionIds.includes(
						marketExpansionConstruction.expansionId,
					)
						? unlockedMarketExpansionIds
						: [
								...unlockedMarketExpansionIds,
								marketExpansionConstruction.expansionId,
							],
				});
				return true;
			},
			saveInteriorLayout: (value) => {
				const { interior, interiorConstructions } = get();
				const sanitized = sanitizeInteriorItems(value, interior.owned);
				if (!sanitized) return false;
				// Bought pieces the player just placed start their works (in the builders' queue);
				// the ones still stored stay in the inventory, owned by their pending construction.
				const now = Date.now();
				let constructions = interiorConstructions;
				const pendingPieces = new Set<string>();
				for (const build of interiorConstructions) {
					if (!build.pending) continue;
					const pieces = interiorPieceIds(build.kind, build.targetId);
					if (pieces.some((id) => sanitized.some((item) => item.id === id && !item.stored)))
						constructions = placeInteriorConstruction(constructions, build.id, now);
					else for (const id of pieces) pendingPieces.add(id);
				}
				const items = sanitized.filter((item) => !(item.stored && pendingPieces.has(item.id)));
				set({ interior: { ...interior, items }, interiorConstructions: constructions });
				return true;
			},
			purchaseDecor: (decorId, currency = "coins") => {
				const { coins, interior, logistics, market } = get();
				const decor = getInteriorDecor(decorId);
				if (!decor || market.level < decor.requiredLevel) return false;
				// The cart bays need the market building's aisles (Mercadinho on).
				if (decor.placeEra && getEraOrder(get().era.id) < getEraOrder(decor.placeEra)) return false;
				const useDiamonds = currency === "diamonds" || !decor.coinPrice;
				const price = useDiamonds ? decor.diamondPrice : decor.coinPrice;
				if (!price) return false;
				if (useDiamonds ? !enoughDiamonds(price) : coins < price) return false;
				if ((interior.owned[decorId] ?? 0) >= 99) return false;
				set({
					coins: useDiamonds ? coins : coins - price,
					logistics: useDiamonds
						? { ...logistics, premiumCurrency: logistics.premiumCurrency - price }
						: logistics,
					interior: {
						...interior,
						owned: { ...interior.owned, [decorId]: (interior.owned[decorId] ?? 0) + 1 },
					},
				});
				return true;
			},
			// Evolving decorations (ATM, gumball, claw machine): every piece of that kind takes the next tier.
			// "Evoluções dos móveis", the special sectors: T2 / T3 for coins by shop size or a fixed diamond price. Nothing
			// else changes: the production queue, the stock and the sector's place in the shop stay as they are.
			upgradeSectorTier: (sectorId, currency = "coins") => {
				const { builtSectorIds, coins, era, evolutions, logistics, sectorTiers } = get();
				if (!builtSectorIds.includes(sectorId) || findEvolution(evolutions, "sector", sectorId)) return false;
				const tier = getSectorTier(sectorTiers, sectorId);
				if (tier >= SECTOR_MAX_TIER) return false;
				const price = getSectorTierPrice(tier + 1, era.id);
				if (!price) return false;
				const useDiamonds = currency === "diamonds";
				const cost = useDiamonds ? price.diamonds : price.coins;
				if (useDiamonds ? !enoughDiamonds(cost) : coins < cost) return false;
				set({
					coins: useDiamonds ? coins : coins - cost,
					logistics: useDiamonds ? { ...logistics, premiumCurrency: logistics.premiumCurrency - cost } : logistics,
					// Timed like every evolution: the sector keeps producing until the crew finishes (processFixtureEvolutions).
					evolutions: enqueueEvolution(evolutions, {
						kind: "sector",
						targetId: sectorId,
						toTier: tier + 1,
						durationMs: getEvolutionDurationMs("sector", sectorId, tier + 1),
					}),
				});
				return true;
			},
			upgradeDecorTier: (decorId, currency = "coins") => {
				const { coins, evolutions, interior, logistics, market } = get();
				const next = getNextDecorTier(interior.tiers, decorId);
				if (!next || market.level < next.requiredLevel || (interior.owned[decorId] ?? 0) <= 0) return false;
				if (findEvolution(evolutions, "decor", decorId)) return false;
				const useDiamonds = currency === "diamonds" || !next.coinPrice;
				const price = useDiamonds ? next.diamondPrice : next.coinPrice;
				if (!price) return false;
				if (useDiamonds ? !enoughDiamonds(price) : coins < price) return false;
				set({
					coins: useDiamonds ? coins : coins - price,
					logistics: useDiamonds ? { ...logistics, premiumCurrency: logistics.premiumCurrency - price } : logistics,
					evolutions: enqueueEvolution(evolutions, {
						kind: "decor",
						targetId: decorId,
						toTier: next.tier,
						durationMs: getEvolutionDurationMs("decor", decorId, next.tier),
					}),
				});
				return true;
			},
			// "Cores do mercado" (src/data/market-paint.ts): repaint for coins (≈2.5 turns of the stage's profit) or a fixed
			// price in diamonds; going back to the classic navy and gold never costs.
			applyMarketPaint: (primary, accent, currency = "coins") => {
				const p = normalizeHex(primary);
				const a = normalizeHex(accent);
				if (!p || !a) return false;
				const { coins, era, logistics, marketPaint } = get();
				if (p === marketPaint.primary && a === marketPaint.accent) return false;
				if (p === CLASSIC_PRIMARY && a === CLASSIC_ACCENT) return get().resetMarketPaint();
				const useDiamonds = currency === "diamonds";
				const price = useDiamonds ? MARKET_PAINT_DIAMONDS : getMarketPaintCoinPrice(era.id);
				if (useDiamonds ? !enoughDiamonds(price) : coins < price) return false;
				set({
					coins: useDiamonds ? coins : coins - price,
					logistics: useDiamonds ? { ...logistics, premiumCurrency: logistics.premiumCurrency - price } : logistics,
					marketPaint: withAppliedPaint(marketPaint, p, a, true),
				});
				return true;
			},
			resetMarketPaint: () => {
				const { marketPaint } = get();
				if (marketPaint.primary === CLASSIC_PRIMARY && marketPaint.accent === CLASSIC_ACCENT) return false;
				set({ marketPaint: withAppliedPaint(marketPaint, CLASSIC_PRIMARY, CLASSIC_ACCENT, false) });
				return true;
			},
			// ---------------------------------------------------------------- Rede de supermercados (src/services/chain.ts)
			// Naming the chain: free the first time (the card that opens with the rede), diamonds to rename later.
			nameChain: (name, emblem) => {
				const { chain, era, logistics } = get();
				if (!isChainUnlocked(era.id)) return false;
				const check = checkChainName(name);
				if (!check.ok || !isChainEmblem(emblem)) return false;
				const first = chain.brand.namedAt === null;
				if (!first && check.name === chain.brand.name && emblem === chain.brand.emblem) return false;
				// changing only the emblem is free; a new name after the first costs diamonds
				const pays = !first && check.name !== chain.brand.name;
				if (pays && !enoughDiamonds(CHAIN_RENAME_DIAMONDS)) return false;
				set({
					logistics: pays ? { ...logistics, premiumCurrency: logistics.premiumCurrency - CHAIN_RENAME_DIAMONDS } : logistics,
					chain: {
						...chain,
						brand: {
							name: check.name,
							emblem,
							namedAt: chain.brand.namedAt ?? Date.now(),
							renames: chain.brand.renames + (pays ? 1 : 0),
						},
					},
				});
				return true;
			},
			setChainAutoOrder: (enabled) => {
				const { chain, era } = get();
				if (!isChainUnlocked(era.id) || chain.autoOrder.enabled === !!enabled) return false;
				set({ chain: { ...chain, autoOrder: { enabled: !!enabled, lastAt: 0 } } });
				return true;
			},
			buyFleetTruck: (kind) => {
				const { chain, coins, era } = get();
				if (!isChainUnlocked(era.id) || (kind !== "seco" && kind !== "refrigerado")) return false;
				const price = getNextTruckPrice(chain, kind as FleetTruckKind);
				if (price === null || coins < price) return false;
				set({ coins: coins - price, chain: addTruck(chain, kind as FleetTruckKind) });
				return true;
			},
			upgradeFleetSpeed: () => {
				const { chain, coins, era } = get();
				const price = getNextSpeedPrice(chain);
				if (!isChainUnlocked(era.id) || price === null || coins < price) return false;
				set({ coins: coins - price, chain: { ...chain, fleet: { ...chain.fleet, speedLevel: chain.fleet.speedLevel + 1 } } });
				return true;
			},
			// Restock through the distribution centre: the same cart as a supplier's, carried by a fleet truck.
			orderFromDistributionCenter: (lines) => get().placeSupplierCart({ lines, via: "frota" }),
			acceptChainContract: (contractId) => {
				const now = Date.now();
				const state = get();
				if (!isChainUnlocked(state.era.id)) return false;
				const chain = releaseTrucks(state.chain, now);
				const contract = chain.contracts.offers.find((offer) => offer.id === contractId && offer.acceptedAt === null);
				if (!contract || contract.expiresAt <= now) return false;
				if (getContractShortfall(contract, state.inventory).length > 0) return false;
				const truck = pickTruck(chain, contract.cold, now);
				if (!truck) return false;
				const inventory = { ...state.inventory };
				const inventoryLots = { ...state.inventoryLots };
				for (const line of contract.lines) {
					inventory[line.productId] = (inventory[line.productId] ?? 0) - line.units;
					inventoryLots[line.productId] = takeInventoryLots(inventoryLots[line.productId], line.units).remainingLots;
				}
				const trip = Math.round(contract.tripMs * getTripFactor(chain));
				const withJob = withTruckJob(chain, truck.id, {
					kind: "contrato",
					refId: contract.id,
					departAt: now,
					arriveAt: now + trip,
					returnAt: now + trip * 2,
				});
				set({
					inventory,
					inventoryLots,
					chain: {
						...withJob,
						contracts: {
							...withJob.contracts,
							offers: withJob.contracts.offers.map((offer) =>
								offer.id === contract.id ? { ...offer, acceptedAt: now, truckId: truck.id } : offer,
							),
						},
					},
				});
				return true;
			},
			// Buys a branch (level 1) or upgrades it; both are works on a clock.
			buyChainBranch: (branchId) => {
				const now = Date.now();
				const { chain, coins, era } = get();
				const branch = chain.branches[branchId as ChainBranchId];
				if (!isChainUnlocked(era.id) || !branch) return false;
				const current = updateBranch(branch, now);
				const next = getBranchNextStep(current);
				if (!next || coins < next.price) return false;
				set({
					coins: coins - next.price,
					chain: {
						...chain,
						branches: {
							...chain.branches,
							[branchId]: { ...current, works: { level: next.level, endsAt: now + next.buildMs }, supplyAt: now },
						},
					},
				});
				return true;
			},
			finishChainBranchNow: (branchId) => {
				const now = Date.now();
				const { chain, logistics } = get();
				const branch = chain.branches[branchId as ChainBranchId];
				if (!branch?.works) return false;
				const cost = getSkipDiamondCost(branch.works.endsAt - now);
				if (!enoughDiamonds(cost)) return false;
				const updated = updateBranch({ ...branch, works: { ...branch.works, endsAt: now } }, now);
				set({
					logistics: { ...logistics, premiumCurrency: logistics.premiumCurrency - cost },
					chain: { ...chain, branches: { ...chain.branches, [branchId]: updated } },
				});
				return true;
			},
			// A truck takes a cargo from the market's stockroom to the branch: its shelves fill when it arrives.
			sendChainBranchCargo: (branchId) => {
				const now = Date.now();
				const state = get();
				const chain0 = releaseTrucks(state.chain, now);
				const branch = chain0.branches[branchId as ChainBranchId];
				if (!isChainUnlocked(state.era.id) || !branch || branch.level < 1 || branch.cargo) return false;
				const cargo = chooseBranchCargo(
					branch.id,
					branch.level,
					state.inventory,
					itemCatalog,
					state.market.unlockedProductIds,
				);
				if (!cargo.enough) return false;
				const truck = pickTruck(chain0, cargo.cold, now) ?? (cargo.cold ? null : pickTruck(chain0, false, now));
				if (!truck) return false;
				const inventory = { ...state.inventory };
				const inventoryLots = { ...state.inventoryLots };
				for (const line of cargo.lines) {
					inventory[line.productId] = (inventory[line.productId] ?? 0) - line.units;
					inventoryLots[line.productId] = takeInventoryLots(inventoryLots[line.productId], line.units).remainingLots;
				}
				const trip = getBranchTripMs(chain0);
				const updated = updateBranch(branch, now);
				const chain = withTruckJob(chain0, truck.id, {
					kind: "filial",
					refId: branch.id,
					departAt: now,
					arriveAt: now + trip,
					returnAt: now + trip * 2,
				});
				set({
					inventory,
					inventoryLots,
					chain: {
						...chain,
						branches: {
							...chain.branches,
							[branch.id]: { ...updated, cargo: { truckId: truck.id, arriveAt: now + trip, supply: cargo.supply } },
						},
					},
				});
				return true;
			},
			collectChainBranches: () => {
				const now = Date.now();
				const { chain, coins } = get();
				const updated = updateBranches(chain, now);
				let got = 0;
				const branches = { ...updated.branches };
				for (const id of Object.keys(branches) as ChainBranchId[]) {
					const amount = Math.floor(branches[id].pending);
					if (amount <= 0) continue;
					got += amount;
					branches[id] = { ...branches[id], pending: branches[id].pending - amount, earned: branches[id].earned + amount };
				}
				if (got <= 0) return false;
				set({ coins: coins + got, chain: { ...updated, branches } });
				return true;
			},
			// Every second (desktop/host.ts): trucks come back, contracts pay, branches earn, offers refresh and the
			// automatic restock sends a truck when something runs low.
			processChain: (now = Date.now()) => {
				const state = get();
				if (!isChainUnlocked(state.era.id)) return false;
				let chain = state.chain;
				let coins = state.coins;
				let diamonds = state.logistics.premiumCurrency;
				let xp = 0;
				let changed = false;
				// the chain's own products open with the rede (saves already there get them now)
				const missing = privateLabelProducts.filter((p) => !state.market.unlockedProductIds.includes(p.id)).map((p) => p.id);
				// contracts whose truck reached the client are paid
				const paid = chain.contracts.offers.filter((offer) => {
					if (offer.acceptedAt === null || !offer.truckId) return false;
					const truck = chain.fleet.trucks.find((t) => t.id === offer.truckId);
					const arrive = truck?.job?.refId === offer.id ? truck.job.arriveAt : offer.acceptedAt + offer.tripMs;
					return now >= arrive;
				});
				if (paid.length) {
					changed = true;
					for (const offer of paid) {
						coins += offer.reward;
						diamonds += offer.diamonds;
						xp += offer.xp;
					}
					chain = {
						...chain,
						contracts: {
							...chain.contracts,
							offers: chain.contracts.offers.filter((offer) => !paid.includes(offer)),
							completed: chain.contracts.completed + paid.length,
							earned: chain.contracts.earned + paid.reduce((sum, offer) => sum + offer.reward, 0),
						},
					};
				}
				const released = releaseTrucks(chain, now);
				if (released !== chain) changed = true;
				chain = released;
				// branches: works ending and cargos arriving change what the player sees; the income itself is applied
				// lazily (collect / page view) so the save is not rewritten every second
				for (const branch of Object.values(chain.branches)) {
					if ((branch.works && now >= branch.works.endsAt) || (branch.cargo && now >= branch.cargo.arriveAt)) {
						chain = { ...chain, branches: { ...chain.branches, [branch.id]: updateBranch(branch, now) } };
						changed = true;
					}
				}
				const refreshed = refreshContracts(chain, {
					catalog: itemCatalog,
					unlockedProductIds: state.market.unlockedProductIds,
					eraIndex: getEraOrder(state.era.id),
					now,
				});
				if (refreshed !== chain) changed = true;
				chain = refreshed;
				if (changed || missing.length || xp > 0) {
					const market = get().market;
					const progression = xp > 0 ? applyExperience(market.level, market.experience, xp) : null;
					set({
						coins,
						logistics: { ...get().logistics, premiumCurrency: diamonds },
						chain,
						market: {
							...market,
							...(progression
								? {
										experience: progression.experience,
										level: progression.level,
										lastExperienceGain: xp,
										totalExperience: market.totalExperience + xp,
									}
								: {}),
							unlockedProductIds: Array.from(new Set([...market.unlockedProductIds, ...missing])),
						},
					});
				}
				// automatic restock through the distribution centre (a dry or cold truck, whatever runs low)
				const auto = get().chain.autoOrder;
				if (auto.enabled && now - auto.lastAt >= AUTO_ORDER_EVERY_MS) {
					set({ chain: { ...get().chain, autoOrder: { ...auto, lastAt: now } } });
					if (get().coins > AUTO_ORDER_RESERVE) get().orderLowStock("frota");
				}
				return changed;
			},
			finishMarketExpansionNow: () => {
				const { logistics, marketExpansionConstruction } = get();
				if (!marketExpansionConstruction) {
					return false;
				}
				const diamondCost = getMarketExpansionSkipCost(
					marketExpansionConstruction.endsAt - Date.now(),
				);
				if (!enoughDiamonds(diamondCost)) {
					return false;
				}
				set({
					logistics: {
						...logistics,
						premiumCurrency: logistics.premiumCurrency - diamondCost,
					},
				});
				return get().processMarketExpansionConstruction(Number.MAX_SAFE_INTEGER);
			},
			upgradeInventoryCapacity: (productId) => {
				const { coins, inventoryCapacityLevels, market } = get();
				const product = itemCatalog.find((item) => item.id === productId);
				const upgradeLevel = inventoryCapacityLevels[productId] ?? 0;
				const nextUpgrade = getNextInventoryCapacityUpgrade(upgradeLevel);

				if (
					!product ||
					!nextUpgrade ||
					market.level < nextUpgrade.playerLevel ||
					coins < nextUpgrade.coinCost
				) {
					return false;
				}
				// Chilled products are kept in the cold room: its tier caps their boxes (what was bought stays).
				if (isChilledCategory(product.category) && upgradeLevel + 1 > getColdRoomUpgradeCap(getColdRoomTier(get().shop.ownedItemIds))) {
					return false;
				}

				set({
					coins: coins - nextUpgrade.coinCost,
					inventoryCapacityLevels: {
						...inventoryCapacityLevels,
						[productId]: upgradeLevel + 1,
					},
				});

				return true;
			},
			unlockProduct: (productId) => {
				const { market } = get();

				if (market.unlockedProductIds.includes(productId)) {
					return;
				}

				set({
					market: {
						...market,
						unlockedProductIds: [...market.unlockedProductIds, productId],
					},
				});
			},
			upgradeShelfCapacity: (shelfId, currency) => {
				if (!isShelfUnlocked(shelfId, getCurrentShelfSlotCounts(get()))) {
					return false;
				}
				shelfId = getPhysicalShelfId(shelfId);
				const { coins, evolutions, logistics, market, shelfUpgradeLevels } = get();
				const upgradeLevel = shelfUpgradeLevels[shelfId] ?? 0;
				const nextUpgrade = getNextShelfCapacityUpgrade(upgradeLevel);

				// One evolution of a fixture at a time (it is already being evolved or waiting for the crew).
				if (!nextUpgrade || market.level < nextUpgrade.playerLevel || findEvolution(evolutions, "shelf", shelfId)) {
					return false;
				}
				// Each capacity step is the fixture's next tier: a bigger piece the shop must have room for.
				if (getShelfType(shelfId) && !canBuyCapacityTier(upgradeLevel, get().era.id)) {
					return false;
				}

				if (
					(currency === "coins" && coins < nextUpgrade.coinCost) ||
					(currency === "diamonds" && !enoughDiamonds(nextUpgrade.diamondCost))
				) {
					return false;
				}

				// "Evoluções com recompensa" (Lucas 01/11): paid now, the evolution crew works on it and the tier (capacity,
				// places, bonuses, the exclusive product) applies when the timer ends. Meanwhile the fixture keeps selling.
				const toTier = getCapacityTier(upgradeLevel + 1);
				set({
					coins: currency === "coins" ? coins - nextUpgrade.coinCost : coins,
					logistics:
						currency === "diamonds"
							? {
									...logistics,
									premiumCurrency:
										logistics.premiumCurrency - nextUpgrade.diamondCost,
								}
							: logistics,
					evolutions: enqueueEvolution(evolutions, {
						kind: "shelf",
						targetId: shelfId,
						toTier,
						durationMs: getEvolutionDurationMs("shelf", shelfId, toTier),
					}),
				});

				return true;
			},
			// The evolution crew finished (also while the game was closed): the tier and its rewards apply, the reveal plays
			// when the player looks at the fixture (Unity, from the "tier" celebration).
			processFixtureEvolutions: (now = Date.now()) => {
				const state = get();
				const done = state.evolutions.filter((item) => item.endsAt <= now);
				if (done.length === 0) return false;
				let shelfUpgradeLevels = state.shelfUpgradeLevels;
				let sectorTiers = state.sectorTiers;
				let ownedItemIds = state.shop.ownedItemIds;
				let interior = state.interior;
				let celebrations = state.celebrations;
				for (const item of [...done].sort((a, b) => a.endsAt - b.endsAt)) {
					const at = Math.min(item.endsAt, Date.now());
					if (item.kind === "shelf") {
						const level = Math.max(shelfUpgradeLevels[item.targetId] ?? 0, item.toTier - 1);
						shelfUpgradeLevels = { ...shelfUpgradeLevels, [item.targetId]: level };
						celebrations = pushCelebration(celebrations, "tier", `shelf:${item.targetId}:${item.toTier}`, at);
					} else if (item.kind === "sector") {
						const tier = Math.max(getSectorTier(sectorTiers, item.targetId), item.toTier);
						sectorTiers = { ...sectorTiers, [item.targetId]: tier };
						celebrations = pushCelebration(celebrations, "tier", `sector:${item.targetId}:${tier}`, at);
					} else if (item.kind === "checkout") {
						if (item.itemId && !ownedItemIds.includes(item.itemId)) ownedItemIds = [...ownedItemIds, item.itemId];
						celebrations = pushCelebration(celebrations, "tier", `checkout:checkout:${item.toTier}`, at);
					} else {
						const tier = Math.max(interior.tiers?.[item.targetId] ?? 1, item.toTier);
						interior = { ...interior, tiers: { ...interior.tiers, [item.targetId]: tier } };
						celebrations = pushCelebration(celebrations, "tier", `decor:${item.targetId}:${tier}`, at);
					}
				}
				const next = { ...state, shelfUpgradeLevels, sectorTiers };
				const rewards = withTierRewards({ ...next, shelfSlotCounts: getCurrentShelfSlotCounts(next) });
				set({
					shelfUpgradeLevels,
					sectorTiers,
					shop: { ...state.shop, ownedItemIds },
					interior,
					celebrations,
					shelfSlotCounts: rewards.shelfSlotCounts,
					unlockedShelfSlots: rewards.unlockedShelfSlots,
					market: { ...state.market, unlockedProductIds: rewards.unlockedProductIds },
					rankings: addLeaguePoints(state.rankings, LEAGUE_POINTS.build * done.length, Date.now()),
					// The next evolution in the queue starts right away.
					evolutions: scheduleEvolutions(
						state.evolutions.filter((item) => item.endsAt > now),
						Math.min(now, Date.now()),
					),
				});
				return true;
			},
			finishEvolutionNow: (evolutionId) => {
				const { evolutions, logistics } = get();
				const item = evolutions.find((entry) => entry.id === evolutionId);
				if (!item) return false;
				const now = Date.now();
				const diamondCost = getEvolutionProgress(item, now).skipCost;
				if (!enoughDiamonds(diamondCost)) return false;
				set({
					logistics: { ...logistics, premiumCurrency: logistics.premiumCurrency - diamondCost },
					evolutions: evolutions.map((entry) =>
						entry.id === evolutionId ? { ...entry, startedAt: Math.min(entry.startedAt, now), endsAt: now } : entry,
					),
				});
				return get().processFixtureEvolutions(now);
			},
			devFinishEvolutions: () => {
				if (!__DEV__) return false;
				return get().processFixtureEvolutions(Number.MAX_SAFE_INTEGER);
			},
			};
		},
		{
			migrate: (persistedState, version) => {
				// Convert the legacy global slot count into complete physical shelves.
				if (version === 28) {
					const state = persistedState as GameState;
					return migrateGameState({
						...state,
						// This field did not exist in v28. Ignore the current in-memory
						// default when tests or a hot reload provide one alongside the
						// legacy total slot count.
						shelfSlotCounts: undefined,
						shelfAssignments: {
							...Object.fromEntries(
								shelfProductSlots.map((slot) => [slot.id, null]),
							),
							...state.shelfAssignments,
						},
					});
				}
				// 40: new catalog (products open with the expansions, two retired) and sector counters.
				// 41: fixtures open with the expansion that has room for them (no dairy fridge on the sidewalk).
				// 42: the supermarket's depot moved from lot B3 to C2: who bought B3 for it gets C2 too.
				// 43: products open level by level with the fixture that holds them (fruit and juice already on the
				// sidewalk): migrateGameState adds what the save's level and expansion open now.
				let migrated = persistedState;
				if (version < 40) migrated = migrateCatalog40(migrated);
				if (version < 41) migrated = migrateFixtures41(migrated);
				if (version < 42) {
					const state = migrated as Partial<GameState>;
					migrated = { ...state, lots: migrateDepotLot(state.lots) ?? state.lots };
				}
				const normalized = migrateGameState(migrated);
				// 49: evolutions with rewards (claude/evolucoes-recompensas.md): fixtures and sectors already past T1 get the
				// places and the exclusive products of their tiers now, with one "Novos produtos liberados" card. Nothing
				// is lowered; production and stock are untouched.
				if (version < 49) return withMigratedTierRewards(normalized);
				return normalized;
			},
			name: "checkout.game",
			// Everything the player built or owns is saved (and goes to the cloud, desktop/cloud.ts). Only diamondShortfall
			// (a store page to open, Lucas 12/10) is left out on purpose — see desktop/cloud.test.mjs.
			partialize: ({
				era,
				checkout,
				coins,
				currencyPurchases,
				daily,
				day,
				employees,
				events,
				incidents,
				inventory,
				receiving,
				inventoryLots,
				inventoryCapacityLevels,
				logistics,
				market,
				offlineSummary,
				lastSessionAt,
				unlockedMarketExpansionIds,
				marketExpansionConstruction,
				interior,
				interiorConstructions,
				evolutions,
				builtSectorIds,
				sectorTiers,
				missions,
				production,
				shop,
				shelfAssignments,
				shelfLots,
				shelfStock,
				shelfPrices,
				shelfSlotCounts,
				unlockedShelfSlots,
				shelfUpgradeLevels,
				shelfCare,
				statistics,
				productLevels,
				dailyLogin,
				rewardedAds,
				albumClaimedIds,
				weeklyEvent,
				lots,
				celebrations,
				delivery,
				onboarding,
				marketPaint,
				social,
				rankings,
				chain,
			}) => ({
				era,
				checkout,
				coins,
				currencyPurchases,
				daily,
				day,
				employees,
				events,
				incidents,
				inventory,
				receiving,
				inventoryLots,
				inventoryCapacityLevels,
				logistics,
				market,
				offlineSummary,
				lastSessionAt,
				unlockedMarketExpansionIds,
				marketExpansionConstruction,
				interior,
				interiorConstructions,
				evolutions,
				builtSectorIds,
				sectorTiers,
				missions,
				production,
				shop,
				shelfAssignments,
				shelfLots,
				shelfStock,
				shelfPrices,
				shelfSlotCounts,
				unlockedShelfSlots,
				shelfUpgradeLevels,
				shelfCare,
				statistics,
				productLevels,
				dailyLogin,
				rewardedAds,
				albumClaimedIds,
				weeklyEvent,
				lots,
				celebrations,
				delivery,
				onboarding,
				marketPaint,
				social,
				rankings,
				chain,
			}),
			storage: createJSONStorage(() => mmkvStorage),
			// A save that fails to load or migrate is kept on disk untouched (src/storage/save-guard.ts).
			onRehydrateStorage: () => (_state, error) => {
				if (error) lockSave(error);
			},
			// 35: employees gained tasks/nextTaskNumber/lastPayroll (staff jobs and per-shift pay).
			// 36: shelves, sectors and fixtures are built over time (interiorConstructions, builtSectorIds).
			// 37: market eras (era: mesinha → rede); old saves start at the mercadinho or later.
			// 38: land (lots bought and cleared) and the fields of product levels, daily gift, album and weekly event.
			// 39: the land became a grid of 12 equal lots (A1–C4); old lot ids are mapped onto it.
			// 42: the supermarket's depot is on lot C2 (was B3).
			// 43: products, sectors, staff and decor open on a level-by-level ladder (scripts/economy/catalog.py).
			// 44: the Delivery app (online orders from the minimercado on). Old saves start with no orders.
			// 45: first-time onboarding (src/services/onboarding.ts). Saves that already played skip the guided day.
			// 46: customers' special requests removed (Lucas 29/10): migrateGameState → normalizeDayState drops their list,
			// stats and contracts from the day; everything else (and the loyalty earned) is kept.
			// 47: "Cores do mercado" (marketPaint): older saves start with the classic navy and gold (migrateGameState).
			// 48: "Evoluções dos móveis": tiers are derived (shelfUpgradeLevels, shop items), nothing is lost. migrateGameState
			// gives the stations of "Cestinhas de Mão"/"Carrinhos Grandes" to place (withCartStations), the register step
			// to the minimercado on and to who had the conveyor/scanner (withCheckoutRegister); interior.tiers is new.
			// 49: evolutions take time (evolutions: the evolution crew's queue) and give rewards; old saves get the places and
			// exclusive products of the tiers they have (withMigratedTierRewards).
			// 50: social v1 (social: inbox ids applied, gifts today, profile cache, requests, invite rewards). Old saves get
			// an empty slice (migrateGameState); nothing else changes.
			// 51: Rede de supermercados (chain: brand, fleet, contracts, branches). Old saves get a fresh slice; nothing else
			// changes (the chain's own products open with the rede through processChain).
			version: 51,
		},
	),
);

// Missions that count what is in stock right now (it drops when boxes go onto the shelves or spoil) stay done once
// reached, so their reward can't vanish before the player claims it (QA 16/10).
useGameStore.subscribe((state) => {
	const reached = getNewlyReachedMissionIds(state);
	if (reached.length > 0)
		useGameStore.setState({
			missions: { ...state.missions, reachedMissionIds: [...(state.missions.reachedMissionIds ?? []), ...reached] },
		});
});

function normalizeShelfState(
	shelfStock: GameShelfStock,
	inventory: GameInventory,
	tiers: Pick<GameState, "shelfUpgradeLevels" | "sectorTiers">,
	shelfSlotCounts: GameShelfSlotCounts,
	shelfAssignments: GameShelfAssignments,
) {
	const nextInventory = { ...inventory };
	const nextShelfStock = { ...shelfStock };

	for (const shelf of shelfProductSlots) {
		const productId = shelfAssignments[shelf.id];
		const shelfQuantity = nextShelfStock[shelf.id] ?? 0;

		if (!productId) {
			nextShelfStock[shelf.id] = 0;
			continue;
		}

		if (!isShelfUnlocked(shelf.id, shelfSlotCounts)) {
			nextShelfStock[shelf.id] = 0;
			nextInventory[productId] =
				(nextInventory[productId] ?? 0) + shelfQuantity;
			continue;
		}

		const capacity = getSlotCapacity(tiers, shelf.id);

		if (shelfQuantity <= capacity) {
			continue;
		}

		const overflow = shelfQuantity - capacity;
		nextShelfStock[shelf.id] = capacity;
		nextInventory[productId] = (nextInventory[productId] ?? 0) + overflow;
	}

	return { inventory: nextInventory, shelfStock: nextShelfStock };
}

function normalizeInventoryLots(
	value: unknown,
	inventory: GameInventory,
): GameInventoryLots {
	const storedLots = value as Partial<GameInventoryLots> | undefined;
	const normalizedLots: GameInventoryLots = {};

	for (const [productId, quantity] of Object.entries(inventory)) {
		const numericProductId = Number(productId);
		if (!Number.isFinite(numericProductId) || quantity <= 0) {
			continue;
		}

		normalizedLots[numericProductId] = reconcileInventoryLots(
			numericProductId,
			quantity,
			storedLots?.[numericProductId],
		);
	}

	return normalizedLots;
}

function normalizeShelfLots(
	value: unknown,
	shelfStock: GameShelfStock,
	shelfAssignments: GameShelfAssignments,
): GameShelfLots {
	const storedLots = value as Partial<GameShelfLots> | undefined;
	const normalizedLots: GameShelfLots = {};

	for (const [shelfId, quantity] of Object.entries(shelfStock)) {
		const productId = shelfAssignments[shelfId];
		if (!productId || quantity <= 0) {
			continue;
		}

		normalizedLots[shelfId] = reconcileInventoryLots(
			productId,
			quantity,
			storedLots?.[shelfId],
		);
	}

	return normalizedLots;
}

// Shelf slots the stock clerks can refill: unlocked, with a product assigned.
function getRestockCandidates(state: GameState): RestockCandidate[] {
	const slotCounts = getCurrentShelfSlotCounts(state);
	return shelfProductSlots.flatMap((slot) => {
		const productId = state.shelfAssignments[slot.id];
		if (!productId || !isShelfUnlocked(slot.id, slotCounts)) return [];
		const product = itemCatalog.find((item) => item.id === productId);
		if (!product) return [];
		const shelfId = getPhysicalShelfId(slot.id);
		return [
			{
				available: state.inventory[productId] ?? 0,
				capacity: getSlotCapacity(state, slot.id),
				restockBonus: getFixtureRestockBonus(state, shelfId),
				category: product.category,
				productId,
				productName: product.name,
				shelfId,
				slotId: slot.id,
				stock: state.shelfStock[slot.id] ?? 0,
			},
		];
	});
}

function normalizeEmployeesState(value: unknown): GameEmployeesState {
	const state = value as Partial<GameEmployeesState> | undefined;
	const employees = Array.isArray(state?.employees) ? state.employees : [];

	return {
		employees: employees.flatMap((employee) => {
			const definition = getEmployeeDefinition(employee.role as EmployeeRole);

			if (!definition || !employee.id || !employee.name) {
				return [];
			}

			return [
				{
					efficiency:
						typeof employee.efficiency === "number" && employee.efficiency > 0
							? employee.efficiency
							: definition.efficiency,
					experience:
						typeof employee.experience === "number" && employee.experience >= 0
							? Math.floor(employee.experience)
							: 0,
					id: employee.id,
					isWorking: employee.isWorking !== false,
					level:
						typeof employee.level === "number" && employee.level >= 1
							? Math.min(5, Math.floor(employee.level))
							: 1,
					name: employee.name,
					role: definition.id,
					salary:
						typeof employee.salary === "number" && employee.salary >= 0
							? employee.salary
							: definition.salary,
				},
			];
		}),
		lastPayroll:
			state?.lastPayroll &&
			typeof state.lastPayroll.amount === "number" &&
			typeof state.lastPayroll.paidAt === "number"
				? state.lastPayroll
				: null,
		nextHireNumber:
			typeof state?.nextHireNumber === "number" && state.nextHireNumber > 0
				? Math.floor(state.nextHireNumber)
				: initialEmployeesState.nextHireNumber,
		nextTaskNumber:
			typeof state?.nextTaskNumber === "number" && state.nextTaskNumber > 0
				? Math.floor(state.nextTaskNumber)
				: 1,
		tasks: Array.isArray(state?.tasks)
			? state.tasks.filter(
					(task) =>
						task &&
						typeof task.id === "string" &&
						typeof task.employeeId === "string" &&
						typeof task.endsAt === "number" &&
						(task.kind === "restock" || task.kind === "incident"),
				)
			: [],
		nextPayrollAt:
			typeof state?.nextPayrollAt === "number" &&
			Number.isFinite(state.nextPayrollAt) &&
			state.nextPayrollAt > Date.now()
				? state.nextPayrollAt
				: Date.now() + EMPLOYEE_PAYROLL_INTERVAL_MS,
		totalSalariesPaid:
			typeof state?.totalSalariesPaid === "number" &&
			Number.isFinite(state.totalSalariesPaid) &&
			state.totalSalariesPaid >= 0
				? Math.floor(state.totalSalariesPaid)
				: 0,
	};
}

function normalizeShelfAssignments(
	shelfAssignments: Partial<GameShelfAssignments> | undefined,
) {
	const nextAssignments: GameShelfAssignments = {};
	const assignedProductIds = new Set<number>();

	for (const shelf of shelfProductSlots) {
		const hasPersistedAssignment = Object.hasOwn(
			shelfAssignments ?? {},
			shelf.id,
		);
		const productId = hasPersistedAssignment
			? shelfAssignments?.[shelf.id]
			: initialAssignments[shelf.id];
		const productExists = itemCatalog.some(
			(product) => product.id === productId,
		);

		if (!productId || !productExists || assignedProductIds.has(productId)) {
			nextAssignments[shelf.id] = null;
			continue;
		}

		nextAssignments[shelf.id] = productId;
		assignedProductIds.add(productId);
	}

	return nextAssignments;
}

// What one day of this market should bring, with its shelves as they are now (sizes the day's contracts).
// Same factors as processNextCustomer, without the passing ones (events, the weekly theme, open incidents).
function getDayForecastFor(state: GameState): DayForecast {
	const shopEffects = getShopEffects(state.shop.ownedItemIds);
	const employeeEffects = getEmployeeEffects(state.employees);
	const turn = getTurnEffects(state.era.id, "dia");
	const counts = getCurrentShelfSlotCounts(state);
	const products = shelfProductSlots.flatMap((shelf) => {
		if (!isShelfUnlocked(shelf.id, counts)) return [];
		const product = itemCatalog.find((item) => item.id === state.shelfAssignments[shelf.id]);
		if (!product || !state.market.unlockedProductIds.includes(product.id)) return [];
		return [
			{
				...product,
				availableQuantity: Math.max(1, state.shelfStock[shelf.id] ?? 0),
				marketPrice: product.suggestedPrice,
				necessity: Math.min(
					100,
					product.demand *
						turn.necessityMultiplier(product.category) *
						getSlotPositionFactor(shelf.id) *
						(1 + getFixtureAttraction(state, getPhysicalShelfId(shelf.id))),
				),
				productId: product.id,
				promotionRate: 0,
				visualAttractiveness:
					(product.visualAttractiveness ?? 0) +
					getProductLevel(state.productLevels, product.id) * ATTRACTIVENESS_PER_LEVEL,
				sellingPrice: state.shelfPrices[shelf.id] ?? product.sellingPrice,
				shelfId: shelf.id,
			},
		];
	});
	const onSale = products;
	const forecast = forecastDay({
		level: state.market.level,
		unlockedProductCount: state.market.unlockedProductIds.length,
		arrivalMultiplier:
			shopEffects.customerArrivalMultiplier *
			employeeEffects.customerArrivalMultiplier *
			turn.customerArrivalMultiplier *
			getLoyaltyArrivalMultiplier(state.day.loyalty),
		minArrivalDelayMs: turn.minArrivalDelayMs / shopEffects.customerCapacityMultiplier,
		products: onSale,
		purchasePrice: (productId) => itemCatalog.find((item) => item.id === productId)?.purchasePrice ?? 0,
		budgetMultiplier:
			(1 + Math.max(state.market.level - 1, 0) * 0.08) *
			shopEffects.customerBudgetMultiplier *
			turn.budgetMultiplier,
		maxProductsBonus: shopEffects.maxProductsBonus + getEraEffects(state.era.id).basketBonus,
		revenueMultiplier: shopEffects.revenueMultiplier,
		categoryRevenueBonuses: shopEffects.categoryRevenueBonuses,
		storeReputation:
			state.market.customerSatisfaction +
			shopEffects.storeReputationBonus +
			employeeEffects.storeReputationBonus,
	});
	if (onSale.length > 0) return forecast;
	// Empty shelves (a brand-new market): the customers are real, the basket is the usual first one.
	const fallback = getFallbackDayForecast(state.market.level);
	const scale = forecast.customers / Math.max(1, fallback.customers);
	return {
		...forecast,
		buyers: fallback.buyers * scale,
		revenue: fallback.revenue * scale,
		profit: fallback.profit * scale,
		units: fallback.units * scale,
	};
}

function getCurrentShelfSlotCounts(
	state: Pick<GameState, "shelfSlotCounts" | "unlockedShelfSlots">,
) {
	return resolveShelfSlotCounts(
		state.shelfSlotCounts,
		state.unlockedShelfSlots,
	);
}

function isShelfUnlocked(
	shelfId: string,
	shelfSlotCounts: GameShelfSlotCounts | number,
) {
	return isShelfSlotUnlocked(shelfId, shelfSlotCounts);
}

function canAddToInventory(
	productId: number,
	quantity: number,
	inventory: GameInventory,
	inventoryCapacityLevels: GameInventoryCapacityLevels,
) {
	const product = itemCatalog.find((item) => item.id === productId);

	if (!product) {
		return false;
	}

	return (
		(inventory[productId] ?? 0) + quantity <=
		getInventoryCapacity(product, inventoryCapacityLevels[productId])
	);
}

function normalizeInventoryCapacityLevels(
	inventoryCapacityLevels: Partial<GameInventoryCapacityLevels> | undefined,
) {
	return Object.fromEntries(
		Object.entries(inventoryCapacityLevels ?? {}).flatMap(
			([productId, upgradeLevel]) => {
				const normalizedLevel = normalizeInventoryCapacityLevel(upgradeLevel);

				return normalizedLevel > 0
					? [[Number(productId), normalizedLevel]]
					: [];
			},
		),
	) as GameInventoryCapacityLevels;
}

function normalizeShelfPrices(
	shelfPrices: Partial<GameShelfPrices> | undefined,
	shelfAssignments: GameShelfAssignments,
) {
	const nextShelfPrices: GameShelfPrices = {};

	for (const shelf of shelfProductSlots) {
		const product = itemCatalog.find(
			(item) => item.id === shelfAssignments[shelf.id],
		);

		if (!product) {
			continue;
		}

		const persistedPrice = shelfPrices?.[shelf.id];

		if (
			typeof persistedPrice !== "number" ||
			!Number.isFinite(persistedPrice)
		) {
			nextShelfPrices[shelf.id] = product.sellingPrice;
			continue;
		}

		nextShelfPrices[shelf.id] = Math.min(
			product.maxPrice,
			Math.max(product.minPrice, Math.round(persistedPrice)),
		);
	}

	return nextShelfPrices;
}

function createMarketCustomer(
	visit: ReturnType<typeof simulateMarketVisit>,
	seed: number,
	shelfPrices: GameShelfPrices,
	marketSatisfaction: number,
): GameMarketCustomer {
	const profile = customerProfiles[visit.customer.archetype];
	const name = profile.names[seed % profile.names.length];
	const purchasedProducts = visit.purchases
		.reduce<string[]>((products, purchase) => {
			const product = itemCatalog.find(
				(item) => item.id === purchase.productId,
			);

			if (product) {
				products.push(product.name);
			}

			return products;
		}, [])
		.join(" e ");
	const averagePriceDifference = visit.purchases.length
		? visit.purchases.reduce((total, purchase) => {
				const product = itemCatalog.find(
					(item) => item.id === purchase.productId,
				);
				const price =
					shelfPrices[purchase.shelfId] ?? product?.sellingPrice ?? 0;

				return total + (price - (product?.suggestedPrice ?? price));
			}, 0) / visit.purchases.length
		: 0;
	const moodBonus = {
		calmo: 2,
		"com-pressa": -4,
		feliz: 8,
		estressado: -9,
	}[visit.customer.mood];
	const satisfaction = Math.round(
		Math.min(
			100,
			Math.max(
				0,
				marketSatisfaction * 0.35 +
					(visit.purchases.length > 0 ? 46 : 17) +
					moodBonus -
					averagePriceDifference * visit.customer.priceSensitivity,
			),
		),
	);

	return {
		id: `${visit.customer.id}-${seed}`,
		purchases: visit.purchases,
		item: purchasedProducts || "Não encontrou produtos",
		mood: visit.customer.mood,
		name,
		satisfaction,
		spent: visit.revenue,
		status: visit.revenue > 0 ? "pagou" : "saiu sem comprar",
	};
}

// Money, XP and sales of a paid basket (the register is where revenue is booked).
/** The "Carrinhos de Compras" upgrade became the cart corral placed on the map: who bought it gets one. */
function withCartsFromShop(interior: InteriorState, ownedItemIds: string[] | undefined): InteriorState {
	if (!ownedItemIds?.includes("simple-cart") || (interior.owned["cart-corral"] ?? 0) > 0) return interior;
	return { ...interior, owned: { ...interior.owned, "cart-corral": 1 } };
}

/**
 * "Cestinhas de Mão" and "Carrinhos Grandes" (shop upgrades) became stations placed on the map (30/10): who bought
 * them gets the station in the build-mode inventory ("Para colocar"). Idempotent: an owner already holding the
 * station gets nothing more.
 */
function withCartStations(interior: InteriorState, ownedItemIds: string[] | undefined): InteriorState {
	const owned = { ...interior.owned };
	let changed = false;
	for (const [itemId, station] of [
		["shopping-basket", "basket-station"],
		["large-cart", "big-cart-corral"],
	] as const)
		if (ownedItemIds?.includes(itemId) && (owned[station] ?? 0) <= 0) {
			owned[station] = 1;
			changed = true;
		}
	return changed ? { ...interior, owned } : interior;
}

function applyCheckoutPayment(
	state: GameState,
	payment: CheckoutPayment,
	now: number,
): Partial<GameState> {
	const { checkout, revenue, tip } = payment;
	const { market } = state;
	const daily = markDailySale(
		normalizeDailyState(state.daily, market.level, now),
		revenue,
		0,
		checkout.units,
	);
	const progression = applyExperience(
		market.level,
		market.experience,
		checkout.experience,
	);
	const unlockedProductIds = Array.from(
		new Set([
			...market.unlockedProductIds,
			...getUnlockedProductIds(progression.level, state.era.id),
		]),
	);
	const recentUnlockProductIds = unlockedProductIds.filter(
		(productId) => !market.unlockedProductIds.includes(productId),
	);
	const soldByProduct = { ...market.soldByProduct };
	for (const [productId, quantity] of Object.entries(checkout.soldByProduct))
		soldByProduct[Number(productId)] =
			(soldByProduct[Number(productId)] ?? 0) + quantity;
	return {
		checkout: payment.state,
		coins: state.coins + revenue + tip,
		// Rankings v1: each customer who bought is a league point.
		rankings: addLeaguePoints(state.rankings, LEAGUE_POINTS.customer, now),
		daily,
		day: recordDaySale(state.day, {
			categories: checkout.categories,
			profit: checkout.profit - (checkout.total - revenue),
			revenue,
			units: checkout.units,
		}),
		lastSessionAt: now,
		market: {
			...market,
			customerSatisfaction: clampSatisfaction(
				market.customerSatisfaction + payment.satisfactionDelta,
			),
			customersWhoBought: market.customersWhoBought + 1,
			experience: progression.experience,
			lastExperienceGain: checkout.experience,
			level: progression.level,
			recentCustomers: market.recentCustomers.map((customer) =>
				customer.id === checkout.customerId
					? { ...customer, spent: revenue, status: "pagou" as const }
					: customer,
			),
			recentUnlockProductIds:
				recentUnlockProductIds.length > 0
					? recentUnlockProductIds
					: market.recentUnlockProductIds,
			soldByProduct,
			todayRevenue: daily.revenue,
			totalExperience: market.totalExperience + checkout.experience,
			totalRevenue: market.totalRevenue + revenue,
			unitsSold: market.unitsSold + checkout.units,
			unlockedProductIds,
		},
	};
}

// A sale outside the register (a drink handed through a car window): the same money, XP and sales
// records as a paid basket of one unit.
function applyStreetSale(
	state: GameState,
	product: { id: number; category: string; purchasePrice: number },
	price: number,
	tip: number,
	experience: number,
	now: number,
): Partial<GameState> {
	const { market } = state;
	const daily = markDailySale(normalizeDailyState(state.daily, market.level, now), price, 0, 1);
	const progression = applyExperience(market.level, market.experience, experience);
	const unlockedProductIds = Array.from(
		new Set([...market.unlockedProductIds, ...getUnlockedProductIds(progression.level, state.era.id)]),
	);
	const recentUnlockProductIds = unlockedProductIds.filter((productId) => !market.unlockedProductIds.includes(productId));
	return {
		coins: state.coins + price + tip,
		daily,
		day: recordDaySale(state.day, {
			categories: { [product.category]: 1 },
			profit: price - product.purchasePrice,
			revenue: price,
			units: 1,
		}),
		lastSessionAt: now,
		market: {
			...market,
			experience: progression.experience,
			lastExperienceGain: experience,
			level: progression.level,
			recentUnlockProductIds: recentUnlockProductIds.length > 0 ? recentUnlockProductIds : market.recentUnlockProductIds,
			soldByProduct: { ...market.soldByProduct, [product.id]: (market.soldByProduct[product.id] ?? 0) + 1 },
			todayRevenue: daily.revenue,
			totalExperience: market.totalExperience + experience,
			totalRevenue: market.totalRevenue + price,
			unitsSold: market.unitsSold + 1,
			unlockedProductIds,
		},
	};
}

// Abandoned baskets: items return to their shelf (or storage if the shelf changed product).
function returnAbandonedCheckouts(
	state: GameState,
	expired: {
		expired: PendingCheckout[];
		satisfactionDelta: number;
		state: GameState["checkout"];
	},
	now: number,
): Partial<GameState> {
	const shelfStock = { ...state.shelfStock };
	const inventory = { ...state.inventory };
	const inventoryLots = { ...state.inventoryLots };
	for (const checkout of expired.expired)
		for (const item of checkout.items) {
			if (state.shelfAssignments[item.shelfId] === item.productId)
				shelfStock[item.shelfId] = (shelfStock[item.shelfId] ?? 0) + item.quantity;
			else {
				inventory[item.productId] = (inventory[item.productId] ?? 0) + item.quantity;
				inventoryLots[item.productId] = reconcileInventoryLots(
					item.productId,
					inventory[item.productId],
					inventoryLots[item.productId],
					now,
				);
			}
		}
	const left = new Set(expired.expired.map((checkout) => checkout.customerId));
	return {
		checkout: expired.state,
		day: recordDayCheckoutLost(state.day, expired.expired.length),
		inventory,
		inventoryLots,
		market: {
			...state.market,
			customerSatisfaction: clampSatisfaction(
				state.market.customerSatisfaction + expired.satisfactionDelta,
			),
			recentCustomers: state.market.recentCustomers.map((customer) =>
				left.has(customer.id)
					? { ...customer, spent: 0, status: "saiu sem comprar" as const }
					: customer,
			),
		},
		shelfStock,
	};
}

function clampSatisfaction(value: number) {
	return Math.round(Math.min(100, Math.max(0, value)) * 10) / 10;
}

const customerProfiles: Record<CustomerArchetype, { names: string[] }> = {
	economico: { names: ["Ana", "Paula", "Rita"] },
	familia: { names: ["Marcos", "Davi", "Lucas"] },
	impulsivo: { names: ["Bia", "Nina", "Lara"] },
	normal: { names: ["Caio", "Igor", "Pedro"] },
	premium: { names: ["Helena", "Clara", "Sofia"] },
};

/** Passive event wear is applied in steps of a few seconds (fewer saves, same total). */
const PASSIVE_WEAR_TICK_MS = 5_000;

/** Fixtures that need power (besides the sector counters and the drinks fridge). */
const POWERED_FIXTURES = ["dairy", "pizza", "icecream"];

// Delivery (src/services/delivery.ts): the price a product has on its shelf now (the base price without one).
function getDeliveryPrice(state: GameState, productId: number) {
	const product = itemCatalog.find((item) => item.id === productId);
	const slot = shelfProductSlots.find((item) => state.shelfAssignments[item.id] === productId);
	return (slot ? state.shelfPrices[slot.id] : undefined) ?? product?.sellingPrice ?? 0;
}

// Products the market sells that are in the stockroom now: the lines an order can ask for.
function getDeliveryStock(state: GameState) {
	return state.market.unlockedProductIds.flatMap((productId) => {
		const units = state.inventory[productId] ?? 0;
		return units > 0 ? [{ productId, units, price: getDeliveryPrice(state, productId) }] : [];
	});
}

// A delivered bag is a sale: its units and their experience count like the sales at the register.
function creditDeliverySales(
	market: GameState["market"],
	eraId: GameState["era"]["id"],
	packed: DeliveryItem[],
	goods: number,
): GameState["market"] {
	const units = packed.reduce((total, item) => total + item.quantity, 0);
	const experience = packed.reduce(
		(total, item) => total + (itemCatalog.find((product) => product.id === item.productId)?.xpPerSale ?? 0) * item.quantity,
		0,
	);
	const progression = applyExperience(market.level, market.experience, experience);
	const unlockedProductIds = Array.from(
		new Set([...market.unlockedProductIds, ...getUnlockedProductIds(progression.level, eraId)]),
	);
	const recentUnlockProductIds = unlockedProductIds.filter((productId) => !market.unlockedProductIds.includes(productId));
	const soldByProduct = { ...market.soldByProduct };
	for (const item of packed) soldByProduct[item.productId] = (soldByProduct[item.productId] ?? 0) + item.quantity;
	return {
		...market,
		experience: progression.experience,
		lastExperienceGain: experience,
		level: progression.level,
		recentUnlockProductIds: recentUnlockProductIds.length > 0 ? recentUnlockProductIds : market.recentUnlockProductIds,
		soldByProduct,
		totalExperience: market.totalExperience + experience,
		totalRevenue: market.totalRevenue + goods,
		unitsSold: market.unitsSold + units,
		unlockedProductIds,
	};
}

// A bag packed too late: the customer cancels, the rating drops and the streak ends.
function cancelLateDelivery(delivery: DeliveryState, order: DeliveryOrder): DeliveryState {
	return {
		...delivery,
		orders: trimDeliveryOrders(replaceDeliveryOrder(delivery.orders, { ...order, status: "cancelado" })),
		rating: applyLateCancelToRating(delivery.rating),
		streak: 0,
	};
}

const eraPosition = (id: MarketEraId) => marketEras.findIndex((era) => era.id === id);

/**
 * Open fixtures and the categories on them. With `poweredOnly`, only what runs on power: the dairy
 * display, the freezers, the sector counters, and the drinks fridge (before the container it is a
 * styrofoam box with ice, which a power cut does not touch).
 */
function getEventFixtures(state: GameState, poweredOnly: boolean): EventFixture[] {
	const counts = getCurrentShelfSlotCounts(state);
	const fixtures = new Map<string, Set<string>>();
	for (const slot of shelfProductSlots) {
		if (!isShelfUnlocked(slot.id, counts)) continue;
		const id = getPhysicalShelfId(slot.id);
		const categories = fixtures.get(id) ?? new Set<string>();
		fixtures.set(id, categories);
		const product = itemCatalog.find((item) => item.id === state.shelfAssignments[slot.id]);
		if (product) categories.add(product.category);
	}
	const powered = (id: string) =>
		POWERED_FIXTURES.includes(id) ||
		isSectorShelfId(id) ||
		(id === "drinks" && eraPosition(state.era.id) >= eraPosition("conteiner"));
	return Array.from(fixtures, ([id, categories]) => ({ id, categories: Array.from(categories) })).filter(
		(fixture) => !poweredOnly || powered(fixture.id),
	);
}

/** What the market has, so only events that make sense are drawn. */
export function getGameEventContext(state: GameState): GameEventContext {
	return {
		eraId: state.era.id,
		hasWorkingStaff: state.employees.employees.some((employee) => employee.isWorking),
		hasRefrigeration: getEventFixtures(state, true).some((fixture) => fixture.categories.length > 0),
	};
}

/** Viralizou!: the influencer films one of the products on sale (stocked right now). */
function withFeaturedProduct(events: GameEventsState, state: GameState): GameEventsState {
	const active = events.activeEvent;
	if (!active || active.featuredProductId !== undefined) return events;
	if ((getGameEvent(active.eventId)?.effects.featuredProductBoost ?? 1) === 1) return events;
	const onSale = shelfProductSlots.flatMap((slot) => {
		const productId = state.shelfAssignments[slot.id];
		return productId && (state.shelfStock[slot.id] ?? 0) > 0 ? [productId] : [];
	});
	const featuredProductId = pickFeaturedProduct(onSale, events.randomSeed);
	return featuredProductId === undefined ? events : { ...events, activeEvent: { ...active, featuredProductId } };
}
