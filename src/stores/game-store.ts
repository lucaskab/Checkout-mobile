import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { CustomerArchetype } from "@/@types/customer-simulation";
import type {
	GameInventory,
	GameMarketCustomer,
	GameMarketState,
	GameShelfStock,
	GameState,
	GameStore,
} from "@/@types/game";
import type { LogisticsState, SupplierOrder } from "@/@types/logistics";
import { getUnlockedProductIds, marketProducts } from "@/data/market-products";
import {
	getCustomerArrivalDelay,
	simulateMarketVisit,
} from "@/services/customer-simulation";
import {
	getSupplierDeliveryDuration,
	getSupplierOrderStatus,
} from "@/services/logistics";
import {
	applyExperience,
	getExperienceFromSales,
} from "@/services/progression";
import { mmkvStorage } from "@/storage/mmkv";

const initialInventory: GameInventory = {
	1: 6,
	5: 4,
	9: 10,
	12: 5,
	13: 6,
	15: 2,
	17: 3,
};

const initialShelfStock: GameShelfStock = {
	bakery: 7,
	coffee: 2,
	dairy: 3,
	drinks: 5,
	pizza: 1,
	produce: 6,
	snacks: 4,
};

const initialLogisticsState: LogisticsState = {
	emergencyTokens: 1,
	extraTruckExpiresAt: null,
	freightCoupons: 1,
	logisticsBoostExpiresAt: null,
	orders: [],
	premiumCurrency: 10,
	vipExpiresAt: null,
};

const initialMarketState: GameMarketState = {
	customersServed: 0,
	customersWhoBought: 0,
	experience: 0,
	isOpen: false,
	lastExperienceGain: 0,
	level: 1,
	nextCustomerAt: null,
	recentUnlockProductIds: [],
	recentCustomers: [],
	randomSeed: 1,
	soldByProduct: {},
	todayRevenue: 0,
	totalExperience: 0,
	unitsSold: 0,
	unlockedProductIds: getUnlockedProductIds(1),
};

const initialGameState: GameState = {
	coins: 1248,
	inventory: initialInventory,
	logistics: initialLogisticsState,
	market: initialMarketState,
	shelfStock: initialShelfStock,
};

function getInitialGameState(): GameState {
	return {
		coins: initialGameState.coins,
		inventory: { ...initialGameState.inventory },
		logistics: {
			...initialGameState.logistics,
			orders: [...initialGameState.logistics.orders],
		},
		market: {
			...initialGameState.market,
			recentUnlockProductIds: [
				...initialGameState.market.recentUnlockProductIds,
			],
			recentCustomers: [...initialGameState.market.recentCustomers],
			soldByProduct: { ...initialGameState.market.soldByProduct },
			unlockedProductIds: [...initialGameState.market.unlockedProductIds],
		},
		shelfStock: { ...initialGameState.shelfStock },
	};
}

