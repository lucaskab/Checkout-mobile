import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
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
import type { GameEventsState } from "@/@types/game-event";
import type { GameInventoryLots, GameShelfLots } from "@/@types/inventory-lot";
import type { LogisticsState, SupplierOrder } from "@/@types/logistics";
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
import { getMission } from "@/data/missions";
import {
	getProductionSector,
	productionRecipes,
} from "@/data/production-sectors";
import {
	getNextShelfCapacityUpgrade,
	getNextShelfSlotUpgrade,
	getNextShelfUnlockUpgrade,
	getShelfCapacity,
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
import { shopItems } from "@/data/shop-items";
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
	nextAutoCheckout,
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
	acceptsCustomers,
	addSpecialRequest,
	advanceMarketDay,
	closeMarketDay,
	createInitialDayState,
	createSpecialRequest,
	expireSpecialRequests,
	FREE_DAY_CONTRACT_ID,
	getLoyaltyArrivalMultiplier,
	isDayOver,
	normalizeDayState,
	recordDayCheckoutLost,
	recordDayCustomer,
	recordDayIncidentFixed,
	recordDaySale,
	resolveSpecialRequest as resolveDayRequest,
	startDay as startMarketDay,
} from "@/services/market-day";
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
	createInitialGameEventsState,
	getActiveGameEventEffects,
	normalizeGameEventsState,
} from "@/services/game-events";
import {
	appendInventoryLots,
	createInventoryLots,
	discardExpiredInventoryLots,
	reconcileInventoryLots,
	takeInventoryLots,
} from "@/services/inventory-lots";
import {
	getSupplierDeliveryDuration,
	getSupplierOrderStatus,
} from "@/services/logistics";
import { getMissionProgress } from "@/services/missions";
import {
	getProductionDiamondCost,
	getSupplierOrderPrice,
} from "@/services/production";
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
import { getMarketEra, STARTING_COINS } from "@/data/economy";
import { canShelfHold } from "@/data/shelf-categories";
import { getSectorCounterFor, shelfTypes } from "@/data/shelf-types";
import {
	getCareFactor,
	getShelfCondition,
	getSlotPositionFactor,
	normalizeShelfCare,
	wearShelfCare,
} from "@/services/shelf-care";
import { albumCollections, getCollectionProgress } from "@/data/product-album";
import { ERA_LOTS, getMarketLot } from "@/data/market-lots";
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
	isBuiltShopItem,
	normalizeBuiltSectorIds,
	normalizeInteriorConstructions,
	sectorBuildPlans,
	shopItemBuildDurations,
} from "@/data/interior-construction";

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
	builtSectorIds: [],
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
};

