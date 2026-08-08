import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { GameStatistics } from "@/@types/achievement";
import type { EmployeeRole, GameEmployeesState } from "@/@types/employee";
import type { CurrencyPurchaseState } from "@/@types/currency-purchase";
import type { CustomerArchetype } from "@/@types/customer-simulation";
import type {
	GameInventory,
	GameInventoryCapacityLevels,
	GameMarketCustomer,
	GameMarketState,
	OfflineRewardSummary,
	GameShelfAssignments,
	GameShelfPrices,
	GameShelfStock,
	GameShelfUpgradeLevels,
	GameState,
	GameStore,
} from "@/@types/game";
import type { GameEventsState } from "@/@types/game-event";
import type { GameInventoryLots, GameShelfLots } from "@/@types/inventory-lot";
import type { LogisticsState, SupplierOrder } from "@/@types/logistics";
import type { GameMissionsState } from "@/@types/mission";
import type { GameProductionState, ProductionJob } from "@/@types/production";
import type { GameShopState } from "@/@types/shop";
import type { SupplierOrderSlotCurrency } from "@/@types/supplier-capacity";
import {
	getInventoryCapacity,
	getNextInventoryCapacityUpgrade,
	normalizeInventoryCapacityLevel,
} from "@/data/inventory-capacity";
import {
	getUnlockedProductIds,
	initialShelfAssignments,
	itemCatalog,
	marketProducts,
	shelves,
} from "@/data/market-products";
import { getMission } from "@/data/missions";
import { getEmployeeDefinition } from "@/data/employees";
import {
	getProductionSector,
	productionRecipes,
} from "@/data/production-sectors";
import {
	getNextShelfCapacityUpgrade,
	getNextShelfSlotUpgrade,
	getShelfCapacity,
	initialUnlockedShelfSlots,
	normalizeUnlockedShelfSlots,
} from "@/data/shelf-capacity";
import { shopItems } from "@/data/shop-items";
import {
	getCustomerArrivalDelay,
	simulateMarketVisit,
} from "@/services/customer-simulation";
import {
	getMarketExpansion,
	normalizeMarketExpansionIds,
} from "@/data/market-expansions";
import {
	getNextSupplierOrderSlotUpgrade,
	initialSupplierOrderSlots,
	normalizeSupplierOrderSlots,
} from "@/data/supplier-capacity";
import {
	activateGameEvent,
	advanceGameEvents,
	createInitialGameEventsState,
	getActiveGameEventEffects,
	normalizeGameEventsState,
} from "@/services/game-events";
import {
	getSupplierDeliveryDuration,
	getSupplierOrderStatus,
} from "@/services/logistics";
import { getMissionProgress } from "@/services/missions";
import {
	createInitialDailyState,
	markDailySale,
	normalizeDailyState,
} from "@/services/daily-progress";
import {
	getProductionDiamondCost,
	getSupplierOrderPrice,
} from "@/services/production";
import {
	applyExperience,
	getExperienceFromSales,
} from "@/services/progression";
import {
	EMPLOYEE_PAYROLL_INTERVAL_MS,
	getEmployeeEffects,
	getEmployeePayrollCost,
} from "@/services/employees";
import {
	getEmployeeTrainingCost,
	grantEmployeeExperience,
	trainEmployee as promoteEmployee,
} from "@/services/employee-progression";
import {
	appendInventoryLots,
	createInventoryLots,
	discardExpiredInventoryLots,
	reconcileInventoryLots,
	takeInventoryLots,
} from "@/services/inventory-lots";
import { getShopEffects } from "@/services/shop-effects";
import { mmkvStorage } from "@/storage/mmkv";

const initialInventory: GameInventory = {
	1: 9,
	5: 4,
	9: 14,
	12: 6,
	13: 8,
	15: 2,
	17: 3,
};

const initialInventoryCapacityLevels: GameInventoryCapacityLevels = {};

const initialInventoryLots: GameInventoryLots = {};