function migrateGameState(persistedState: unknown): GameState {
	const state = persistedState as Partial<GameState>;
	const market = state.market as Partial<GameMarketState> | undefined;

	return {
		coins: state.coins ?? initialGameState.coins,
		inventory: {
			...initialGameState.inventory,
			...state.inventory,
		},
		logistics: {
			...initialGameState.logistics,
			...state.logistics,
			orders: state.logistics?.orders ?? initialGameState.logistics.orders,
		},
		market: {
			...initialGameState.market,
			...market,
			recentCustomers:
				market?.recentCustomers ?? initialGameState.market.recentCustomers,
			recentUnlockProductIds:
				market?.recentUnlockProductIds ??
				initialGameState.market.recentUnlockProductIds,
			experience: market?.experience ?? initialGameState.market.experience,
			lastExperienceGain:
				market?.lastExperienceGain ??
				initialGameState.market.lastExperienceGain,
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
		shelfStock: {
			...initialGameState.shelfStock,
			...state.shelfStock,
		},
	};
}

export const useGameStore = create<GameStore>()(
	persist(
		(set, get) => ({
			...getInitialGameState(),
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
			activateVip: () => {
				const { logistics } = get();

				set({
					logistics: {
						...logistics,
						vipExpiresAt: Date.now() + 30 * 24 * 60 * 60_000,
					},
				});
			},
			addPremiumEntitlement: (productId) => {
				const { logistics } = get();
				const nextLogistics = { ...logistics };

				if (productId === "com.checkout.logistics.gems.small") {
					nextLogistics.premiumCurrency += 50;
				}
				if (productId === "com.checkout.logistics.emergency-pack") {
					nextLogistics.emergencyTokens += 3;
				}
				if (productId === "com.checkout.logistics.boost") {
					nextLogistics.logisticsBoostExpiresAt = Date.now() + 15 * 60_000;
				}
				if (productId === "com.checkout.logistics.extra-truck") {
					nextLogistics.extraTruckExpiresAt = Date.now() + 30 * 60_000;
				}
				if (productId === "com.checkout.vip.monthly") {
					nextLogistics.vipExpiresAt = Date.now() + 30 * 24 * 60 * 60_000;
				}

				set({ logistics: nextLogistics });
			},
			completeOrderFinalStage: (orderId) => {
				const { inventory, logistics } = get();
				const order = logistics.orders.find((item) => item.id === orderId);
				const now = Date.now();

				if (
					!order ||
					order.status === "entregue" ||
					logistics.premiumCurrency < 2 ||
					now < order.createdAt + order.deliveryDurationMs / 2
				) {
					return false;
				}

				set({
					inventory: {
						...inventory,
						[order.productId]:
							(inventory[order.productId] ?? 0) + order.quantity,
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
				});

				return true;
			},
			deliverOrderInstantly: (orderId) => {
				const { inventory, logistics } = get();
				const order = logistics.orders.find((item) => item.id === orderId);
				const now = Date.now();

				if (!order || order.status === "entregue") {
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
				});

				return true;
			},
			placeSupplierOrder: ({
				productId,
				quantity,
				totalCost,
				useFreightCoupon = false,
			}) => {
				const { coins, logistics } = get();
				const product = marketProducts.find((item) => item.id === productId);
				const now = Date.now();
				const activeOrders = logistics.orders.filter(
					(order) => order.status !== "entregue",
				);
				const truckCapacity =
					(logistics.extraTruckExpiresAt ?? 0) > now ? 2 : 1;
				const hasCoupon = useFreightCoupon && logistics.freightCoupons > 0;
				const discountedCost = hasCoupon
					? Math.ceil(totalCost * 0.9)
					: totalCost;

				if (
					!product ||
					quantity <= 0 ||
					coins < discountedCost ||
					activeOrders.length >= truckCapacity
				) {
					return false;
				}

				const order: SupplierOrder = {
					createdAt: now,
					deliveryDurationMs: getSupplierDeliveryDuration(
						product.supplierTime,
						logistics,
						now,
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
				});

				return true;
			},
			processSupplierOrders: () => {
				const { inventory, logistics } = get();
				const now = Date.now();
				let hasChanges = false;
				const nextInventory = { ...inventory };
				const orders = logistics.orders.map((order) => {
					if (order.status === "entregue") {
						return order;
					}

					const status = getSupplierOrderStatus(order, now);

					if (status === "entregue") {
						hasChanges = true;
						nextInventory[order.productId] =
							(nextInventory[order.productId] ?? 0) + order.quantity;
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
					logistics: { ...logistics, orders },
				});

				return true;
			},
			processNextCustomer: () => {
				const { coins, market, shelfStock } = get();
				const now = Date.now();

				if (
					!market.isOpen ||
					!market.nextCustomerAt ||
					now < market.nextCustomerAt
				) {
					return false;
				}

				const availableProducts = marketProducts
					.filter(
						(product) =>
							market.unlockedProductIds.includes(product.id) &&
							(shelfStock[product.shelfId] ?? 0) > 0,
					)
					.map((product) => ({
						...product,
						availableQuantity: shelfStock[product.shelfId] ?? 0,
						promotionRate: 0,
						productId: product.id,
					}));
				const visit = simulateMarketVisit({
					products: availableProducts,
					seed: market.randomSeed,
					storeReputation: 55,
				});
				const nextShelfStock = { ...shelfStock };
				const nextSoldByProduct = { ...market.soldByProduct };
				const experienceGained = getExperienceFromSales(
					visit.purchases,
					marketProducts,
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
					nextShelfStock[purchase.shelfId] -= purchase.quantity;
					nextSoldByProduct[purchase.productId] =
						(nextSoldByProduct[purchase.productId] ?? 0) + purchase.quantity;
				}

				const nextSeed = market.randomSeed + 1;
				const customer = createMarketCustomer(visit, market.randomSeed);

				set({
					coins: coins + visit.revenue,
					market: {
						...market,
						customersServed: market.customersServed + 1,
						customersWhoBought:
							market.customersWhoBought + (visit.purchases.length > 0 ? 1 : 0),
						experience: progression.experience,
						lastExperienceGain: experienceGained,
						level: progression.level,
						nextCustomerAt:
							now +
							getCustomerArrivalDelay(
								progression.level,
								market.unlockedProductIds.length,
								nextSeed,
							),
						recentCustomers: [customer, ...market.recentCustomers].slice(0, 3),
						randomSeed: nextSeed,
						recentUnlockProductIds:
							recentUnlockProductIds.length > 0
								? recentUnlockProductIds
								: market.recentUnlockProductIds,
						soldByProduct: nextSoldByProduct,
						todayRevenue: market.todayRevenue + visit.revenue,
						totalExperience: market.totalExperience + experienceGained,
						unitsSold: market.unitsSold + visit.totalUnits,
						unlockedProductIds,
					},
					shelfStock: nextShelfStock,
				});

				return true;
			},
			resetGame: () => set(getInitialGameState()),
			restockShelf: ({ amount = 1, productId, shelfId }) => {
				const { inventory, shelfStock } = get();
				const availableQuantity = inventory[productId] ?? 0;

				if (availableQuantity < amount || amount <= 0) {
					return false;
				}

				set({
					inventory: {
						...inventory,
						[productId]: availableQuantity - amount,
					},
					shelfStock: {
						...shelfStock,
						[shelfId]: (shelfStock[shelfId] ?? 0) + amount,
					},
				});

				return true;
			},
			setMarketOpen: (isOpen) => {
				const { market } = get();

				set({
					market: {
						...market,
						isOpen,
						nextCustomerAt: isOpen
							? Date.now() +
								getCustomerArrivalDelay(
									market.level,
									market.unlockedProductIds.length,
									market.randomSeed,
								)
							: null,
					},
				});
			},
			setMarketLevel: (level) => {
				const { market } = get();

				set({
					market: {
						...market,
						level: Math.max(1, Math.floor(level)),
					},
				});
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
		}),
		{
			migrate: migrateGameState,
			name: "checkout.game",
			partialize: ({ coins, inventory, logistics, market, shelfStock }) => ({
				coins,
				inventory,
				logistics,
				market,
				shelfStock,
			}),
			storage: createJSONStorage(() => mmkvStorage),
			version: 6,
		},
	),
);

function createMarketCustomer(
	visit: ReturnType<typeof simulateMarketVisit>,
	seed: number,
): GameMarketCustomer {
	const profile = customerProfiles[visit.customer.archetype];
	const name = profile.names[seed % profile.names.length];
	const purchasedProducts = visit.purchases
		.reduce<string[]>((products, purchase) => {
			const product = marketProducts.find(
				(item) => item.id === purchase.productId,
			);

			if (product) {
				products.push(product.name);
			}

			return products;
		}, [])
		.join(" e ");

	return {
		emoji: profile.emoji,
		id: `${visit.customer.id}-${seed}`,
		item: purchasedProducts || "Não encontrou produtos",
		name,
		spent: visit.revenue,
		status: visit.revenue > 0 ? "pagou" : "saiu sem comprar",
	};
}

const customerProfiles: Record<
	CustomerArchetype,
	{ emoji: string; names: string[] }
> = {
	economico: { emoji: "👩🏻", names: ["Ana", "Paula", "Rita"] },
	familia: { emoji: "👨🏾", names: ["Marcos", "Davi", "Lucas"] },
	impulsivo: { emoji: "👩🏽‍🦱", names: ["Bia", "Nina", "Lara"] },
	normal: { emoji: "👨🏻", names: ["Caio", "Igor", "Pedro"] },
	premium: { emoji: "👩🏾", names: ["Helena", "Clara", "Sofia"] },
};