function getInitialGameState(): GameState {
	return {
		era: createInitialEraState(),
		productLevels: {},
		dailyLogin: createDailyLoginState(),
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
		builtSectorIds: [],
		missions: {
			claimedMissionIds: [...initialGameState.missions.claimedMissionIds],
		},
		production: {
			...initialGameState.production,
			jobs: [...initialGameState.production.jobs],
		},
		shop: {
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
		shelfUpgradeLevels,
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
	const shop = {
		...initialGameState.shop,
		...state.shop,
		consumableAmounts: {
			...initialGameState.shop.consumableAmounts,
			...state.shop?.consumableAmounts,
		},
		ownedItemIds:
			state.shop?.ownedItemIds ?? initialGameState.shop.ownedItemIds,
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
		weeklyEvent: normalizeWeeklyEventState(state.weeklyEvent),
		// Saves from before the land get the lots their expansion already stands on.
		lots: normalizeLotsState(
			state.lots,
			normalizeEraState(state.era, state.era ? "mesinha" : getEraForExpansions(unlockedMarketExpansionIds)).id,
		),
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
		interior: normalizeInteriorState(state.interior),
		interiorConstructions,
		builtSectorIds,
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
	};
}

export const useGameStore = create<GameStore>()(
	persist(
		(set, get) => ({
			...getInitialGameState(),
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
				const shopEffects = getShopEffects(state.shop.ownedItemIds);
				// Obras keep going while the player is away.
				get().processMarketEraConstruction(now);
				// The market keeps selling while the player is away (if it was left open): every hour
				// is worth part of a played turn, more in bigger eras (see data/economy.ts).
				const averageTicket =
					state.market.customersWhoBought > 0
						? state.market.totalRevenue / state.market.customersWhoBought
						: 18;
				const away = state.market.isOpen
					? getOfflineEraIncome(get().era, elapsedMs, averageTicket)
					: null;
				const customers = away?.customers ?? 0;
				const offlineCoins = Math.floor(
					(away?.coins ?? 0) * shopEffects.offlineRevenueMultiplier,
				);
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

				if (logistics.premiumCurrency < 3) {
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
					(currency === "diamonds" &&
						logistics.premiumCurrency < nextUpgrade.diamondCost)
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
			completeOrderFinalStage: (orderId) => {
				const {
					inventory,
					inventoryCapacityLevels,
					inventoryLots,
					logistics,
					statistics,
				} = get();
				const order = logistics.orders.find((item) => item.id === orderId);
				const now = Date.now();

				if (
					!order ||
					order.status === "entregue" ||
					logistics.premiumCurrency < 2 ||
					now < order.createdAt + order.deliveryDurationMs / 2 ||
					!canAddToInventory(
						order.productId,
						order.quantity,
						inventory,
						inventoryCapacityLevels,
					)
				) {
					return false;
				}

				set({
					inventory: {
						...inventory,
						[order.productId]:
							(inventory[order.productId] ?? 0) + order.quantity,
					},
					inventoryLots: {
						...inventoryLots,
						[order.productId]: appendInventoryLots(
							inventoryLots[order.productId],
							createInventoryLots(order.productId, order.quantity, now),
						),
					},
					logistics: {
						...logistics,
						orders: logistics.orders.map((item) =>
							item.id === orderId
								? { ...item, deliveredAt: now, status: "entregue" }
								: item,
						),
						premiumCurrency: logistics.premiumCurrency - 2,
					},
					statistics: {
						...statistics,
						instantDeliveries: statistics.instantDeliveries + 1,
					},
				});

				return true;
			},
			claimMission: (missionId) => {
				const state = get();
				const mission = getMission(missionId);

				if (
					!mission ||
					state.market.level < mission.requiredLevel ||
					state.missions.claimedMissionIds.includes(mission.id) ||
					getMissionProgress(mission, state) < mission.goal
				) {
					return false;
				}

				const inventory = { ...state.inventory };
				const inventoryLots = { ...state.inventoryLots };

				for (const item of mission.reward.items ?? []) {
					if (
						!canAddToInventory(
							item.productId,
							item.quantity,
							inventory,
							state.inventoryCapacityLevels,
						)
					) {
						return false;
					}

					inventory[item.productId] =
						(inventory[item.productId] ?? 0) + item.quantity;
					inventoryLots[item.productId] = appendInventoryLots(
						inventoryLots[item.productId],
						createInventoryLots(item.productId, item.quantity),
					);
				}

				set({
					coins: state.coins + mission.reward.coins,
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
			deliverOrderInstantly: (orderId) => {
				const {
					inventory,
					inventoryCapacityLevels,
					inventoryLots,
					logistics,
					statistics,
				} = get();
				const order = logistics.orders.find((item) => item.id === orderId);
				const now = Date.now();

				if (
					!order ||
					order.status === "entregue" ||
					!canAddToInventory(
						order.productId,
						order.quantity,
						inventory,
						inventoryCapacityLevels,
					)
				) {
					return false;
				}

				const canUseToken = logistics.emergencyTokens > 0;
				const canUseCurrency = logistics.premiumCurrency >= 5;

				if (!canUseToken && !canUseCurrency) {
					return false;
				}

				set({
					inventory: {
						...inventory,
						[order.productId]:
							(inventory[order.productId] ?? 0) + order.quantity,
					},
					inventoryLots: {
						...inventoryLots,
						[order.productId]: appendInventoryLots(
							inventoryLots[order.productId],
							createInventoryLots(order.productId, order.quantity, now),
						),
					},
					logistics: {
						...logistics,
						emergencyTokens: canUseToken
							? logistics.emergencyTokens - 1
							: logistics.emergencyTokens,
						orders: logistics.orders.map((item) =>
							item.id === orderId
								? { ...item, deliveredAt: now, status: "entregue" }
								: item,
						),
						premiumCurrency: canUseToken
							? logistics.premiumCurrency
							: logistics.premiumCurrency - 5,
					},
					statistics: {
						...statistics,
						instantDeliveries: statistics.instantDeliveries + 1,
					},
				});

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
				const nextEvents = activateGameEvent(events, eventId, now);

				if (!nextEvents) {
					return false;
				}

				const eventEffects = getActiveGameEventEffects(nextEvents, now);
				const shopEffects = getShopEffects(shop.ownedItemIds);
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
										getTurnEffects(get().era.id, get().day.shift).minArrivalDelayMs,
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
						{ id: `dev-${now}`, productId, quantity: units },
						{ category: product.category, name: product.name },
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
				const cost = getMarketExpansionSkipCost(era.construction.endsAt - Date.now());
				if (logistics.premiumCurrency < cost) return false;
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
				const cost = getMarketExpansionSkipCost(lots.clearing.endsAt - Date.now());
				if (get().logistics.premiumCurrency < cost) return false;
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
				set({ lots: next });
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
				const dock = receiving.dock.filter((item) => !item.orderId.startsWith("dev-"));
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
					logistics.premiumCurrency < diamondCost ||
					!canAddToInventory(
						job.outputProductId,
						job.outputQuantity,
						inventory,
						inventoryCapacityLevels,
					)
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
			placeSupplierOrder: ({
				productId,
				quantity,
				useFreightCoupon = false,
			}) => {
				const {
					coins,
					events,
					inventory,
					inventoryCapacityLevels,
					logistics,
					statistics,
				} = get();
				const shopEffects = getShopEffects(get().shop.ownedItemIds);
				const product = itemCatalog.find((item) => item.id === productId);
				const now = Date.now();
				const activeOrders = logistics.orders.filter(
					(order) => getSupplierOrderStatus(order, now) !== "entregue",
				);
				const hasCoupon = useFreightCoupon && logistics.freightCoupons > 0;
				const eventEffects = getActiveGameEventEffects(events, now);
				const supplierOrderPrice = Math.ceil(
					getSupplierOrderPrice(productId, quantity) *
						eventEffects.supplierCostMultiplier *
						shopEffects.supplierCostMultiplier,
				);
				const incomingQuantity = logistics.orders
					.filter(
						(order) =>
							order.productId === productId &&
							getSupplierOrderStatus(order, now) !== "entregue",
					)
					.reduce((total, order) => total + order.quantity, 0);
				const discountedCost = hasCoupon
					? Math.ceil(supplierOrderPrice * 0.9)
					: supplierOrderPrice;

				if (
					!product ||
					quantity <= 0 ||
					supplierOrderPrice <= 0 ||
					!canAddToInventory(
						productId,
						quantity + incomingQuantity,
						inventory,
						inventoryCapacityLevels,
					) ||
					coins < discountedCost ||
					activeOrders.length >= logistics.supplierOrderSlots
				) {
					return false;
				}

				const order: SupplierOrder = {
					createdAt: now,
					deliveryDurationMs: Math.round(
						getSupplierDeliveryDuration(product.supplierTime, logistics, now) *
							eventEffects.supplierDurationMultiplier *
							shopEffects.supplierDurationMultiplier,
					),
					deliveredAt: null,
					id: `${productId}-${now}`,
					productId,
					quantity,
					status: "em-producao",
					totalCost: discountedCost,
				};

				set({
					coins: coins - discountedCost,
					logistics: {
						...logistics,
						freightCoupons: hasCoupon
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
			purchaseShopItem: (itemId, currency) => {
				const { coins, logistics, market, shop, statistics } = get();
				const item = shopItems.find((shopItem) => shopItem.id === itemId);

				if (!item || market.level < item.level) {
					return false;
				}

				if (!item.isConsumable && shop.ownedItemIds.includes(item.id)) {
					return false;
				}

				// Fixtures (second checkout, self-checkout) are installed by the builders.
				const installed = isBuiltShopItem(item.id);
				const interiorConstructions = get().interiorConstructions;
				if (installed && findInteriorConstruction(interiorConstructions, "shop", item.id)) {
					return false;
				}

				if (
					(currency === "coins" &&
						(!item.coinPrice || coins < item.coinPrice)) ||
					(currency === "diamonds" &&
						(!item.diamondPrice ||
							logistics.premiumCurrency < item.diamondPrice))
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
						consumableAmounts: item.isConsumable
							? {
									...shop.consumableAmounts,
									[item.id]: (shop.consumableAmounts[item.id] ?? 0) + 1,
								}
							: shop.consumableAmounts,
						ownedItemIds:
							item.isConsumable || installed
								? shop.ownedItemIds
								: [...shop.ownedItemIds, item.id],
					},
					// Bought fixtures wait in the inventory until the player places them.
					interiorConstructions: installed
						? [
								...interiorConstructions,
								createPendingConstruction("shop", item.id, shopItemBuildDurations[item.id]),
							]
						: interiorConstructions,
					statistics: {
						...statistics,
						shopPurchases: statistics.shopPurchases + 1,
					},
				});

				return true;
			},
			processGameEvents: () => {
				const { employees, events, market, shop } = get();
				const now = Date.now();
				const nextEvents = advanceGameEvents(events, now);

				if (!nextEvents) {
					return false;
				}

				const eventEffects = getActiveGameEventEffects(nextEvents, now);
				const shopEffects = getShopEffects(shop.ownedItemIds);
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
										getTurnEffects(get().era.id, get().day.shift).minArrivalDelayMs,
									),
							}
						: market,
				});

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
							const capacity = getShelfCapacity(
								state.shelfUpgradeLevels[getPhysicalShelfId(task.slotId)],
							);
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
					restockMultiplier: getShopEffects(state.shop.ownedItemIds).restockMultiplier,
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
						const product = itemCatalog.find((item) => item.id === order.productId);
						hasChanges = true;
						nextReceiving = addDockDelivery(
							nextReceiving,
							order,
							{ category: product?.category ?? "", name: product?.name ?? "Produto" },
							now,
						);
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
				const room =
					getInventoryCapacity(product, state.inventoryCapacityLevels[product.id]) -
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
			startProduction: ({ recipeId, sectorId }) => {
				const {
					events,
					inventory,
					inventoryCapacityLevels,
					market,
					production,
					statistics,
				} = get();
				const shopEffects = getShopEffects(get().shop.ownedItemIds);
				const sector = getProductionSector(sectorId);
				const recipe = productionRecipes.find(
					(item) => item.id === recipeId && item.sectorId === sectorId,
				);

				if (
					!sector ||
					!recipe ||
					!get().builtSectorIds.includes(sector.id) ||
					market.level < sector.requiredLevel ||
					market.level < recipe.requiredLevel
				) {
					return false;
				}

				const usedSlots = new Set(
					production.jobs
						.filter((job) => job.sectorId === sectorId)
						.map((job) => job.slotIndex),
				);
				const slotIndex = Array.from(
					{ length: sector.slotCount },
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
						recipe.outputQuantity + queuedOutput,
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
								shopEffects.productionDurationMultiplier,
						),
					id: `${sectorId}-${recipeId}-${now}`,
					outputProductId: recipe.outputProductId,
					outputQuantity: recipe.outputQuantity,
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
				const shopEffects = getShopEffects(shop.ownedItemIds);
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

				// A new week starts counting the weekly event's sales from here.
				const weekly = syncWeeklyEvent(get().weeklyEvent, market.soldByProduct, now);
				if (weekly !== get().weeklyEvent) set({ weeklyEvent: weekly });
				// Store mishaps: a broken freezer blocks its shelf, a wrong tag sells at half
				// price, and every open incident lowers the store's reputation.
				const incidentEffects = getIncidentEffects(get().incidents.active);
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
								marketPrice: product.suggestedPrice,
								// Night customers want drinks and snacks more. A tidy fixture and a spot at eye level
								// sell more (src/services/shelf-care.ts).
								necessity: Math.min(
									100,
									product.demand *
										getTurnEffects(get().era.id, get().day.shift).necessityMultiplier(product.category) *
										getWeeklyNecessityMultiplier(product.category, now) *
										getCareFactor(getShelfCondition(get().shelfCare, getPhysicalShelfId(shelf.id))) *
										getSlotPositionFactor(shelf.id),
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
											(incidentEffects.priceMultipliers[
												getPhysicalShelfId(shelf.id)
											] ?? 1),
									),
								),
								shelfId: shelf.id,
							},
						];
					});
				// A stall only has so many places on its table/crates: before the market building, only the
				// first products on display (in shelf order) are on sale.
				const onSale = isMarketBuilding(get().era.id)
					? availableProducts
					: availableProducts.slice(0, getMarketEra(get().era.id).productSlots);
				const plainVisit = simulateMarketVisit({
					budgetMultiplier:
						(1 + Math.max(market.level - 1, 0) * 0.08) *
						shopEffects.customerBudgetMultiplier *
						eventEffects.customerBudgetMultiplier *
						getTurnEffects(get().era.id, get().day.shift).budgetMultiplier,
					// Bigger markets: customers come with a basket, then a cart (more products each).
					maxProductsBonus:
						shopEffects.maxProductsBonus + getEraEffects(get().era.id).basketBonus,
					products: onSale,
					// Customers pay the shelf price: the era makes them richer (budget), never the goods dearer.
					revenueMultiplier: shopEffects.revenueMultiplier * eventEffects.revenueMultiplier,
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
				// Every product taken leaves its fixture a little messier (src/services/shelf-care.ts).
				const nextShelfCare = wearShelfCare(get().shelfCare, visit.purchases);

				const nextSeed = market.randomSeed + 1;
				const visitor = createMarketCustomer(
					visit,
					market.randomSeed,
					shelfPrices,
					market.customerSatisfaction - incidentEffects.reputationPenalty,
				);
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
				const specialRequest = createSpecialRequest(
					nextDay,
					{
						archetype: visit.customer.archetype,
						customerId: customer.id,
						customerName: customer.name,
						mood: customer.mood,
						seed: market.randomSeed,
					},
					getDayStoreContext({ ...get(), shelfStock: nextShelfStock }),
					now,
				);
				if (specialRequest) {
					nextDay = addSpecialRequest(nextDay, specialRequest);
				}
				set({
					checkout: checkout
						? enqueueCheckout(get().checkout, checkout)
						: get().checkout,
					daily: nextDaily,
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
								getTurnEffects(get().era.id, get().day.shift).minArrivalDelayMs,
							),
						recentCustomers: [customer, ...market.recentCustomers].slice(0, 3),
						randomSeed: nextSeed,
					},
					shelfStock: nextShelfStock,
					shelfLots: nextShelfLots,
					shelfCare: nextShelfCare,
				});

				get().processEmployeeWork();
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
				// A working cashier rings up the line without the player.
				const cashierEfficiency = get()
					.employees.employees.filter(
						(employee) => employee.isWorking && employee.role === "cashier",
					)
					.reduce((total, employee) => total + employee.efficiency, 0);
				const next = nextAutoCheckout(get().checkout, now, cashierEfficiency);
				if (next.state !== get().checkout) set({ checkout: next.state });
				if (next.checkoutId) {
					const payment = completeCheckoutRule(
						get().checkout,
						next.checkoutId,
						now,
						undefined,
						true,
					);
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
					!canShelfHold(getPhysicalShelfId(shelfId), product.category).ok ||
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
				const capacity = getShelfCapacity(
					shelfUpgradeLevels[getPhysicalShelfId(shelfId)],
				);

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
					return;
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
				const shopEffects = getShopEffects(shop.ownedItemIds);
				const employeeEffects = getEmployeeEffects(employees);
				let day = get().day;
				// Opening always happens inside a day: without a chosen contract it is a free day.
				// A finished day must be reviewed (claimDayResult) before the next one opens.
				if (isOpen && !market.isOpen) {
					if (day.phase === "results") return;
					if (day.phase === "planning") day = startMarketDay(day, null, now) ?? day;
				}
				const isOpening = isOpen && !market.isOpen;
				const isClosing = !isOpen && market.isOpen;
				let customerSatisfaction = market.customerSatisfaction;
				if (isClosing && day.phase === "open") {
					const closed = closeMarketDay(day, now, market.level);
					if (closed) {
						customerSatisfaction = clampSatisfaction(
							customerSatisfaction +
								closed.stats.reputationChange -
								day.stats.reputationChange,
						);
						day = closed;
					}
				}
				const firstCustomer =
					market.customersServed === 0 && market.recentCustomers.length === 0;
				const nextCustomerDelay = firstCustomer
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
							getTurnEffects(get().era.id, get().day.shift).minArrivalDelayMs,
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
				const nextDay = advanceMarketDay(
					day,
					progression.level,
					getDayStoreContext({ ...state, market: nextMarket }),
				);
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
			resolveSpecialRequest: (requestId, optionId) => {
				const state = get();
				const now = Date.now();
				const resolution = resolveDayRequest(
					state.day,
					requestId,
					optionId,
					now,
					state.market.level,
				);
				if (!resolution) return false;
				let { day } = resolution;
				let coins = state.coins + resolution.tip;
				let { daily, inventory, inventoryLots, market } = state;
				// "Buscar no depósito": sell one unit straight from storage.
				if (resolution.option.source === "stock" && resolution.option.productId) {
					const productId = resolution.option.productId;
					const product = itemCatalog.find((item) => item.id === productId);
					const available = inventory[productId] ?? 0;
					if (!product || available <= 0) return false;
					const lots = takeInventoryLots(
						reconcileInventoryLots(productId, available, inventoryLots[productId]),
						1,
					);
					const price = product.sellingPrice;
					inventory = { ...inventory, [productId]: available - 1 };
					inventoryLots = { ...inventoryLots, [productId]: lots.remainingLots };
					coins += price;
					daily = markDailySale(
						normalizeDailyState(daily, market.level, now),
						price,
						0,
						1,
					);
					market = {
						...market,
						soldByProduct: {
							...market.soldByProduct,
							[productId]: (market.soldByProduct[productId] ?? 0) + 1,
						},
						todayRevenue: daily.revenue,
						totalRevenue: market.totalRevenue + price,
						unitsSold: market.unitsSold + 1,
					};
					day = {
						...day,
						stats: {
							...day.stats,
							profit: day.stats.profit + price - product.purchasePrice,
							revenue: day.stats.revenue + price,
							soldByCategory: {
								...day.stats.soldByCategory,
								[product.category]:
									(day.stats.soldByCategory[product.category] ?? 0) + 1,
							},
							unitsSold: day.stats.unitsSold + 1,
						},
					};
				}
				set({
					coins,
					daily,
					day,
					inventory,
					inventoryLots,
					lastSessionAt: now,
					market: {
						...market,
						customerSatisfaction: clampSatisfaction(
							market.customerSatisfaction + resolution.satisfactionDelta,
						),
					},
				});
				return true;
			},
			processMarketDay: () => {
				const { day, market } = get();
				const now = Date.now();
				// Saves from before turns (or a desync) never leave an open market outside a day.
				if (market.isOpen && day.phase === "planning") {
					const started = startMarketDay(day, null, now);
					if (started) set({ day: started });
					return Boolean(started);
				}
				if (day.phase !== "open") return false;
				const expired = expireSpecialRequests(day, now);
				if (expired.expired.length > 0) {
					set({
						day: expired.day,
						market: {
							...market,
							customerSatisfaction: clampSatisfaction(
								market.customerSatisfaction + expired.satisfactionDelta,
							),
						},
					});
				}
				if (isDayOver(get().day, now)) {
					return get().closeDay();
				}
				return expired.expired.length > 0;
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
						unlockedProductIds: getUnlockedProductIds(nextLevel, get().era.id),
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
				const layout = getSimulatorLayout(state.unlockedMarketExpansionIds);
				const diamondCost = Math.max(1, Math.ceil(plan.coinCost / 1_500));
				if (
					state.builtSectorIds.includes(sector.id) ||
					findInteriorConstruction(state.interiorConstructions, "sector", sector.id) ||
					state.market.level < sector.requiredLevel ||
					getEraOrder(state.era.id) < getEraOrder(sector.eraId) ||
					// The sector needs the market wing that has room for it.
					!layout.sectorIds.includes(sector.id) ||
					(currency === "coins" && state.coins < plan.coinCost) ||
					(currency === "diamonds" &&
						state.logistics.premiumCurrency < diamondCost)
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
				for (const item of done) {
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
				if (logistics.premiumCurrency < diamondCost) return false;
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
			expandShelfSlots: (shelfId) => {
				const state = get();
				const physicalShelfId = getPhysicalShelfId(shelfId);
				const shelfSlotCounts = getCurrentShelfSlotCounts(state);
				const currentSlotCount = getShelfSlotCount(
					physicalShelfId,
					shelfSlotCounts,
				);
				const nextUpgrade = getNextShelfSlotUpgrade(currentSlotCount);

				if (
					currentSlotCount <= 0 ||
					!nextUpgrade ||
					state.market.level < nextUpgrade.playerLevel ||
					state.coins < nextUpgrade.coinCost
				) {
					return false;
				}

				const nextShelfSlotCounts = {
					...shelfSlotCounts,
					[physicalShelfId]: nextUpgrade.unlockedSlots,
				};

				set({
					coins: state.coins - nextUpgrade.coinCost,
					shelfSlotCounts: nextShelfSlotCounts,
					unlockedShelfSlots: getTotalUnlockedShelfSlots(nextShelfSlotCounts),
				});

				return true;
			},
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
					(currency === "diamonds" &&
						logistics.premiumCurrency < expansion.diamondCost)
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
				const useDiamonds = currency === "diamonds" || !decor.coinPrice;
				const price = useDiamonds ? decor.diamondPrice : decor.coinPrice;
				if (!price) return false;
				if (useDiamonds ? logistics.premiumCurrency < price : coins < price) return false;
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
			finishMarketExpansionNow: () => {
				const { logistics, marketExpansionConstruction } = get();
				if (!marketExpansionConstruction) {
					return false;
				}
				const diamondCost = getMarketExpansionSkipCost(
					marketExpansionConstruction.endsAt - Date.now(),
				);
				if (logistics.premiumCurrency < diamondCost) {
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
				const { coins, logistics, market, shelfUpgradeLevels } = get();
				const upgradeLevel = shelfUpgradeLevels[shelfId] ?? 0;
				const nextUpgrade = getNextShelfCapacityUpgrade(upgradeLevel);

				if (!nextUpgrade || market.level < nextUpgrade.playerLevel) {
					return false;
				}

				if (
					(currency === "coins" && coins < nextUpgrade.coinCost) ||
					(currency === "diamonds" &&
						logistics.premiumCurrency < nextUpgrade.diamondCost)
				) {
					return false;
				}

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
					shelfUpgradeLevels: {
						...shelfUpgradeLevels,
						[shelfId]: upgradeLevel + 1,
					},
				});

				return true;
			},
		}),
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
				let migrated = persistedState;
				if (version < 40) migrated = migrateCatalog40(migrated);
				if (version < 41) migrated = migrateFixtures41(migrated);
				return migrateGameState(migrated);
			},
			name: "checkout.game",
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
				builtSectorIds,
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
				albumClaimedIds,
				weeklyEvent,
				lots,
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
				builtSectorIds,
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
				albumClaimedIds,
				weeklyEvent,
				lots,
			}),
			storage: createJSONStorage(() => mmkvStorage),
			// 35: employees gained tasks/nextTaskNumber/lastPayroll (staff jobs and per-shift pay).
			// 36: shelves, sectors and fixtures are built over time (interiorConstructions, builtSectorIds).
			// 37: market eras (era: mesinha → rede); old saves start at the mercadinho or later.
			// 38: land (lots bought and cleared) and the fields of product levels, daily gift, album and weekly event.
			// 39: the land became a grid of 12 equal lots (A1–C4); old lot ids are mapped onto it.
			version: 41,
		},
	),
);

function normalizeShelfState(
	shelfStock: GameShelfStock,
	inventory: GameInventory,
	shelfUpgradeLevels: GameShelfUpgradeLevels,
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

		const capacity = getShelfCapacity(
			shelfUpgradeLevels[getPhysicalShelfId(shelf.id)],
		);

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
				capacity: getShelfCapacity(state.shelfUpgradeLevels[shelfId]),
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