const initialShelfStock: GameShelfStock = {
	bakery: 3,
	dairy: 3,
	produce: 3,
	snacks: 3,
};

const initialShelfLots: GameShelfLots = {};

const initialAssignments: GameShelfAssignments = initialShelfAssignments;

const initialShelfPrices: GameShelfPrices = Object.fromEntries(
	marketProducts.flatMap((product) =>
		product.shelfId ? [[product.shelfId, product.sellingPrice]] : [],
	),
);

const initialShelfUpgradeLevels: GameShelfUpgradeLevels = {};

const initialShopState: GameShopState = {
	consumableAmounts: {},
	ownedItemIds: [],
};

const initialUnlockedMarketExpansionIds: GameState["unlockedMarketExpansionIds"] = [];

const initialProductionState: GameProductionState = {
	jobs: [],
	totalCrafted: 0,
};

const initialEmployeesState: GameEmployeesState = {
	employees: [],
	nextHireNumber: 1,
	nextPayrollAt: Date.now() + EMPLOYEE_PAYROLL_INTERVAL_MS,
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
	unlockedProductIds: getUnlockedProductIds(1),
};

const initialGameState: GameState = {
	coins: 1248,
	currencyPurchases: initialCurrencyPurchaseState,
	daily: createInitialDailyState(1),
	events: createInitialGameEventsState(),
	employees: initialEmployeesState,
	inventory: initialInventory,
	inventoryLots: initialInventoryLots,
	inventoryCapacityLevels: initialInventoryCapacityLevels,
	logistics: initialLogisticsState,
	market: initialMarketState,
	offlineSummary: null,
	lastSessionAt: Date.now(),
	unlockedMarketExpansionIds: initialUnlockedMarketExpansionIds,
	missions: initialMissionsState,
	production: initialProductionState,
	shop: initialShopState,
	shelfAssignments: initialAssignments,
	shelfLots: initialShelfLots,
	shelfStock: initialShelfStock,
	shelfPrices: initialShelfPrices,
	unlockedShelfSlots: initialUnlockedShelfSlots,
	shelfUpgradeLevels: initialShelfUpgradeLevels,
	statistics: initialStatistics,
};

function getInitialGameState(): GameState {
	return {
		coins: initialGameState.coins,
		currencyPurchases: {
			processedTransactionIds: [
				...initialGameState.currencyPurchases.processedTransactionIds,
			],
		},
		daily: createInitialDailyState(1),
		events: createInitialGameEventsState(),
		employees: {
			employees: initialGameState.employees.employees.map((employee) => ({
				...employee,
			})),
			nextHireNumber: initialGameState.employees.nextHireNumber,
			nextPayrollAt: Date.now() + EMPLOYEE_PAYROLL_INTERVAL_MS,
			totalSalariesPaid: 0,
		},
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
		unlockedShelfSlots: initialGameState.unlockedShelfSlots,
		shelfUpgradeLevels: { ...initialGameState.shelfUpgradeLevels },
		statistics: { ...initialGameState.statistics },
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
	const unlockedShelfSlots = normalizeUnlockedShelfSlots(
		state.unlockedShelfSlots,
	);
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
		unlockedShelfSlots,
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
	const supplierOrderSlots = normalizeSupplierOrderSlots(
		state.logistics?.supplierOrderSlots,
	);
	const daily = normalizeDailyState(state.daily, normalizedLevel);
	const previousTotalRevenue =
		market?.totalRevenue ?? market?.todayRevenue ?? 0;
	const lastSessionAt =
		typeof state.lastSessionAt === "number" && Number.isFinite(state.lastSessionAt)
			? state.lastSessionAt
			: Date.now();

	return {
		coins: state.coins ?? initialGameState.coins,
		currencyPurchases: {
			processedTransactionIds:
				state.currencyPurchases?.processedTransactionIds ??
				initialGameState.currencyPurchases.processedTransactionIds,
		},
		daily,
		events,
		employees,
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
					...getUnlockedProductIds(market?.level ?? 1),
					...(market?.unlockedProductIds ?? []),
				]),
			),
		},
		offlineSummary: state.offlineSummary ?? null,
		lastSessionAt,
		unlockedMarketExpansionIds,
		missions,
		production,
		shop,
		shelfAssignments,
		shelfLots,
		shelfStock: normalizedShelfState.shelfStock,
		shelfPrices,
		unlockedShelfSlots,
		shelfUpgradeLevels,
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
				const activeEmployees = state.employees.employees.filter(
					(employee) => employee.isWorking,
				).length;
				const customers = state.market.isOpen
					? Math.min(120, Math.floor(elapsedMs / 90_000) + activeEmployees)
					: 0;
				const averageRevenue =
					state.market.customersWhoBought > 0
						? state.market.totalRevenue / state.market.customersWhoBought
						: 18;
				const offlineCoins = Math.floor(
					customers * averageRevenue * shopEffects.offlineRevenueMultiplier,
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
					lastSessionAt: now,
					market: {
						...state.market,
						customersServed: state.market.customersServed + customers,
						customersWhoBought:
							state.market.customersWhoBought + customers,
						experience: progression.experience,
						level: progression.level,
						todayRevenue: nextDaily.revenue,
						totalExperience:
							state.market.totalExperience + customers * 2,
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
											employeeEffects.customerArrivalMultiplier,
									),
							}
						: market,
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
						nextHireNumber: employees.nextHireNumber + 1,
						nextPayrollAt: employees.nextPayrollAt,
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
						ownedItemIds: item.isConsumable
							? shop.ownedItemIds
							: [...shop.ownedItemIds, item.id],
					},
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
											employeeEffects.customerArrivalMultiplier,
									),
							}
						: market,
				});

				return true;
			},
			processEmployeeWork: () => {
				const {
					employees,
					inventory,
					inventoryLots,
					shelfAssignments,
					shelfLots,
					shelfStock,
					shelfUpgradeLevels,
					statistics,
					unlockedShelfSlots,
				} = get();
				const shopEffects = getShopEffects(get().shop.ownedItemIds);
				const restockAmount = Math.ceil(
					getEmployeeEffects(employees).restockAmount *
					shopEffects.restockMultiplier,
				);

				if (restockAmount <= 0) {
					return false;
				}

				const targetShelf = shelves
					.slice(0, unlockedShelfSlots)
					.filter((shelf) => shelfAssignments[shelf.id])
					.sort((left, right) => {
						const leftCapacity = getShelfCapacity(shelfUpgradeLevels[left.id]);
						const rightCapacity = getShelfCapacity(shelfUpgradeLevels[right.id]);
						return (
							(shelfStock[left.id] ?? 0) / leftCapacity -
							(shelfStock[right.id] ?? 0) / rightCapacity
						);
					})[0];

				if (!targetShelf) {
					return false;
				}

				const productId = shelfAssignments[targetShelf.id];
				const capacity = getShelfCapacity(shelfUpgradeLevels[targetShelf.id]);
				const available = productId ? inventory[productId] ?? 0 : 0;
				const quantity = Math.min(
					restockAmount,
					available,
					capacity - (shelfStock[targetShelf.id] ?? 0),
				);

				if (!productId || quantity <= 0) {
					return false;
				}

				const inventoryLotsForProduct = reconcileInventoryLots(
					productId,
					available,
					inventoryLots[productId],
				);
				const movedLots = takeInventoryLots(inventoryLotsForProduct, quantity);

				set({
					inventory: { ...inventory, [productId]: available - quantity },
					inventoryLots: {
						...inventoryLots,
						[productId]: movedLots.remainingLots,
					},
					shelfLots: {
						...shelfLots,
						[targetShelf.id]: appendInventoryLots(
							shelfLots[targetShelf.id],
							movedLots.takenLots,
						),
					},
					shelfStock: {
						...shelfStock,
						[targetShelf.id]: (shelfStock[targetShelf.id] ?? 0) + quantity,
					},
					statistics: {
						...statistics,
						restockedUnits: statistics.restockedUnits + quantity,
					},
				});

				return true;
			},
			processEmployeePayroll: () => {
				const { coins, employees } = get();
				const now = Date.now();

				if (now < employees.nextPayrollAt) {
					return false;
				}

				const payrollCost = getEmployeePayrollCost(employees);
				const canPay = coins >= payrollCost;

				set({
					coins: canPay ? coins - payrollCost : coins,
					employees: {
						...employees,
						employees: canPay
							? employees.employees
							: employees.employees.map((employee) => ({
								...employee,
								isWorking: false,
							})),
						nextPayrollAt: now + EMPLOYEE_PAYROLL_INTERVAL_MS,
						totalSalariesPaid:
							employees.totalSalariesPaid + (canPay ? payrollCost : 0),
					},
				});

				return true;
			},
			processInventorySpoilage: () => {
				const { inventory, inventoryLots, shelfAssignments, shelfLots, shelfStock, statistics } = get();
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
					hasLotChanges ||= JSON.stringify(inventoryLots[numericProductId] ?? []) !== JSON.stringify(discarded.remainingLots);

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
					hasLotChanges ||= JSON.stringify(shelfLots[shelfId] ?? []) !== JSON.stringify(discarded.remainingLots);

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
				const { inventory, inventoryCapacityLevels, inventoryLots, logistics } = get();
				const now = Date.now();
				let hasChanges = false;
				const nextInventory = { ...inventory };
				const nextInventoryLots: GameInventoryLots = { ...inventoryLots };
				const orders = logistics.orders.map((order) => {
					if (order.status === "entregue") {
						return order;
					}

					const status = getSupplierOrderStatus(order, now);

					if (status === "entregue") {
						if (
							!canAddToInventory(
								order.productId,
								order.quantity,
								nextInventory,
								inventoryCapacityLevels,
							)
						) {
							return order;
						}

						hasChanges = true;
						nextInventory[order.productId] =
							(nextInventory[order.productId] ?? 0) + order.quantity;
						nextInventoryLots[order.productId] = appendInventoryLots(
							nextInventoryLots[order.productId],
							createInventoryLots(order.productId, order.quantity, now),
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
					inventory: nextInventory,
					inventoryLots: nextInventoryLots,
					logistics: { ...logistics, orders },
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
				const shopEffects = getShopEffects(get().shop.ownedItemIds);
				const sector = getProductionSector(sectorId);
				const recipe = productionRecipes.find(
					(item) => item.id === recipeId && item.sectorId === sectorId,
				);

				if (
					!sector ||
					!recipe ||
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
					coins,
					employees,
					events,
					market,
					shelfAssignments,
					shelfLots,
					shelfPrices,
					shelfStock,
					shop,
					unlockedShelfSlots,
				} = get();
				const now = Date.now();
				const daily = normalizeDailyState(get().daily, market.level, now);
				const eventEffects = getActiveGameEventEffects(events, now);
				const shopEffects = getShopEffects(shop.ownedItemIds);
				const employeeEffects = getEmployeeEffects(employees);

				if (
					!market.isOpen ||
					!market.nextCustomerAt ||
					now < market.nextCustomerAt
				) {
					return false;
				}

				const availableProducts = shelves
					.slice(0, unlockedShelfSlots)
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
								necessity: product.demand,
								productId: product.id,
								promotionRate: 0,
								sellingPrice: shelfPrices[shelf.id] ?? product.sellingPrice,
								shelfId: shelf.id,
							},
						];
					});
				const visit = simulateMarketVisit({
					budgetMultiplier:
						(1 + Math.max(market.level - 1, 0) * 0.08) *
						shopEffects.customerBudgetMultiplier *
						eventEffects.customerBudgetMultiplier,
					maxProductsBonus: shopEffects.maxProductsBonus,
					products: availableProducts,
					revenueMultiplier:
						shopEffects.revenueMultiplier * eventEffects.revenueMultiplier,
					seed: market.randomSeed,
					storeReputation:
						market.customerSatisfaction +
							shopEffects.storeReputationBonus +
							employeeEffects.storeReputationBonus,
				});
				const nextDaily = markDailySale(
					daily,
					visit.revenue,
					1,
					visit.totalUnits,
				);
				const nextShelfStock = { ...shelfStock };
				const nextShelfLots: GameShelfLots = { ...shelfLots };
				const nextSoldByProduct = { ...market.soldByProduct };
				const experienceGained = Math.round(
					getExperienceFromSales(visit.purchases, itemCatalog) *
						eventEffects.experienceMultiplier,
				);
				const progression = applyExperience(
					market.level,
					market.experience,
					experienceGained,
				);
				const unlockedProductIds = Array.from(
					new Set([
						...market.unlockedProductIds,
						...getUnlockedProductIds(progression.level),
					]),
				);
				const recentUnlockProductIds = unlockedProductIds.filter(
					(productId) => !market.unlockedProductIds.includes(productId),
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
					nextSoldByProduct[purchase.productId] =
						(nextSoldByProduct[purchase.productId] ?? 0) + purchase.quantity;
				}

				const nextSeed = market.randomSeed + 1;
				const customer = createMarketCustomer(
					visit,
					market.randomSeed,
					shelfPrices,
					market.customerSatisfaction,
				);

				set({
					coins: coins + visit.revenue,
					daily: nextDaily,
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
						customersWhoBought:
							market.customersWhoBought + (visit.purchases.length > 0 ? 1 : 0),
						customerSatisfaction: Math.round(
							(market.customerSatisfaction * 0.88 + customer.satisfaction * 0.12) *
								10,
						) / 10,
						experience: progression.experience,
						lastExperienceGain: experienceGained,
						level: progression.level,
						nextCustomerAt:
							now +
							getCustomerArrivalDelay(
								progression.level,
								market.unlockedProductIds.length,
								nextSeed,
								shopEffects.customerArrivalMultiplier *
									eventEffects.customerArrivalMultiplier *
									employeeEffects.customerArrivalMultiplier,
							),
						recentCustomers: [customer, ...market.recentCustomers].slice(0, 3),
						randomSeed: nextSeed,
						recentUnlockProductIds:
							recentUnlockProductIds.length > 0
								? recentUnlockProductIds
								: market.recentUnlockProductIds,
						soldByProduct: nextSoldByProduct,
						todayRevenue: nextDaily.revenue,
						totalExperience: market.totalExperience + experienceGained,
						totalRevenue: market.totalRevenue + visit.revenue,
						unitsSold: market.unitsSold + visit.totalUnits,
						unlockedProductIds,
					},
					shelfStock: nextShelfStock,
					shelfLots: nextShelfLots,
				});

				get().processEmployeeWork();
				return true;
			},
			resetGame: () => {
				const { currencyPurchases } = get();

				set({ ...getInitialGameState(), currencyPurchases });
			},
			assignProductToShelf: (shelfId, productId) => {
				const {
					market,
					shelfAssignments,
					shelfPrices,
					shelfStock,
					unlockedShelfSlots,
				} = get();
				const product = itemCatalog.find((item) => item.id === productId);
				const isAssignedElsewhere = Object.entries(shelfAssignments).some(
					([assignedShelfId, assignedProductId]) =>
						assignedShelfId !== shelfId && assignedProductId === productId,
				);

				if (
					!product ||
					!market.unlockedProductIds.includes(productId) ||
					!isShelfUnlocked(shelfId, unlockedShelfSlots) ||
					isAssignedElsewhere ||
					(shelfStock[shelfId] ?? 0) > 0
				) {
					return false;
				}

				set({
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
			clearShelf: (shelfId) => {
				const {
					inventory,
					inventoryCapacityLevels,
					inventoryLots,
					shelfAssignments,
					shelfLots,
					shelfStock,
					unlockedShelfSlots,
				} = get();
				const productId = shelfAssignments[shelfId];
				const quantity = shelfStock[shelfId] ?? 0;

				if (
					!productId ||
					!isShelfUnlocked(shelfId, unlockedShelfSlots) ||
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
					unlockedShelfSlots,
				} = get();
				const availableQuantity = inventory[productId] ?? 0;
				const currentQuantity = shelfStock[shelfId] ?? 0;
				const capacity = getShelfCapacity(shelfUpgradeLevels[shelfId]);

				if (
					shelfAssignments[shelfId] !== productId ||
					!isShelfUnlocked(shelfId, unlockedShelfSlots)
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
						[shelfId]: appendInventoryLots(shelfLots[shelfId], movedLots.takenLots),
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
				const { employees, events, market, shop, statistics } = get();
				const now = Date.now();
				const daily = normalizeDailyState(get().daily, market.level, now);
				const eventEffects = getActiveGameEventEffects(events, now);
				const shopEffects = getShopEffects(shop.ownedItemIds);
				const employeeEffects = getEmployeeEffects(employees);
				const isOpening = isOpen && !market.isOpen;
				const isClosing = !isOpen && market.isOpen;
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
								employeeEffects.customerArrivalMultiplier,
						);
				const lastShiftSummary =
					isClosing && market.currentShift
						? {
								closedAt: now,
								customersServed:
									market.customersServed -
									market.currentShift.startingCustomersServed,
								durationMs: Math.max(
									0,
									now - market.currentShift.startedAt,
								),
								experienceGained:
									market.totalExperience -
									market.currentShift.startingExperience,
								revenue:
									market.totalRevenue -
									market.currentShift.startingTotalRevenue,
								satisfactionChange: Number(
									(
										market.customerSatisfaction -
										market.currentShift.startingSatisfaction
									).toFixed(1),
								),
								satisfaction: market.customerSatisfaction,
								unitsSold:
									market.unitsSold - market.currentShift.startingUnitsSold,
							}
						: market.lastShiftSummary;

				set({
					daily,
					lastSessionAt: now,
					market: {
						...market,
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
						unlockedProductIds: getUnlockedProductIds(nextLevel),
					},
				});
			},
			setEmployeeWorking: (employeeId, isWorking) => {
				const { employees } = get();

				if (!employees.employees.some((employee) => employee.id === employeeId)) {
					return false;
				}

				set({
					employees: {
						...employees,
						employees: employees.employees.map((employee) =>
							employee.id === employeeId ? { ...employee, isWorking } : employee,
						),
					},
				});

				return true;
			},
			trainEmployee: (employeeId) => {
				const { coins, employees } = get();
				const employee = employees.employees.find((item) => item.id === employeeId);
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
			unlockNextShelfSlot: () => {
				const { coins, market, unlockedShelfSlots } = get();
				const nextUpgrade = getNextShelfSlotUpgrade(unlockedShelfSlots);

				if (
					!nextUpgrade ||
					market.level < nextUpgrade.playerLevel ||
					coins < nextUpgrade.coinCost
				) {
					return false;
				}

				set({
					coins: coins - nextUpgrade.coinCost,
					unlockedShelfSlots: nextUpgrade.unlockedSlots,
				});

				return true;
			},
			unlockMarketExpansion: (expansionId) => {
				const { coins, market, unlockedMarketExpansionIds } = get();
				const expansion = getMarketExpansion(expansionId);

				if (
					!expansion ||
					unlockedMarketExpansionIds.includes(expansionId) ||
					market.level < expansion.requiredLevel ||
					coins < expansion.coinCost
				) {
					return false;
				}

				set({
					coins: coins - expansion.coinCost,
					unlockedMarketExpansionIds: [
						...unlockedMarketExpansionIds,
						expansionId,
					],
				});
				return true;
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
			migrate: migrateGameState,
			name: "checkout.game",
			partialize: ({
				coins,
				currencyPurchases,
				daily,
				employees,
					events,
					inventory,
					inventoryLots,
				inventoryCapacityLevels,
				logistics,
				market,
				offlineSummary,
				lastSessionAt,
				unlockedMarketExpansionIds,
				missions,
				production,
				shop,
					shelfAssignments,
					shelfLots,
					shelfStock,
				shelfPrices,
				unlockedShelfSlots,
				shelfUpgradeLevels,
				statistics,
			}) => ({
				coins,
				currencyPurchases,
				daily,
				employees,
					events,
					inventory,
					inventoryLots,
				inventoryCapacityLevels,
				logistics,
				market,
				offlineSummary,
				lastSessionAt,
				unlockedMarketExpansionIds,
				missions,
				production,
				shop,
					shelfAssignments,
					shelfLots,
					shelfStock,
				shelfPrices,
				unlockedShelfSlots,
				shelfUpgradeLevels,
				statistics,
			}),
			storage: createJSONStorage(() => mmkvStorage),
			version: 28,
		},
	),
);

function normalizeShelfState(
	shelfStock: GameShelfStock,
	inventory: GameInventory,
	shelfUpgradeLevels: GameShelfUpgradeLevels,
	unlockedShelfSlots: number,
	shelfAssignments: GameShelfAssignments,
) {
	const nextInventory = { ...inventory };
	const nextShelfStock = { ...shelfStock };

	for (const shelf of shelves) {
		const productId = shelfAssignments[shelf.id];
		const shelfQuantity = nextShelfStock[shelf.id] ?? 0;

		if (!productId) {
			nextShelfStock[shelf.id] = 0;
			continue;
		}

		if (!isShelfUnlocked(shelf.id, unlockedShelfSlots)) {
			nextShelfStock[shelf.id] = 0;
			nextInventory[productId] =
				(nextInventory[productId] ?? 0) + shelfQuantity;
			continue;
		}

		const capacity = getShelfCapacity(shelfUpgradeLevels[shelf.id]);

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

function normalizeEmployeesState(value: unknown): GameEmployeesState {
	const state = value as Partial<GameEmployeesState> | undefined;
	const employees = Array.isArray(state?.employees) ? state.employees : [];

	return {
		employees: employees.flatMap((employee) => {
			const definition = getEmployeeDefinition(employee.role as EmployeeRole);

			if (!definition || !employee.id || !employee.name) {
				return [];
			}

			return [{
				efficiency:
					typeof employee.efficiency === "number" && employee.efficiency > 0
						? employee.efficiency
						: definition.efficiency,
				experience:
					typeof employee.experience === "number" &&
					employee.experience >= 0
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
			}];
		}),
		nextHireNumber:
			typeof state?.nextHireNumber === "number" && state.nextHireNumber > 0
				? Math.floor(state.nextHireNumber)
				: initialEmployeesState.nextHireNumber,
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

	for (const shelf of shelves) {
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

function isShelfUnlocked(shelfId: string, unlockedShelfSlots: number) {
	const shelfIndex = shelves.findIndex((shelf) => shelf.id === shelfId);

	return shelfIndex !== -1 && shelfIndex < unlockedShelfSlots;
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

	for (const shelf of shelves) {
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
				const product = itemCatalog.find((item) => item.id === purchase.productId);
				const price = shelfPrices[purchase.shelfId] ?? product?.sellingPrice ?? 0;

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
		item: purchasedProducts || "Não encontrou produtos",
		mood: visit.customer.mood,
		name,
		satisfaction,
		spent: visit.revenue,
		status: visit.revenue > 0 ? "pagou" : "saiu sem comprar",
	};
}

const customerProfiles: Record<CustomerArchetype, { names: string[] }> = {
	economico: { names: ["Ana", "Paula", "Rita"] },
	familia: { names: ["Marcos", "Davi", "Lucas"] },
	impulsivo: { names: ["Bia", "Nina", "Lara"] },
	normal: { names: ["Caio", "Igor", "Pedro"] },
	premium: { names: ["Helena", "Clara", "Sofia"] },
};
